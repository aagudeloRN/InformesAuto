"""Tests de retrieval: requieren Ollama y PostgreSQL corriendo (sin mocks — CLAUDE.md)."""

import socket

import pytest

from ic.data.database import SessionLocal
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval.chunker import chunk_text
from ic.infrastructure.retrieval.embedder import Embedder
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.config import get_settings
from ic.shared.constants.gics_groups import GICS_GROUPS, build_gics_prompt_block
from ic.shared.types import WebResult

settings = get_settings()


def _ollama_available() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 11434), timeout=2)
        s.close()
        return True
    except OSError:
        return False


def _network_available() -> bool:
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=2)
        s.close()
        return True
    except OSError:
        return False


requires_ollama = pytest.mark.skipif(not _ollama_available(), reason="Ollama no disponible")
requires_network = pytest.mark.skipif(not _network_available(), reason="Sin acceso a red")


# --- GICS ---


def test_gics_prompt_block():
    assert len(GICS_GROUPS) == 25
    block = build_gics_prompt_block()
    assert "GICS 3020" in block  # Alimentos, bebidas y tabaco
    assert "GICS 4510" in block  # Software y servicios


# --- Chunker ---


def test_chunk_text_short():
    chunks = chunk_text("texto corto")
    assert len(chunks) == 1
    assert chunks[0] == "texto corto"


def test_chunk_text_long():
    long_text = "palabra " * 300
    chunks = chunk_text(long_text, chunk_size=200, overlap=20)
    assert len(chunks) > 1


# --- CIIU extraction ---


def test_ciiu_extraction():
    connector = WebConnector(settings)
    results = [
        WebResult(
            url="http://example.com",
            title="Noel CIIU: 1083 fabricación de galletas",
            content="Empresa de alimentos con CIIU 1083",
        )
    ]
    ciiu = connector.extract_ciiu(results)
    assert ciiu == "1083"


def test_ciiu_extraction_no_match():
    connector = WebConnector(settings)
    results = [WebResult(url="http://example.com", title="Sin código", content="nada relevante")]
    assert connector.extract_ciiu(results) is None


# --- Embedder ---


@pytest.mark.slow
@requires_ollama
def test_embedder_returns_correct_dimensions():
    embedder = Embedder(settings)
    vec = embedder.embed("Grupo Nutresa es un conglomerado de alimentos")
    assert len(vec) == 768
    assert all(isinstance(v, float) for v in vec)


@pytest.mark.slow
@requires_ollama
def test_embedder_many():
    embedder = Embedder(settings)
    texts = ["galletas", "chocolates", "café"]
    vecs = embedder.embed_many(texts)
    assert len(vecs) == 3
    assert all(len(v) == 768 for v in vecs)


# --- Ingest + Search (integración completa) ---


@pytest.mark.slow
@requires_ollama
def test_ingest_and_search():
    embedder = Embedder(settings)
    db = SessionLocal()
    try:
        repo = EmbeddingRepository(db)
        store = PGVectorStore(embedder, repo, settings)

        texts = [
            "Noel es una empresa colombiana de galletas y snacks fundada en 1916 en Medellín.",
            "El portafolio de Noel incluye galletas, chocolates, café y productos de panadería.",
            "Noel pertenece al Grupo Nutresa y compite en el segmento de alimentos envasados.",
        ]
        urls = [None, None, None]
        count = store.ingest(texts, fuente_tipo="web", urls=urls)
        assert count > 0

        results = store.search("galletas snacks Colombia", threshold=0.0)
        assert len(results) > 0
        assert all(hasattr(r, "chunk_texto") for r in results)
        assert all(hasattr(r, "score") for r in results)
    finally:
        db.close()


# --- Web connector ---


@requires_network
def test_web_connector_ddg():
    # Solo corre si no hay TAVILY_API_KEY configurado para evitar llamadas de pago
    if settings.tavily_api_key:
        pytest.skip("Tavily configurado — test DDG omitido")
    connector = WebConnector(settings)
    results = connector.search("Noel galletas Colombia empresa", max_results=3)
    assert len(results) > 0
    assert all(r.url for r in results)
