"""Curación del KB de competidores (DT-061/T3): purga de ruido + siembra de pares verificados.

Dos pasos idempotentes sobre la tabla `entidades` (esquema propio; NO toca vectores, NO reingesta):

1. **Purga**: marca `descartado` el ruido residual (medios "… News", fragmentos de métrica OCR
   "ProfitMargin") vía el predicado puro `es_ruido_competidor`. Nunca degrada `verificado`
   (RN-001). Re-ejecutar no re-marca (excluye ya-descartados).
2. **Siembra**: hace upsert de los pares reales curados (`shared/data/pares_sectoriales.py`) como
   `verificado`, con su `sub_gics` (granularidad food/beverage/tobacco) y provenance
   `usuario/curado`. Idempotente por `(nombre_normalizado, sector)`; upgradea a `verificado` un
   candidato NER preexistente sin duplicar.

Uso:
    uv run python scripts/curar_kb_competidores.py --dry-run   # números, sin escribir
    uv run python scripts/curar_kb_competidores.py             # aplica purga + siembra
    uv run python scripts/curar_kb_competidores.py --sector 3020
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ic.data.database import SessionLocal, engine  # noqa: E402
from ic.data.models.entidad import (  # noqa: E402
    ESTADO_VERIFICADO,
    FUENTE_USUARIO,
    TIPO_COMPETIDOR,
    ensure_entidades_tables,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow  # noqa: E402
from ic.shared.data.pares_sectoriales import PARES_VERIFICADOS, pares_de_sector  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("curar_kb_competidores")


def _seed_rows(sector: str) -> list[EntidadRow]:
    """Construye las filas verificadas a sembrar para un sector (puro, sin BD)."""
    return [
        EntidadRow(
            nombre=p["nombre"],
            nombre_normalizado=p["nombre_normalizado"],
            tipo=TIPO_COMPETIDOR,
            sector_gics=sector,
            sub_gics=p["sub_gics"],
            alcance=p["alcance"],
            estado=ESTADO_VERIFICADO,
        )
        for p in pares_de_sector(sector)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Curación KB competidores (DT-061)")
    parser.add_argument("--sector", default=None, help="Acota a un sector (ej. 3020)")
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta")
    args = parser.parse_args()

    ensure_entidades_tables(engine)
    sectores = [args.sector] if args.sector else list(PARES_VERIFICADOS)

    with SessionLocal() as db:
        repo = EntidadRepository(db)

        # 1. Purga de ruido (global; el ruido no es sector-específico).
        marcados = repo.descartar_ruido_competidores(dry_run=args.dry_run)
        logger.info("Ruido %s: %d entidades (%s)",
                    "detectado" if args.dry_run else "descartado", len(marcados),
                    ", ".join(marcados[:12]) + ("…" if len(marcados) > 12 else ""))

        # 2. Siembra de pares verificados por sector.
        n_sembrados = 0
        for sector in sectores:
            filas = _seed_rows(sector)
            logger.info("Sector %s: %d pares verificados a sembrar", sector, len(filas))
            if args.dry_run:
                for f in filas:
                    logger.info("  seed %-24s sub_gics=%s alcance=%s",
                                f.nombre, f.sub_gics, f.alcance)
                continue
            for f in filas:
                eid = repo.upsert_entidad(f)
                repo.add_atributo(
                    eid, "origen", "curado", FUENTE_USUARIO, estado=ESTADO_VERIFICADO
                )
                n_sembrados += 1

        if args.dry_run:
            logger.info("DRY-RUN: no se escribió nada.")
        else:
            logger.info("Curación completada: ruido descartado=%d, pares sembrados=%d",
                        len(marcados), n_sembrados)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
