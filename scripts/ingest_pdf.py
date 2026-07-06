"""CLI: ingesta manual de PDFs al índice vectorial.

Uso:
    uv run python scripts/ingest_pdf.py --pdf ruta.pdf [--empresa-id UUID]
        [--titulo "Título"] [--autor "Autor"] [--año 2024]
"""

import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ic.infrastructure.sources.pdf_ingestor import PdfIngestor
from ic.shared.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestar PDF al índice vectorial")
    parser.add_argument("--pdf", required=True, help="Ruta al archivo PDF")
    parser.add_argument("--empresa-id", default=None, help="UUID de la empresa (opcional)")
    parser.add_argument("--titulo", default=None)
    parser.add_argument("--autor", default=None)
    parser.add_argument("--año", type=int, default=None)
    args = parser.parse_args()

    empresa_id = uuid.UUID(args.empresa_id) if args.empresa_id else None
    settings = get_settings()

    n = PdfIngestor(settings).ingest_batched(
        pdf_path=args.pdf,
        empresa_id=empresa_id,
        titulo=args.titulo,
        autor=args.autor,
        año=args.año,
    )
    print(f"[OK] {n} chunks ingestados desde '{args.pdf}'")


if __name__ == "__main__":
    main()
