"""CLI: ingesta manual de PDFs al índice vectorial.

Uso:
    uv run python scripts/ingest_pdf.py --pdf ruta.pdf [--empresa-id UUID]
        [--titulo "Título"] [--autor "Autor"] [--año 2024]
"""

import argparse
import hashlib
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pypdf import PdfReader
from sqlalchemy import text

from ic.data.database import SessionLocal, engine
from ic.data.models.documento_local import DocumentoLocal
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval.embedder import Embedder
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.shared.config import get_settings
from ic.shared.constants import EstadoIngesta, TipoDocumento


def _ensure_metadatos_column() -> None:
    schema = get_settings().db_schema
    with engine.begin() as conn:
        conn.execute(text(
            f"ALTER TABLE {schema}.documentos_locales "
            "ADD COLUMN IF NOT EXISTS metadatos JSONB"
        ))


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_year_from_str(s: str | None) -> str | None:
    if not s:
        return None
    import re
    m = re.search(r"(19|20)\d{2}", s)
    return m.group(0) if m else None


def ingest_pdf(
    pdf_path: str,
    empresa_id: uuid.UUID | None,
    titulo: str | None,
    autor: str | None,
    año: int | None,
) -> int:
    settings = get_settings()

    sha = _sha256(pdf_path)

    with SessionLocal() as db:
        existing = db.execute(
            text(
                f"SELECT id FROM {settings.db_schema}.documentos_locales "
                "WHERE metadatos->>'sha256' = :sha LIMIT 1"
            ),
            {"sha": sha},
        ).fetchone()
        if existing:
            print(f"[SKIP] PDF ya ingestado (sha256={sha[:12]}…). ID={existing[0]}")
            return 0

    reader = PdfReader(pdf_path)
    pdf_info = reader.metadata or {}

    titulo_final = titulo or pdf_info.get("/Title") or os.path.basename(pdf_path)
    autor_final = autor or pdf_info.get("/Author")
    año_str: str | None = str(año) if año else _extract_year_from_str(
        pdf_info.get("/CreationDate") or pdf_info.get("/ModDate")
    )

    pages_text = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages_text)

    if not full_text.strip():
        print("[ERROR] No se pudo extraer texto del PDF.")
        return 0

    metadatos_extra_item = {
        "titulo": titulo_final,
        "fuente_nombre": autor_final or os.path.basename(pdf_path),
        "año": año_str or "s.f.",
        "autor": autor_final,
        "fecha_acceso": None,
        "sha256": sha,
    }

    with SessionLocal() as db:
        embedder = Embedder(settings)
        repo = EmbeddingRepository(db)
        store = PGVectorStore(embedder, repo, settings)

        n_chunks = store.ingest(
            texts=[full_text],
            fuente_tipo="pdf_manual",
            urls=[pdf_path],
            empresa_id=empresa_id,
            metadatos_extra=[metadatos_extra_item],
        )

        doc = DocumentoLocal(
            empresa_id=empresa_id,
            nombre_archivo=os.path.basename(pdf_path),
            ruta_archivo=os.path.abspath(pdf_path),
            tipo=TipoDocumento.PDF_SECTORIAL,
            estado_ingesta=EstadoIngesta.PROCESADO,
            metadatos={
                "sha256": sha,
                "titulo": titulo_final,
                "autor": autor_final,
                "año": año_str,
                "n_chunks": n_chunks,
            },
        )
        db.add(doc)
        db.commit()

    print(f"[OK] {n_chunks} chunks ingestados desde '{pdf_path}'")
    print(f"     Título: {titulo_final} | Autor: {autor_final} | Año: {año_str or 's.f.'}")
    return n_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestar PDF al índice vectorial")
    parser.add_argument("--pdf", required=True, help="Ruta al archivo PDF")
    parser.add_argument("--empresa-id", default=None, help="UUID de la empresa (opcional)")
    parser.add_argument("--titulo", default=None)
    parser.add_argument("--autor", default=None)
    parser.add_argument("--año", type=int, default=None)
    args = parser.parse_args()

    empresa_id = uuid.UUID(args.empresa_id) if args.empresa_id else None

    _ensure_metadatos_column()
    ingest_pdf(
        pdf_path=args.pdf,
        empresa_id=empresa_id,
        titulo=args.titulo,
        autor=args.autor,
        año=args.año,
    )


if __name__ == "__main__":
    main()
