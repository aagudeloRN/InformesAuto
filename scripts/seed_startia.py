"""Siembra del tier de startups desde StartIA (Medellín) — DT-050/T2.

Lee ``documentos_sectoriales/FuentesExternas/startia_clean.xlsx`` (388 startups, header fila 1),
mapea cada Vertical a su grupo GICS (crosswalk) y hace upsert por NIT con ``segmento=startup``,
``alcance=local``, ``estado=candidato``, ``fuente=db_externa`` + membresía por vertical. Alimenta
el tier 2.1.3. RN-001: candidato (curación futura). NO reingesta vectores.

Uso:
    uv run python scripts/seed_startia.py --dry-run
    uv run python scripts/seed_startia.py
"""

from __future__ import annotations

import argparse
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
    ALCANCE_LOCAL,
    ESTADO_CANDIDATO,
    FUENTE_DB_EXTERNA,
    SEGMENTO_STARTUP,
    TIPO_EMPRESA,
    ensure_entidades_tables,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow  # noqa: E402
from ic.infrastructure.ner.entity_recognizer import normalize_entity  # noqa: E402
from ic.infrastructure.sources.excel_reader import iter_excel_rows  # noqa: E402
from ic.shared.ingest.startia import parse_startia  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("seed_startia")

_XLSX = _ROOT / "documentos_sectoriales" / "FuentesExternas" / "startia_clean.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(description="Siembra tier startups StartIA (DT-050)")
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta")
    args = parser.parse_args()

    if not _XLSX.exists():
        logger.error("No se encontró %s", _XLSX)
        return 1

    if not args.dry_run:
        ensure_entidades_tables(engine)

    total = con_membresia = escritas = 0
    gics_dist: Counter[str] = Counter()
    db = None if args.dry_run else SessionLocal()
    repo = None if db is None else EntidadRepository(db)
    try:
        for row in iter_excel_rows(_XLSX, header_row=1):
            parsed = parse_startia(row, normalize=normalize_entity)
            if parsed is None:
                continue
            total += 1
            if parsed.memberships:
                con_membresia += 1
                for m in parsed.memberships:
                    gics_dist[m.sector_gics] += 1
            if total <= 5:
                logger.info(
                    "ej %-28s nit=%s GICS=%s",
                    parsed.nombre[:28],
                    parsed.nit,
                    [(m.sector_gics, m.vertical) for m in parsed.memberships],
                )
            if args.dry_run:
                continue

            primaria = parsed.memberships[0] if parsed.memberships else None
            eid = repo.upsert_entidad(
                EntidadRow(
                    nombre=parsed.nombre,
                    nombre_normalizado=parsed.nombre_normalizado,
                    tipo=TIPO_EMPRESA,
                    nit=parsed.nit,
                    ciudad=parsed.ciudad,
                    sector_gics=primaria.sector_gics if primaria else None,
                    alcance=ALCANCE_LOCAL,
                    segmento=SEGMENTO_STARTUP,
                    estado=ESTADO_CANDIDATO,
                )
            )
            for m in parsed.memberships:
                repo.upsert_sector_membership(
                    eid,
                    m.sector_gics,
                    sub_gics=m.sub_gics,
                    vertical=m.vertical,
                    alcance=ALCANCE_LOCAL,
                    fuente=FUENTE_DB_EXTERNA,
                    estado=ESTADO_CANDIDATO,
                )
            for a in parsed.atributos:
                repo.add_atributo(eid, a.clave, a.valor, FUENTE_DB_EXTERNA, estado=ESTADO_CANDIDATO)
            escritas += 1
    finally:
        if db is not None:
            db.close()

    logger.info("Total=%d con_membresía=%d escritas=%d", total, con_membresia, escritas)
    logger.info("Distribución GICS: %s", dict(gics_dist.most_common()))
    if args.dry_run:
        logger.info("DRY-RUN: no se escribió nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
