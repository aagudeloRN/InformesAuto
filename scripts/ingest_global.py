"""Ingesta del PDF global cross-sector (Fase 18, T18.1 — DT-031).

Ingestar documentos con es_global=True para que participen en el retrieval de todos los
sectores con cupo propio (reserva global, ADR-012 addendum).

Uso:
    uv run python scripts/ingest_global.py
    uv run python scripts/ingest_global.py --pdf ruta/al/archivo.pdf --titulo "Título" --autor "Autor" --año 2026

El PDF InformeConvergenciaLocal2026V3RvADAA.pdf está en la raíz del repo por defecto.
Idempotente: salta documentos ya indexados por título.
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

from ic.infrastructure.sources.pdf_ingestor import PdfIngestor  # noqa: E402
from ic.shared.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_global")

_DEFAULT_PDF = _ROOT / "InformeConvergenciaLocal2026V3RvADAA.pdf"
_DEFAULT_TITULO = "Informe de Convergencia Local 2026"
_DEFAULT_AUTOR = "Ruta N"
_DEFAULT_AÑO = 2026


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingesta PDF global cross-sector")
    parser.add_argument("--pdf", default=str(_DEFAULT_PDF), help="Ruta al PDF global")
    parser.add_argument("--titulo", default=_DEFAULT_TITULO, help="Título APA del documento")
    parser.add_argument("--autor", default=_DEFAULT_AUTOR, help="Autor institucional")
    parser.add_argument("--año", type=int, default=_DEFAULT_AÑO, help="Año de publicación")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error("PDF no encontrado: %s", pdf_path)
        return 1

    settings = get_settings()
    ingestor = PdfIngestor(settings)

    logger.info("Ingestando PDF global: %s", pdf_path.name)
    n = ingestor.ingest_batched(
        pdf_path=str(pdf_path),
        titulo=args.titulo,
        autor=args.autor,
        año=args.año,
        sector_gics=None,
        es_global=True,
    )
    logger.info("PDF global '%s': %d chunks ingestados", args.titulo, n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
