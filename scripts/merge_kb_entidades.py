"""Merge del sustrato `entidad_menciones` → KB `entidades` (DT-056/T2).

Lee las menciones candidatas (NER, DT-057/T3), las consolida con el agregador puro
(``domain/kb/aggregate``) y hace upsert idempotente de las entidades con señal ``competidor`` en
la tabla canónica ``entidades`` (estado ``candidato``, provenance vía atributo ``origen_ner``).
Los ``publisher`` (fuentes omnipresentes) y ``ruido`` (títulos/acrónimos) NO entran al KB: quedan
en el sustrato para auditoría.

La agregación es **global** (el umbral de publisher depende de la dispersión cross-sector);
``--sector`` solo acota qué competidores se persisten (sector dominante coincide). NO toca vectores,
NO reingesta: solo lee texto/menciones ya almacenados y escribe en tablas del KB. Idempotente
(upsert): re-ejecutar no duplica filas.

Uso:
    uv run python scripts/merge_kb_entidades.py --dry-run           # números, sin escribir
    uv run python scripts/merge_kb_entidades.py                     # persiste competidores
    uv run python scripts/merge_kb_entidades.py --sector 3020       # solo un sector dominante
    uv run python scripts/merge_kb_entidades.py --min-sectores 10   # afinar umbral publisher
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

from sqlalchemy import text  # noqa: E402

from ic.data.database import SessionLocal, engine  # noqa: E402
from ic.data.models.entidad import (  # noqa: E402
    ESTADO_CANDIDATO,
    FUENTE_INFORME,
    TIPO_COMPETIDOR,
    ensure_entidades_tables,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow  # noqa: E402
from ic.domain.kb.aggregate import (  # noqa: E402
    PUBLISHER_MIN_SECTORES,
    SIGNAL_COMPETIDOR,
    MencionCruda,
    aggregate_menciones,
    rank_candidatos,
)
from ic.shared.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("merge_kb_entidades")


def _fetch_menciones(db, schema: str) -> list[MencionCruda]:
    """Carga todas las menciones candidatas del sustrato (subset para el agregador)."""
    sql = text(
        f"SELECT entidad_normalizada, entidad_texto, sector, chunk_id, documento_id "
        f"FROM {schema}.entidad_menciones"
    )
    return [
        MencionCruda(
            entidad_normalizada=r.entidad_normalizada,
            entidad_texto=r.entidad_texto,
            sector=r.sector,
            chunk_id=str(r.chunk_id),
            documento_id=str(r.documento_id) if r.documento_id else None,
        )
        for r in db.execute(sql).fetchall()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge entidad_menciones → KB entidades (DT-056)")
    parser.add_argument(
        "--sector", default=None, help="Acota los competidores persistidos a este sector dominante"
    )
    parser.add_argument(
        "--min-sectores",
        type=int,
        default=PUBLISHER_MIN_SECTORES,
        help=f"Umbral de dispersión publisher (default {PUBLISHER_MIN_SECTORES})",
    )
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta números")
    args = parser.parse_args()

    settings = get_settings()
    schema = settings.db_schema
    ensure_entidades_tables(engine)

    with SessionLocal() as db:
        menciones = _fetch_menciones(db, schema)
        logger.info("Menciones cargadas del sustrato: %d", len(menciones))

        candidatas = aggregate_menciones(menciones, publisher_min_sectores=args.min_sectores)
        por_signal = Counter(c.signal for c in candidatas)
        logger.info(
            "Entidades consolidadas: %d (competidor=%d, publisher=%d, ruido=%d)",
            len(candidatas),
            por_signal.get(SIGNAL_COMPETIDOR, 0),
            por_signal.get("publisher", 0),
            por_signal.get("ruido", 0),
        )

        competidores = [c for c in candidatas if c.signal == SIGNAL_COMPETIDOR]
        if args.sector:
            competidores = [c for c in competidores if c.sector_dominante == args.sector]
        competidores = rank_candidatos(competidores)
        logger.info(
            "Competidores a persistir%s: %d",
            f" (sector {args.sector})" if args.sector else "",
            len(competidores),
        )

        # Muestra top-15 para inspección humana (verificación del cierre).
        for c in competidores[:15]:
            logger.info(
                "  %-42s sector=%-6s chunks=%d sectores=%d conc=%.2f",
                c.nombre[:42],
                c.sector_dominante,
                c.n_chunks,
                c.n_sectores,
                c.concentracion,
            )

        if args.dry_run:
            logger.info("DRY-RUN: no se escribió nada.")
            return 0

        repo = EntidadRepository(db)
        n_antes = repo.count()
        for c in competidores:
            eid = repo.upsert_entidad(
                EntidadRow(
                    nombre=c.nombre,
                    nombre_normalizado=c.nombre_normalizado,
                    tipo=TIPO_COMPETIDOR,
                    sector_gics=c.sector_dominante,
                    estado=ESTADO_CANDIDATO,
                    aliases=c.aliases,
                    n_menciones=c.n_menciones,
                    n_chunks=c.n_chunks,
                    n_sectores=c.n_sectores,
                )
            )
            # Lineage: de dónde salió la entidad (candidato, no hecho verificado).
            repo.add_atributo(
                eid,
                "origen_ner",
                f"n_chunks={c.n_chunks};n_menciones={c.n_menciones};concentracion={c.concentracion}",
                FUENTE_INFORME,
                estado=ESTADO_CANDIDATO,
            )
        n_despues = repo.count()

    logger.info(
        "Merge completado: entidades %d → %d (nuevas=%d).", n_antes, n_despues, n_despues - n_antes
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
