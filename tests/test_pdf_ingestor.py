"""Tests para PdfIngestor (fast, mocked — sin PDF real ni Ollama real)."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def fake_settings():
    s = MagicMock()
    s.ollama_base_url = "http://127.0.0.1:11434"
    s.llm_local_embed_model = "nomic-embed-text"
    s.llm_local_analytic_model = "qwen3:8b"
    s.pdf_batch_size_pages = 2
    s.db_schema = "informes_ic"
    s.rag_top_k = 10
    s.rag_similarity_threshold = 0.7
    return s


def _make_fake_reader(pages_text: list[str]):
    """Crea un PdfReader mock con las páginas indicadas."""
    fake_reader = MagicMock()
    fake_reader.metadata = {"/Title": "Test PDF", "/Author": "Test Author"}
    fake_pages = [MagicMock() for _ in pages_text]
    for page, text in zip(fake_pages, pages_text):
        page.extract_text.return_value = text
    fake_reader.pages = fake_pages
    return fake_reader


def test_ingest_batched_skips_if_document_already_indexed(fake_settings):
    """Si _document_already_ingested retorna True, ingest_batched devuelve 0 sin embeddings."""
    from ic.infrastructure.sources.pdf_ingestor import PdfIngestor

    with (
        patch("ic.infrastructure.sources.pdf_ingestor._ensure_metadatos_column"),
        patch("ic.infrastructure.sources.pdf_ingestor.PdfReader") as mock_reader_cls,
        patch("ic.infrastructure.sources.pdf_ingestor.SessionLocal"),
        patch(
            "ic.infrastructure.sources.pdf_ingestor._document_already_ingested",
            return_value=True,
        ),
        patch("ic.infrastructure.sources.pdf_ingestor.Embedder") as mock_embedder_cls,
        patch("ic.infrastructure.sources.pdf_ingestor._release_vram") as mock_release,
    ):
        mock_reader_cls.return_value = _make_fake_reader(["Texto"])
        ingestor = PdfIngestor(fake_settings)
        result = ingestor.ingest_batched(pdf_path="/fake/test.pdf", titulo="Informe Convergencia")

    assert result == 0
    mock_embedder_cls.return_value.embed_many.assert_not_called()
    mock_release.assert_not_called()


def test_ingest_batched_skips_duplicate_chunks(fake_settings):
    """Si un chunk ya existe en BD (por SHA-256), no se inserta."""
    from ic.infrastructure.sources.pdf_ingestor import PdfIngestor

    with (
        patch("ic.infrastructure.sources.pdf_ingestor._ensure_metadatos_column"),
        patch("ic.infrastructure.sources.pdf_ingestor.PdfReader") as mock_reader_cls,
        patch("ic.infrastructure.sources.pdf_ingestor.SessionLocal") as mock_session_cls,
        patch(
            "ic.infrastructure.sources.pdf_ingestor._document_already_ingested",
            return_value=False,
        ),
        patch("ic.infrastructure.sources.pdf_ingestor.Embedder") as mock_embedder_cls,
        patch("ic.infrastructure.sources.pdf_ingestor._chunk_exists", return_value=True),
        patch("ic.infrastructure.sources.pdf_ingestor._release_vram"),
    ):
        mock_reader_cls.return_value = _make_fake_reader(["Contenido página 1", "Contenido página 2"])  # noqa: E501
        mock_embedder_cls.return_value = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        ingestor = PdfIngestor(fake_settings)
        n = ingestor.ingest_batched(pdf_path="/fake/test.pdf")

    assert n == 0  # todos los chunks ya existían


def test_ingest_batched_calls_keep_alive_after_each_batch(fake_settings):
    """Se llama a _release_vram (keep_alive:0) después de cada lote procesado."""
    from ic.infrastructure.sources.pdf_ingestor import PdfIngestor

    pages = ["Página A con texto suficiente para chunking", "Página B con más contenido"]
    fake_embedding = [0.1] * 768

    with (
        patch("ic.infrastructure.sources.pdf_ingestor._ensure_metadatos_column"),
        patch("ic.infrastructure.sources.pdf_ingestor.PdfReader") as mock_reader_cls,
        patch("ic.infrastructure.sources.pdf_ingestor.SessionLocal") as mock_session_cls,
        patch(
            "ic.infrastructure.sources.pdf_ingestor._document_already_ingested",
            return_value=False,
        ),
        patch("ic.infrastructure.sources.pdf_ingestor.Embedder") as mock_embedder_cls,
        patch("ic.infrastructure.sources.pdf_ingestor._chunk_exists", return_value=False),
        patch("ic.infrastructure.sources.pdf_ingestor._release_vram") as mock_release,
        patch("ic.infrastructure.sources.pdf_ingestor.EmbeddingRepository"),
        patch("ic.infrastructure.sources.pdf_ingestor.EmbeddingVectorial"),
    ):
        mock_reader_cls.return_value = _make_fake_reader(pages)
        mock_embedder = MagicMock()
        mock_embedder.embed_many.return_value = [fake_embedding]
        mock_embedder_cls.return_value = mock_embedder

        db_mock = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=db_mock)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        ingestor = PdfIngestor(fake_settings)
        # batch_size=2, 2 páginas → 1 lote
        ingestor.ingest_batched(pdf_path="/fake/test.pdf")

    # 1 pre-call (desaloja qwen3:8b) + 1 post-batch (nomic-embed-text) = 2
    assert mock_release.call_count == 2
    mock_release.assert_called_with("http://127.0.0.1:11434", "nomic-embed-text")


def test_ingest_batched_two_batches_calls_release_twice(fake_settings):
    """Con 4 páginas y batch_size=2, se llama release_vram 2 veces."""
    from ic.infrastructure.sources.pdf_ingestor import PdfIngestor

    pages = ["Pág 1", "Pág 2", "Pág 3", "Pág 4"]
    fake_embedding = [0.1] * 768

    with (
        patch("ic.infrastructure.sources.pdf_ingestor._ensure_metadatos_column"),
        patch("ic.infrastructure.sources.pdf_ingestor.PdfReader") as mock_reader_cls,
        patch("ic.infrastructure.sources.pdf_ingestor.SessionLocal") as mock_session_cls,
        patch(
            "ic.infrastructure.sources.pdf_ingestor._document_already_ingested",
            return_value=False,
        ),
        patch("ic.infrastructure.sources.pdf_ingestor.Embedder") as mock_embedder_cls,
        patch("ic.infrastructure.sources.pdf_ingestor._chunk_exists", return_value=False),
        patch("ic.infrastructure.sources.pdf_ingestor._release_vram") as mock_release,
        patch("ic.infrastructure.sources.pdf_ingestor.EmbeddingRepository"),
        patch("ic.infrastructure.sources.pdf_ingestor.EmbeddingVectorial"),
    ):
        mock_reader_cls.return_value = _make_fake_reader(pages)
        mock_embedder = MagicMock()
        mock_embedder.embed_many.return_value = [fake_embedding]
        mock_embedder_cls.return_value = mock_embedder

        db_mock = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=db_mock)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        ingestor = PdfIngestor(fake_settings)
        ingestor.ingest_batched(pdf_path="/fake/test.pdf")

    # 1 pre-call (desaloja qwen3:8b) + 2 post-batch (nomic-embed-text) = 3
    assert mock_release.call_count == 3


def test_release_vram_handles_connection_error():
    """_release_vram no lanza excepción si Ollama no está disponible."""
    from ic.infrastructure.sources.pdf_ingestor import _release_vram

    with patch(
        "ic.infrastructure.sources.pdf_ingestor.httpx.post",
        side_effect=Exception("Connection refused"),
    ):
        _release_vram("http://127.0.0.1:11434", "nomic-embed-text")  # no debe lanzar


def test_sanitize_text_elimina_nul_y_controles(fake_settings):
    """DT-051: PDFs con bytes NUL (Euromonitor) rompían la ingesta en PostgreSQL."""
    from ic.infrastructure.sources.pdf_ingestor import _sanitize_text

    sucio = "Mercado\x00 de café\x07 en\x1f Colombia\tOK\nlínea2\r"
    limpio = _sanitize_text(sucio)
    assert "\x00" not in limpio
    assert "\x07" not in limpio and "\x1f" not in limpio
    # Conserva tab, salto de línea y retorno de carro y el texto legible.
    assert "\t" in limpio and "\n" in limpio and "\r" in limpio
    assert limpio.startswith("Mercado de café en Colombia")
