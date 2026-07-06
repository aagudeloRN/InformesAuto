"""Ingesta modular de PDFs: procesamiento por lotes con liberación de VRAM entre lotes.

Implementa RN-010: lotes de PDF_BATCH_SIZE_PAGES páginas, anti-duplicados por SHA-256
del chunk, keep_alive:0 tras cada lote.
"""

import hashlib
import logging
import os
import uuid
from pathlib import Path

import httpx
from pypdf import PdfReader
from sqlalchemy import text

from ic.data.database import SessionLocal, engine
from ic.data.models.documento_local import DocumentoLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval import chunker as chunker_mod
from ic.infrastructure.retrieval.embedder import Embedder
from ic.shared.config import Settings
from ic.shared.constants import EstadoIngesta, TipoDocumento

logger = logging.getLogger(__name__)


def _ensure_metadatos_column() -> None:
    from ic.shared.config import get_settings
    schema = get_settings().db_schema
    with engine.begin() as conn:
        conn.execute(text(
            f"ALTER TABLE {schema}.documentos_locales ADD COLUMN IF NOT EXISTS metadatos JSONB"
        ))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _chunk_exists(db_session, chunk_sha: str, schema: str) -> bool:
    sql = (
        f"SELECT 1 FROM {schema}.embeddings_vectoriales "
        "WHERE metadatos->>'chunk_sha256' = :sha LIMIT 1"
    )
    row = db_session.execute(text(sql), {"sha": chunk_sha}).fetchone()
    return row is not None


def _release_vram(base_url: str, model: str) -> None:
    try:
        httpx.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": "", "keep_alive": 0},
            timeout=10,
        )
    except Exception:
        logger.debug("keep_alive:0 ignorado (Ollama no disponible)")


class PdfIngestor:
    """Ingesta PDFs al índice vectorial en lotes reanudables con anti-duplicados por chunk."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def ingest_batched(
        self,
        pdf_path: str,
        empresa_id: uuid.UUID | None = None,
        titulo: str | None = None,
        autor: str | None = None,
        año: int | None = None,
    ) -> int:
        _ensure_metadatos_column()
        schema = self._settings.db_schema
        batch_size = getattr(self._settings, "pdf_batch_size_pages", 20)

        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pdf_info = reader.metadata or {}

        titulo_final = titulo or pdf_info.get("/Title") or Path(pdf_path).name
        autor_final = autor or pdf_info.get("/Author")
        año_str = str(año) if año else None

        metadatos_base = {
            "titulo": titulo_final,
            "fuente_nombre": autor_final or Path(pdf_path).name,
            "año": año_str or "s.f.",
            "autor": autor_final,
            "fecha_acceso": None,
        }

        embedder = Embedder(self._settings)
        total_inserted = 0
        n_batches = (total_pages + batch_size - 1) // batch_size

        for batch_idx in range(n_batches):
            start_page = batch_idx * batch_size
            end_page = min(start_page + batch_size, total_pages)
            batch_text = "\n".join(
                page.extract_text() or "" for page in reader.pages[start_page:end_page]
            ).strip()

            if not batch_text:
                logger.info("Lote %d/%d: sin texto — saltando", batch_idx + 1, n_batches)
                continue

            chunks = chunker_mod.chunk_text(batch_text)
            new_chunks: list[str] = []

            with SessionLocal() as db:
                for chunk in chunks:
                    sha = _sha256_text(chunk)
                    if not _chunk_exists(db, sha, schema):
                        new_chunks.append(chunk)

                if new_chunks:
                    embeddings = embedder.embed_many(new_chunks)
                    chunk_metas = [
                        {**metadatos_base, "chunk_sha256": _sha256_text(c)} for c in new_chunks
                    ]
                    repo = EmbeddingRepository(db)
                    orm_objects = [
                        EmbeddingVectorial(
                            fuente_tipo="pdf_manual",
                            fuente_url=os.path.abspath(pdf_path),
                            empresa_id=empresa_id,
                            chunk_texto=new_chunks[j],
                            chunk_index=total_inserted + j,
                            embedding=embeddings[j],
                            metadatos=chunk_metas[j],
                        )
                        for j in range(len(new_chunks))
                    ]
                    repo.insert_many(orm_objects)
                    total_inserted += len(new_chunks)

            _release_vram(self._settings.ollama_base_url, self._settings.llm_local_embed_model)
            logger.info(
                "Lote %d/%d (págs %d–%d): %d chunks nuevos, %d omitidos",
                batch_idx + 1, n_batches, start_page + 1, end_page,
                len(new_chunks), len(chunks) - len(new_chunks),
            )

        if total_inserted > 0:
            try:
                with SessionLocal() as db:
                    doc = DocumentoLocal(
                        empresa_id=empresa_id,
                        nombre_archivo=Path(pdf_path).name,
                        ruta_archivo=os.path.abspath(pdf_path),
                        tipo=TipoDocumento.PDF_SECTORIAL,
                        estado_ingesta=EstadoIngesta.PROCESADO,
                        metadatos={**metadatos_base, "n_chunks": total_inserted},
                    )
                    db.add(doc)
                    db.commit()
            except Exception:
                logger.warning("No se pudo registrar DocumentoLocal", exc_info=True)

        logger.info(
            "PDF '%s': %d chunks ingestados en %d lotes",
            Path(pdf_path).name, total_inserted, n_batches,
        )
        return total_inserted
