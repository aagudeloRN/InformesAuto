"""Carga masiva del corpus sectorial desde documentos_sectoriales/indice.csv (Fase 13, T13.5).

Uso:
    uv run python scripts/ingest_batch.py
    uv run python scripts/ingest_batch.py --dir documentos_sectoriales --csv <ruta_indice.csv>

Idempotente: PdfIngestor.ingest_batched salta documentos ya indexados (por título).
Recomendado ejecutar en tmux/nohup: el lote de 25 PDFs puede tardar 5-20 min.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

# Asegurar src/ en el path al ejecutar como script suelto
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ic.infrastructure.sources.pdf_ingestor import PdfIngestor  # noqa: E402
from ic.shared.config import get_settings  # noqa: E402
from ic.shared.constants import TipoDocumento  # noqa: E402
from ic.shared.constants.gics_groups import gics_options  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_batch")


def _tipo_from_csv(valor: str) -> str:
    """Mapea el texto del CSV (ej. 'PDF_SECTORIAL') al valor del enum TipoDocumento."""
    try:
        return TipoDocumento[valor.strip()].value
    except KeyError:
        return TipoDocumento.PDF_SECTORIAL.value


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingesta masiva del corpus sectorial")
    parser.add_argument("--dir", default="documentos_sectoriales", help="Carpeta con los PDFs")
    parser.add_argument(
        "--csv", default="documentos_sectoriales/indice.csv", help="Índice CSV del corpus"
    )
    args = parser.parse_args()

    base_dir = (_ROOT / args.dir).resolve()
    csv_path = (_ROOT / args.csv).resolve()

    if not csv_path.exists():
        logger.error("No existe el índice CSV: %s", csv_path)
        return 1

    nombre_por_codigo = dict(gics_options())  # {"2530": "Servicios al consumidor", ...}
    settings = get_settings()
    ingestor = PdfIngestor(settings)

    total_docs = 0
    total_chunks = 0
    errores = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            archivo = (fila.get("archivo") or "").strip()
            sector = (fila.get("sector_gics") or "").strip()
            if not archivo:
                continue
            # La ruta puede ser relativa al base_dir o relativa al root del repo
            pdf_path = base_dir / archivo
            if not pdf_path.exists():
                pdf_path = (_ROOT / archivo)
            if not pdf_path.exists():
                logger.error("Archivo no encontrado: %s — se omite", pdf_path)
                errores += 1
                continue

            nombre_sector = nombre_por_codigo.get(sector, sector)
            # Columna "titulo" en el CSV tiene prioridad; sino, inferir del sector
            titulo_csv = (fila.get("titulo") or "").strip()
            titulo = titulo_csv or f"Informe sectorial: {nombre_sector}"
            tipo = _tipo_from_csv(fila.get("tipo") or "")
            autor = (fila.get("autor") or "Ruta N Medellín").strip() or "Ruta N Medellín"
            año_raw = (fila.get("año") or "").strip()
            año = int(año_raw) if año_raw.isdigit() else None
            # Sectores adicionales para docs multi-sector (Fase 18, T18.4)
            sectores_add_raw = (fila.get("sectores_adicionales") or "").strip()
            sectores_adicionales = (
                [s.strip() for s in sectores_add_raw.split("|") if s.strip()]
                if sectores_add_raw else None
            )

            total_docs += 1
            logger.info("[%s] %s → %s", sector, archivo, titulo)
            try:
                n = ingestor.ingest_batched(
                    pdf_path=str(pdf_path),
                    titulo=titulo,
                    autor=autor,
                    año=año,
                    sector_gics=sector or None,
                    tipo=tipo,
                    sectores_adicionales=sectores_adicionales,
                )
                total_chunks += n
                logger.info("  → %d chunks nuevos", n)
            except Exception:
                logger.exception("  ✗ Error al ingerir %s", archivo)
                errores += 1

    logger.info(
        "Lote completado: %d documentos, %d chunks nuevos, %d errores",
        total_docs, total_chunks, errores,
    )
    return 0 if errores == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
