"""Backfill de `tipo_fuente` a los chunks EMIS ya indexados (DT-057/T1, cierra DT-054).

Los informes EMIS individuales se ingirieron con `tipo_fuente` NULL (solo PDF_SECTORIAL/global
llevaban `informe_compilado`) → quedaban sin telemetría ni palanca de reserva/boost. Este script
estampa `metadatos->>'tipo_fuente' = 'informe_emis'` en:
  1. los chunks (`embeddings_vectoriales`) cuyo documento es de tipo INFORME_EMIS, vía
     `EmbeddingBackfillRepository.backfill_tipo_fuente_emis` (lógica testeable en la capa de datos);
  2. los `documentos_locales` EMIS (telemetría a nivel documento).

NO re-embebe ni reprocesa PDFs: solo UPDATE de metadatos sobre filas existentes. Idempotente
(el filtro `tipo_fuente IS NULL` hace que una segunda corrida no afecte filas). Acotado al esquema
propio del proyecto.

Uso:
    uv run python scripts/backfill_tipo_fuente_emis.py            # aplica el backfill
    uv run python scripts/backfill_tipo_fuente_emis.py --dry-run  # solo cuenta, no escribe
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

from ic.data.database import SessionLocal  # noqa: E402
from ic.data.repositories.embedding_backfill_repo import EmbeddingBackfillRepository  # noqa: E402
from ic.shared.config import get_settings  # noqa: E402
from ic.shared.constants import TipoDocumento, TipoFuente  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_tipo_fuente_emis")


def _emis_sin_tipo(db, schema: str) -> int:
    """Chunks EMIS pendientes de etiquetar (para medición antes/después)."""
    sql = (
        f"SELECT count(*) FROM {schema}.embeddings_vectoriales e "
        f"JOIN {schema}.documentos_locales d ON e.documento_id = d.id "
        "WHERE d.tipo = :tipo_emis AND (e.metadatos->>'tipo_fuente') IS NULL"
    )
    return int(db.execute(text(sql), {"tipo_emis": TipoDocumento.INFORME_EMIS.value}).scalar())


def _backfill_documentos(db, schema: str) -> int:
    """Estampa tipo_fuente en los documentos_locales EMIS (telemetría a nivel doc). Idempotente."""
    n = db.execute(
        text(
            f"UPDATE {schema}.documentos_locales SET metadatos = "
            "coalesce(metadatos, '{}'::jsonb) || jsonb_build_object('tipo_fuente', :tf) "
            "WHERE tipo = :tipo_emis AND (metadatos->>'tipo_fuente') IS NULL"
        ),
        {"tf": TipoFuente.INFORME_EMIS.value, "tipo_emis": TipoDocumento.INFORME_EMIS.value},
    ).rowcount
    db.commit()
    return int(n)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill tipo_fuente a EMIS individuales")
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo cuenta los chunks pendientes; no escribe"
    )
    args = parser.parse_args()

    schema = get_settings().db_schema
    with SessionLocal() as db:
        antes = _emis_sin_tipo(db, schema)
        logger.info("Chunks EMIS sin tipo_fuente ANTES: %d", antes)
        if args.dry_run:
            logger.info("--dry-run: no se escribe nada")
            return 0

        n_chunks = EmbeddingBackfillRepository(db).backfill_tipo_fuente_emis()
        n_docs = _backfill_documentos(db, schema)
        despues = _emis_sin_tipo(db, schema)

    logger.info(
        "Backfill aplicado: %d chunks + %d documentos etiquetados como '%s'",
        n_chunks,
        n_docs,
        TipoFuente.INFORME_EMIS.value,
    )
    logger.info("Chunks EMIS sin tipo_fuente DESPUÉS: %d (idempotente si se re-ejecuta)", despues)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
