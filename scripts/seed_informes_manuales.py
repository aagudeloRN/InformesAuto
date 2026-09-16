"""Siembra del KB de competidores desde los 5 informes manuales del cliente (DT-064).

Los informes de `docs/ReportesHumanos/` (NO trackeados) son **verdad de terreno**: su sección 2.1
trae las fichas de competidor en tablas anchas, por tier.
Este script:

  docx → ``iter_docx_blocks`` (wrapper infra) → ``extract_seccion_markdown`` (2.1 → markdown puro) →
  ``parse_fichas_competidores`` → ``merge_fichas_parciales`` (une las dos tablas de cada tier) →
  ``upsert_entidad`` + ``upsert_sector_membership`` + ``add_atributo`` (los 8 campos de ficha).

Todo se siembra ``fuente=informe`` / ``estado=verificado`` (el informe del cliente es fuente curada
— decisión del usuario) y con ``alcance`` por tier (global→global; regional/startup→local, +segmento
startup). Idempotente (``upsert_*`` / ``ON CONFLICT``): re-correr no duplica. NO reingesta vectores.

Doble entregable: además del KB poblado (reuso sectorial + pre-fill T4), ``--eval-out`` vuelca el
**set de evaluación** (ground truth de regresión, independiente de BD). Contiene datos del cliente →
por defecto se escribe en `docs/ReportesHumanos/` (gitignored), nunca se commitea.

Uso:
    uv run python scripts/seed_informes_manuales.py --dry-run
    uv run python scripts/seed_informes_manuales.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ic.data.database import SessionLocal, engine  # noqa: E402
from ic.data.models.entidad import (  # noqa: E402
    ALCANCE_GLOBAL,
    ALCANCE_LOCAL,
    ESTADO_VERIFICADO,
    FUENTE_INFORME,
    SEGMENTO_STARTUP,
    TIPO_COMPETIDOR,
    ensure_entidades_tables,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow  # noqa: E402
from ic.domain.kb.ficha_parser import (  # noqa: E402
    TIER_GLOBAL,
    TIER_STARTUP,
    FichaCompetidor,
    merge_fichas_parciales,
    parse_fichas_competidores,
)
from ic.domain.kb.informe_seccion import extract_seccion_markdown  # noqa: E402
from ic.infrastructure.ner.entity_recognizer import normalize_entity  # noqa: E402
from ic.infrastructure.sources.docx_reader import iter_docx_blocks  # noqa: E402
from ic.shared.constants.gics_groups import resolve_sub_gics  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("seed_informes")

_REPORTES = _ROOT / "docs" / "ReportesHumanos"
_EVAL_DEFAULT = _REPORTES / "DT064_EVAL_SET.json"

# Informe → grupo GICS (confirmado con el usuario 2026-08-01): Noel/Alsec alimentos, Andercol
# materiales/químicos, Emtelco servicios comerciales/BPO, Guane software.
_INFORMES: list[tuple[str, str]] = [
    ("Noel", "3020"),
    ("Alsec", "3020"),
    ("Andercol", "1510"),
    ("Emtelco", "2020"),
    ("Guane", "4510"),
]


def _alcance_segmento(tier: str) -> tuple[str, str | None]:
    """Mapea el tier de la ficha a (alcance, segmento) del modelo de entidad."""
    if tier == TIER_GLOBAL:
        return ALCANCE_GLOBAL, None
    if tier == TIER_STARTUP:
        return ALCANCE_LOCAL, SEGMENTO_STARTUP
    return ALCANCE_LOCAL, None  # regional


def _sub_gics_de(ficha: FichaCompetidor, sector: str) -> str | None:
    """Sub-código GICS (grupo 3020) desde texto de ficha; None fuera de 3020 o sin señal."""
    texto = " ".join(ficha.campos.get(k, "") for k in ("portafolio", "resumen_estrategico"))
    return resolve_sub_gics(texto, sector)


def _sembrar_informe(
    repo: EntidadRepository | None, nombre_informe: str, sector: str
) -> tuple[list[FichaCompetidor], int]:
    """Extrae y siembra las fichas de un informe. Devuelve (fichas, n_escritas)."""
    ruta = _REPORTES / f"InformeSectoryCompetitivo{nombre_informe}.docx"
    if not ruta.exists():
        logger.warning("No se encontró %s — se omite", ruta)
        return [], 0
    md = extract_seccion_markdown(iter_docx_blocks(ruta))
    fichas = merge_fichas_parciales(parse_fichas_competidores(md), normalize_entity)
    if repo is None:
        return fichas, 0

    escritas = 0
    for ficha in fichas:
        alcance, segmento = _alcance_segmento(ficha.tier)
        sub_gics = _sub_gics_de(ficha, sector)
        pais = ficha.campos.get("pais_origen")
        eid = repo.upsert_entidad(
            EntidadRow(
                nombre=ficha.nombre,
                nombre_normalizado=normalize_entity(ficha.nombre),
                tipo=TIPO_COMPETIDOR,
                pais=pais,
                sector_gics=sector,
                sub_gics=sub_gics,
                alcance=alcance,
                segmento=segmento,
                estado=ESTADO_VERIFICADO,
            )
        )
        repo.upsert_sector_membership(
            eid,
            sector,
            sub_gics=sub_gics,
            alcance=alcance,
            fuente=FUENTE_INFORME,
            estado=ESTADO_VERIFICADO,
        )
        for clave, valor in ficha.campos.items():
            repo.add_atributo(eid, clave, valor, FUENTE_INFORME, estado=ESTADO_VERIFICADO)
        escritas += 1
    return fichas, escritas


def main() -> int:
    parser = argparse.ArgumentParser(description="Siembra KB desde informes manuales (DT-064)")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en BD; solo reporta")
    parser.add_argument(
        "--eval-out",
        default=str(_EVAL_DEFAULT),
        help=f"Ruta del set de evaluación JSON (default: {_EVAL_DEFAULT}; gitignored)",
    )
    args = parser.parse_args()

    if not args.dry_run:
        ensure_entidades_tables(engine)

    db = None if args.dry_run else SessionLocal()
    repo = None if db is None else EntidadRepository(db)
    eval_set: dict[str, list[dict]] = {}
    total_fichas = total_escritas = 0
    try:
        for nombre_informe, sector in _INFORMES:
            fichas, escritas = _sembrar_informe(repo, nombre_informe, sector)
            total_fichas += len(fichas)
            total_escritas += escritas
            tiers = Counter(f.tier for f in fichas)
            logger.info(
                "%-9s GICS=%s fichas=%d tiers=%s escritas=%d",
                nombre_informe, sector, len(fichas), dict(tiers), escritas,
            )
            eval_set.setdefault(sector, []).extend(
                {"nombre": f.nombre, "tier": f.tier, "campos": f.campos, "informe": nombre_informe}
                for f in fichas
            )
    finally:
        if db is not None:
            db.close()

    logger.info("TOTAL fichas=%d escritas=%d sectores=%s",
                total_fichas, total_escritas, sorted(eval_set))
    if not args.dry_run:
        out = Path(args.eval_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(eval_set, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Set de evaluación → %s", out)
    else:
        logger.info("DRY-RUN: no se escribió BD ni set de evaluación.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
