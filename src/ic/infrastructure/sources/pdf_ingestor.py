"""Ingesta modular de PDFs: procesamiento por lotes con liberación de VRAM entre lotes.

Implementa RN-010: lotes de PDF_BATCH_SIZE_PAGES páginas, anti-duplicados por SHA-256
del chunk, keep_alive:0 tras cada lote.
"""

import hashlib
import logging
import os
import re
import uuid
from pathlib import Path

import httpx
from pypdf import PdfReader
from sqlalchemy import text

from ic.data.database import SessionLocal, engine
from ic.data.models.documento_local import DocumentoLocal, ensure_documento_columns
from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval import chunker as chunker_mod
from ic.infrastructure.retrieval.embedder import Embedder
from ic.shared.config import Settings
from ic.shared.constants import EstadoIngesta, TipoDocumento, TipoFuente

logger = logging.getLogger(__name__)


def _ensure_metadatos_column() -> None:
    """Migración idempotente de columnas de DocumentoLocal (metadatos, sector_gics, activo)."""
    ensure_documento_columns(engine)


# Caracteres de control C0 que PostgreSQL TEXT no admite (sobre todo NUL 0x00). Se conservan
# tab (0x09), salto de línea (0x0a) y retorno de carro (0x0d). Algunos PDFs (p. ej. Euromonitor
# "Sector Capsule") inyectan 0x00 en el texto extraído, lo que rompía la ingesta (DT-051).
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitize_text(text: str) -> str:
    """Elimina bytes NUL y otros controles C0 que PostgreSQL rechaza en columnas TEXT."""
    return _CONTROL_CHARS_RE.sub("", text)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _chunk_exists(db_session, chunk_sha: str, schema: str) -> bool:
    sql = (
        f"SELECT 1 FROM {schema}.embeddings_vectoriales "
        "WHERE metadatos->>'chunk_sha256' = :sha LIMIT 1"
    )
    row = db_session.execute(text(sql), {"sha": chunk_sha}).fetchone()
    return row is not None


def _document_already_ingested(db_session, titulo: str, schema: str) -> bool:
    """True si ya existe al menos un chunk con este título en el índice vectorial."""
    sql = (
        f"SELECT 1 FROM {schema}.embeddings_vectoriales "
        "WHERE metadatos->>'titulo' = :titulo LIMIT 1"
    )
    return db_session.execute(text(sql), {"titulo": titulo}).fetchone() is not None


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
        sector_gics: str | None = None,
        tipo: str = TipoDocumento.PDF_SECTORIAL,
        es_global: bool = False,
        sectores_adicionales: list[str] | None = None,
    ) -> int:
        _ensure_metadatos_column()
        schema = self._settings.db_schema
        batch_size = getattr(self._settings, "pdf_batch_size_pages", 20)

        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pdf_info = reader.metadata or {}

        # Título: nunca exponer extensión .pdf ni sufijos de ruta (DT-033)
        titulo_raw = titulo or pdf_info.get("/Title") or Path(pdf_path).stem
        titulo_final = titulo_raw.removesuffix(".pdf").strip()
        autor_final = autor or pdf_info.get("/Author") or "Ruta N"
        año_str = str(año) if año else None

        # Con es_global, forzar sector_gics=None para que participe en todos los sectores
        sector_efectivo = None if es_global else sector_gics

        # Fast-path: si el documento ya está indexado, no re-procesar
        with SessionLocal() as _db:
            if _document_already_ingested(_db, titulo_final, schema):
                logger.info("PDF ya indexado: '%s' — saltando re-ingesta", titulo_final)
                return 0

        metadatos_base: dict = {
            "titulo": titulo_final,
            "fuente_nombre": autor_final,
            "año": año_str or "s.f.",
            "autor": autor_final,
            "fecha_acceso": None,
        }
        if sector_efectivo:
            metadatos_base["sector_gics"] = sector_efectivo
        if es_global:
            metadatos_base["es_global"] = "true"
        # Sectores adicionales para docs multi-sector (Fase 18, T18.4)
        if sectores_adicionales:
            todos = ([sector_efectivo] if sector_efectivo else []) + sectores_adicionales
            metadatos_base["sectores"] = todos
        # Procedencia (tipo_fuente): habilita reserva/boost y telemetría de mix (DT-054/057).
        # Los informes sectoriales de Ruta N son compilaciones de múltiples fuentes (ADR-012);
        # los EMIS individuales entran etiquetados desde su ingesta (antes quedaban NULL).
        if tipo == TipoDocumento.PDF_SECTORIAL or es_global:
            metadatos_base["tipo_fuente"] = TipoFuente.INFORME_COMPILADO.value
        elif tipo == TipoDocumento.INFORME_EMIS:
            metadatos_base["tipo_fuente"] = TipoFuente.INFORME_EMIS.value

        # Crear el DocumentoLocal PRIMERO para estampar documento_id en cada chunk
        # (habilita filtrado por ciclo de vida activo/inactivo vía JOIN).
        doc_id = uuid.uuid4()
        try:
            with SessionLocal() as db_doc:
                db_doc.add(DocumentoLocal(
                    id=doc_id,
                    empresa_id=empresa_id,
                    nombre_archivo=Path(pdf_path).name,
                    ruta_archivo=os.path.abspath(pdf_path),
                    tipo=tipo,
                    sector_gics=sector_efectivo,
                    estado_ingesta=EstadoIngesta.PENDIENTE,
                    metadatos=metadatos_base,
                ))
                db_doc.commit()
        except Exception:
            logger.warning("No se pudo registrar DocumentoLocal", exc_info=True)
            doc_id = None

        # Evita OOM: desaloja el LLM generativo (qwen3:8b) antes de cargar nomic-embed-text
        _release_vram(self._settings.ollama_base_url, self._settings.llm_local_analytic_model)

        embedder = Embedder(self._settings)
        total_inserted = 0
        n_batches = (total_pages + batch_size - 1) // batch_size

        for batch_idx in range(n_batches):
            start_page = batch_idx * batch_size
            end_page = min(start_page + batch_size, total_pages)
            batch_text = _sanitize_text("\n".join(
                page.extract_text() or "" for page in reader.pages[start_page:end_page]
            )).strip()

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
                            fuente_tipo="pdf",
                            fuente_url=os.path.abspath(pdf_path),
                            documento_id=doc_id,
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

        if doc_id is not None:
            try:
                with SessionLocal() as db:
                    doc = db.get(DocumentoLocal, doc_id)
                    if doc is not None:
                        doc.estado_ingesta = EstadoIngesta.PROCESADO
                        doc.metadatos = {**metadatos_base, "n_chunks": total_inserted}
                        db.commit()
            except Exception:
                logger.warning("No se pudo actualizar DocumentoLocal", exc_info=True)

        logger.info(
            "PDF '%s': %d chunks ingestados en %d lotes",
            Path(pdf_path).name, total_inserted, n_batches,
        )
        return total_inserted
