"""Backfill de `entidad_sectores` desde `entidades` + recálculo de n_sectores — DT-050/T4.

Unifica el KB preexistente (competidores globales de DT-062, candidatos NER) en el modelo de
membresías sectoriales introducido en DT-050: cada entidad con `sector_gics` obtiene su membresía
(fuente=`backfill`), conservando sub_gics/alcance/estado.
Luego @n_sectores` pasa a ser el COUNT real
de membresías (deja de ser un proxy). Idempotente: re-ejecutar no duplica ni degrada.

NOTA (T4, decisión conservadora): NO se reescribe el path del tier GLOBAL
(`list_competidores_by_sector`), que sigue leyendo `entidades.sector_gics` para preservar el
invariante DT-062b (verificado sin poder correr el E2E aquí). Migrar esa consulta al JOIN queda como
paso siguiente, con el E2E 3020 como gate. El tier LOCAL ya usa el JOIN (`list_locales_by_sector`).

Uso:
    uv run python scripts/backfill_entidad_sectores.py --dry-run
    uv run python scripts/backfill_entidad_sectores.py
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
from ic.data.models.entidad import ensure_entidades_tables  # noqa: E402
from ic.data.repositories.entidad_repo import EntidadRepository  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("backfill_entidad_sectores")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill entidad_sectores (DT-050/T4)")
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta conteos")
    args = parser.parse_args()

    ensure_entidades_tables(engine)
    with SessionLocal() as db:
        repo = EntidadRepository(db)
        total = repo.count()
        if args.dry_run:
            logger.info("Entidades en KB: %d. DRY-RUN: no se escribió nada.", total)
            return 0
        insertadas = repo.backfill_memberships_from_entidades()
        actualizadas = repo.recompute_n_sectores()
        logger.info(
            "Backfill: %d membresías nuevas, n_sectores recalculado en %d entidades (total %d).",
            insertadas, actualizadas, total,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
