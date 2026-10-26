"""Backfill de `sectores_adicionales` desde el CSV → `metadatos->'sectores'` (DT-057/T2, DT-053).

Activa la capacidad multi-sector dormida: la columna `sectores_adicionales` del índice existe
pero está vacía → ningún doc está multi-etiquetado, aunque el retrieval ya la soporta
(`search_similar`: `jsonb_exists(metadatos->'sectores', :sector)`). Este script lee el CSV, y para
cada fila con `sectores_adicionales` no vacío estampa el array `[primario] + adicionales` en:
  1. los chunks del documento (identificado por título) vía
     `EmbeddingBackfillRepository.backfill_sectores`;
  2. su `documentos_locales` (telemetría a nivel doc).

NO re-embebe ni reprocesa PDFs: solo UPDATE de metadatos. Idempotente (guarda `IS DISTINCT FROM`
→ segunda corrida no afecta filas). Acotado al esquema propio. **No inventa mapeos**: solo aplica
lo que el CSV/curador declare; si la columna está vacía, activa 0 documentos (la curación es un
paso humano — ver DT-053, "curación de datos").

Uso:
    uv run python scripts/backfill_sectores_adicionales.py
    uv run python scripts/backfill_sectores_adicionales.py --csv <ruta_indice.csv>
"""

from __future__ import annotations

import argparse
import csv
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_sectores_adicionales")


def _parse_sectores(fila: dict) -> list[str] | None:
    """Array multi-sector [primario] + adicionales, o None si la fila no declara adicionales."""
    primario = (fila.get("sector_gics") or "").strip()
    add_raw = (fila.get("sectores_adicionales") or "").strip()
    if not add_raw:
        return None
    adicionales = [s.strip() for s in add_raw.split("|") if s.strip()]
    if not adicionales:
        return None
    todos = ([primario] if primario else []) + adicionales
    # Dedup preservando orden
    return list(dict.fromkeys(todos))


def _titulo(fila: dict) -> str:
    return (fila.get("titulo") or "").strip()


def _backfill_doc_metadatos(db, schema: str, titulo: str, sectores: list[str]) -> int:
    """Estampa sectores en documentos_locales (telemetría a nivel doc). Idempotente."""
    import json

    n = db.execute(
        text(
            f"UPDATE {schema}.documentos_locales SET metadatos = "
            "coalesce(metadatos, '{}'::jsonb) "
            "|| jsonb_build_object('sectores', CAST(:sectores AS jsonb)) "
            "WHERE metadatos->>'titulo' = :titulo "
            "AND (metadatos->'sectores') IS DISTINCT FROM CAST(:sectores AS jsonb)"
        ),
        {"sectores": json.dumps(sectores), "titulo": titulo},
    ).rowcount
    db.commit()
    return int(n)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill sectores_adicionales → sectores")
    parser.add_argument(
        "--csv",
        default="documentos_sectoriales/FuentesEMIS/indice_emis.csv",
        help="Índice CSV con la columna sectores_adicionales",
    )
    args = parser.parse_args()

    csv_path = (_ROOT / args.csv).resolve()
    if not csv_path.exists():
        logger.error("No existe el índice CSV: %s", csv_path)
        return 1

    schema = get_settings().db_schema
    docs_declarados = 0
    docs_activados = 0
    chunks_actualizados = 0

    with open(csv_path, newline="", encoding="utf-8") as f, SessionLocal() as db:
        repo = EmbeddingBackfillRepository(db)
        for fila in csv.DictReader(f):
            sectores = _parse_sectores(fila)
            titulo = _titulo(fila)
            if sectores is None or not titulo:
                continue
            docs_declarados += 1
            n_chunks = repo.backfill_sectores(titulo, sectores)
            _backfill_doc_metadatos(db, schema, titulo, sectores)
            if n_chunks:
                docs_activados += 1
                chunks_actualizados += n_chunks
            logger.info("[%s] sectores=%s → %d chunks", titulo, sectores, n_chunks)

    logger.info(
        "Backfill multi-sector: %d docs declaran adicionales en el CSV; %d activados "
        "(%d chunks actualizados).",
        docs_declarados,
        docs_activados,
        chunks_actualizados,
    )
    if docs_declarados == 0:
        logger.warning(
            "La columna 'sectores_adicionales' está vacía en el CSV → 0 docs multi-etiquetados. "
            "La curación de docs transversales es un paso humano (DT-053)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
