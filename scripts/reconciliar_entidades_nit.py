#!/usr/bin/env python3
"""Script CLI para ejecucion idempotente de Reconciliacion de Entidades por NIT (DT-050b).

Soporta:
  --dry-run   Simula la reconciliacion sin alterar la base de datos.
  --execute   Ejecuta la reconciliacion y fusion real en la base de datos.
"""

from __future__ import annotations

import argparse
import logging

from sqlalchemy import text

from ic.data.database import SessionLocal, engine
from ic.data.models.entidad import ensure_entidades_tables
from ic.data.repositories.entidad_repo import EntidadRepository
from ic.domain.use_cases.reconcile_entidades import ReconcileEntidades
from ic.shared.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ensure_ddl_migration() -> None:
    """Asegura la migracion DDL de la columna aliases en entidades."""
    schema = get_settings().db_schema
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE {schema}.entidades "
                "ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]'::jsonb"
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcilia entidades duplicadas por NIT en el Knowledge Base."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la reconciliacion e imprime los pares detectados sin modificar la BD.",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Ejecuta la reconciliacion y fusion de entidades en la base de datos.",
    )

    args = parser.parse_args()
    is_dry_run = args.dry_run

    logger.info("Iniciando Reconciliacion de Entidades por NIT (dry_run=%s)", is_dry_run)
    ensure_ddl_migration()

    with SessionLocal() as db:
        ensure_entidades_tables(db.get_bind())
        repo = EntidadRepository(db)
        use_case = ReconcileEntidades(repo)
        res = use_case.reconcile(dry_run=is_dry_run)

    print("\n--- RESUMEN DE RECONCILIACIÓN POR NIT ---")
    print(f"Modo de ejecución: {'DRY RUN (Simulación)' if is_dry_run else 'EJECUCIÓN REAL'}")
    print(f"Grupos duplicados por NIT detectados: {res['total_grupos']}")
    print(f"Entidades redundantes a fusionar/fusionadas: {res['total_fusionadas']}\n")

    for g in res["grupos"]:
        print(
            f"NIT {g['nit']}: Canónica #{g['canonica_id']} '{g['canonica_nombre']}' "
            f"<- Absorbe duplicados {g['duplicados_ids']} ({', '.join(g['duplicados_nombres'])})"
        )

    print("\nProceso completado exitosamente.")


if __name__ == "__main__":
    main()
