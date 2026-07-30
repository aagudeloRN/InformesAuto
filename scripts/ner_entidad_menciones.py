"""NER sobre el `chunk_texto` ya almacenado → tabla `entidad_menciones` (DT-057/T3).

Recorre el corpus PDF por lotes, extrae entidades (organizaciones/competidores) con el wrapper NER
(motor spaCy por config, CPU, sin VRAM) y hace upsert idempotente por (entidad_normalizada,
chunk_id). NO reprocesa PDFs ni re-embebe: lee el texto YA almacenado. Cada mención entra como
**candidato** con procedencia (documento, chunk, sector, tipo de fuente) — sustrato del KB (DT-056).

Idempotente: ON CONFLICT DO NOTHING → correr dos veces no duplica filas.

Uso:
    uv run python scripts/ner_entidad_menciones.py                 # todo el corpus PDF sectorial
    uv run python scripts/ner_entidad_menciones.py --sector 3020   # solo un sector
    uv run python scripts/ner_entidad_menciones.py --limit 500     # prueba acotada
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

from sqlalchemy import text  # noqa: E402

from ic.data.database import SessionLocal, engine  # noqa: E402
from ic.data.models.entidad_mencion import ensure_entidad_menciones_table  # noqa: E402
from ic.data.repositories.entidad_mencion_repo import (  # noqa: E402
    EntidadMencionRepository,
    MencionRow,
)
from ic.infrastructure.ner.entity_recognizer import EntityRecognizer  # noqa: E402
from ic.shared.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("ner_entidad_menciones")


def _fetch_batch(db, schema: str, sector: str | None, after_id, limit: int) -> list:
    """Lote de chunks PDF con sector (keyset por id). Solo el corpus sectorial (empresas)."""
    cond = "e.fuente_tipo = 'pdf' AND (e.metadatos->>'sector_gics') IS NOT NULL"
    params: dict = {"after_id": after_id, "limit": limit}
    if sector:
        cond += " AND e.metadatos->>'sector_gics' = :sector"
        params["sector"] = sector
    sql = text(
        f"SELECT e.id, e.documento_id, e.chunk_texto, "
        f"       e.metadatos->>'sector_gics' AS sector, "
        f"       e.metadatos->>'tipo_fuente' AS fuente_tipo "
        f"FROM {schema}.embeddings_vectoriales e "
        f"WHERE {cond} AND e.id > :after_id "
        f"ORDER BY e.id LIMIT :limit"
    )
    return db.execute(sql, params).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(description="NER → entidad_menciones (sustrato KB, DT-057/T3)")
    parser.add_argument("--sector", default=None, help="Acota a un sector GICS (ej. 3020)")
    parser.add_argument("--limit", type=int, default=None, help="Máx. de chunks (prueba acotada)")
    parser.add_argument("--batch", type=int, default=500, help="Tamaño de lote (default 500)")
    args = parser.parse_args()

    settings = get_settings()
    schema = settings.db_schema
    ensure_entidad_menciones_table(engine)

    recognizer = EntityRecognizer(settings)
    procesados = 0
    insertadas = 0
    after_id = "00000000-0000-0000-0000-000000000000"

    with SessionLocal() as db:
        repo = EntidadMencionRepository(db)
        n_inicial = repo.count()
        while True:
            restante = args.batch
            if args.limit is not None:
                restante = min(restante, args.limit - procesados)
                if restante <= 0:
                    break
            filas_chunk = _fetch_batch(db, schema, args.sector, after_id, restante)
            if not filas_chunk:
                break
            lote: list[MencionRow] = []
            for row in filas_chunk:
                after_id = row.id
                for m in recognizer.extract(row.chunk_texto or ""):
                    lote.append(MencionRow(
                        entidad_normalizada=m.normalizada,
                        entidad_texto=m.texto,
                        tipo=m.tipo,
                        chunk_id=str(row.id),
                        documento_id=str(row.documento_id) if row.documento_id else None,
                        sector=row.sector,
                        fuente_tipo=row.fuente_tipo,
                    ))
            insertadas += repo.upsert_many(lote)
            procesados += len(filas_chunk)
            logger.info("Procesados %d chunks; %d menciones nuevas", procesados, insertadas)

        n_final = repo.count()

    logger.info(
        "NER completado: %d chunks procesados, %d menciones nuevas (tabla: %d → %d).",
        procesados, insertadas, n_inicial, n_final,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
