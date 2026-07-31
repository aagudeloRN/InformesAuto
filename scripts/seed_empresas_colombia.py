"""Siembra del directorio local desde EmpresasColombia (ISI Markets/WVB) — DT-050/T1.

Lee los 10 Excel de ``documentos_sectoriales/FuentesEMIS/EmpresasColombia/`` (header en la fila 8),
mapea cada empresa a su(s) grupo(s) GICS por división CIIU y hace upsert idempotente por NIT en la
KB de entidades (``alcance=local``, ``estado=candidato``, ``fuente=emis``) + una membresía sectorial
por cada CIIU. RN-001: entra como **candidato** (directorio bruto, no competencia verificada); la
curación humana es futura. NO toca vectores ni reingesta.

Uso:
    uv run python scripts/seed_empresas_colombia.py --dry-run   # conteos/mapeos, sin escribir
    uv run python scripts/seed_empresas_colombia.py             # aplica (correr en tmux/nohup, ~98k)
    uv run python scripts/seed_empresas_colombia.py --limit 500 # prueba acotada
"""

from __future__ import annotations

import argparse
import glob
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
    FUENTE_EMIS,
    TIPO_EMPRESA,
    ensure_entidades_tables,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow  # noqa: E402
from ic.infrastructure.ner.entity_recognizer import normalize_entity  # noqa: E402
from ic.infrastructure.sources.excel_reader import iter_excel_rows  # noqa: E402
from ic.shared.ingest.empresas_colombia import parse_empresa_colombia  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("seed_empresas_colombia")

_GLOB = str(_ROOT / "documentos_sectoriales" / "FuentesEMIS" / "EmpresasColombia" / "EXPORT*.xlsx")
_HEADER_ROW = 8


def main() -> int:
    parser = argparse.ArgumentParser(description="Siembra directorio local EmpresasColombia (DT-050)")
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta")
    parser.add_argument("--limit", type=int, default=None, help="Máx. filas (prueba)")
    args = parser.parse_args()

    archivos = sorted(glob.glob(_GLOB))
    if not archivos:
        logger.error("No se encontraron Excel en %s", _GLOB)
        return 1
    logger.info("%d archivos EmpresasColombia", len(archivos))

    if not args.dry_run:
        ensure_entidades_tables(engine)

    total = con_membresia = sin_membresia = sin_nit = escritas = 0
    gics_dist: Counter[str] = Counter()
    db = None if args.dry_run else SessionLocal()
    repo = None if db is None else EntidadRepository(db)
    try:
        for archivo in archivos:
            for row in iter_excel_rows(archivo, header_row=_HEADER_ROW):
                if args.limit is not None and total >= args.limit:
                    break
                parsed = parse_empresa_colombia(row, normalize=normalize_entity)
                if parsed is None:
                    continue
                total += 1
                if parsed.memberships:
                    con_membresia += 1
                    for m in parsed.memberships:
                        gics_dist[m.sector_gics] += 1
                else:
                    sin_membresia += 1
                if not parsed.nit:
                    sin_nit += 1

                if total <= 5:
                    logger.info(
                        "ej %-32s nit=%s GICS=%s ciudad=%s",
                        parsed.nombre[:32], parsed.nit,
                        [m.sector_gics for m in parsed.memberships], parsed.ciudad,
                    )
                if args.dry_run:
                    continue

                primaria = parsed.memberships[0] if parsed.memberships else None
                eid = repo.upsert_entidad(EntidadRow(
                    nombre=parsed.nombre, nombre_normalizado=parsed.nombre_normalizado,
                    tipo=TIPO_EMPRESA, nit=parsed.nit, ciudad=parsed.ciudad, pais=parsed.pais,
                    sector_gics=primaria.sector_gics if primaria else None,
                    sub_gics=primaria.sub_gics if primaria else None,
                    alcance=ALCANCE_LOCAL, estado=ESTADO_CANDIDATO,
                ))
                for m in parsed.memberships:
                    repo.upsert_sector_membership(
                        eid, m.sector_gics, sub_gics=m.sub_gics, vertical=m.vertical,
                        alcance=ALCANCE_LOCAL, fuente=FUENTE_EMIS, estado=ESTADO_CANDIDATO,
                    )
                for a in parsed.atributos:
                    repo.add_atributo(eid, a.clave, a.valor, FUENTE_EMIS, estado=ESTADO_CANDIDATO)
                escritas += 1
            if args.limit is not None and total >= args.limit:
                break
    finally:
        if db is not None:
            db.close()

    logger.info(
        "Total=%d con_membresía=%d sin_membresía=%d sin_NIT=%d escritas=%d",
        total, con_membresia, sin_membresia, sin_nit, escritas,
    )
    logger.info("Distribución GICS (membresías): %s", dict(gics_dist.most_common()))
    if args.dry_run:
        logger.info("DRY-RUN: no se escribió nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
