"""Tests unitarios para AutoEnrich y EnrichmentConnector (Spec 008 / US2)."""

from unittest.mock import MagicMock, patch

import pytest

from ic.domain.use_cases.auto_enrich import AutoEnrich
from ic.infrastructure.sources.enrichment_connector import FragmentoEnriquecido


@pytest.fixture
def fragmentos_mock():
    return [
        FragmentoEnriquecido(
            texto="Párrafo sobre energía renovable en Colombia.",
            titulo="Informe Energético 2023",
            autores="García, J.",
            año="2023",
            url="https://openalex.org/W12345",
            fuente="openalex",
            sector_gics="5510",
            idioma="es",
        )
    ]


def test_try_enrich_success(fragmentos_mock):
    settings = MagicMock()

    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal") as mock_session_cls,
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as mock_store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as mock_conn_cls,
        patch("ic.domain.use_cases.auto_enrich.EmbeddingRepository") as mock_repo_cls,
    ):
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db

        mock_store = MagicMock()
        mock_chunk_result = MagicMock()
        mock_chunk_result.score = 0.2
        mock_store.search.return_value = [mock_chunk_result]  # < threshold 0.5
        mock_store_cls.return_value = mock_store

        mock_conn = MagicMock()
        mock_conn.fetch_fragments.return_value = fragmentos_mock
        mock_conn_cls.return_value = mock_conn

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        embedder = MagicMock()
        embedder.embed.return_value = [0.1] * 768

        auto_enrich = AutoEnrich(settings=settings, embedder=embedder)
        res = auto_enrich.try_enrich(
            sector_gics="5510", query_text="energía renovable", threshold=0.5
        )

        assert res is True
        mock_conn.fetch_fragments.assert_called_once()
        mock_repo.insert_many.assert_called_once()


def test_try_enrich_skips_when_evidence_sufficient():
    settings = MagicMock()

    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal") as mock_session_cls,
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as mock_store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as mock_conn_cls,
    ):
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db

        mock_store = MagicMock()
        mock_chunk_result = MagicMock()
        mock_chunk_result.score = 0.85
        mock_store.search.return_value = [mock_chunk_result]  # >= threshold 0.5
        mock_store_cls.return_value = mock_store

        mock_conn = MagicMock()
        mock_conn_cls.return_value = mock_conn

        embedder = MagicMock()
        auto_enrich = AutoEnrich(settings=settings, embedder=embedder)
        res = auto_enrich.try_enrich(
            sector_gics="5510", query_text="energía renovable", threshold=0.5
        )

        assert res is False
        mock_conn.fetch_fragments.assert_not_called()


def test_try_enrich_graceful_degradation_on_exception():
    settings = MagicMock()

    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal") as mock_session_cls,
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as mock_store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as mock_conn_cls,
    ):
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db

        mock_store = MagicMock()
        mock_chunk_result = MagicMock()
        mock_chunk_result.score = 0.1
        mock_store.search.return_value = [mock_chunk_result]
        mock_store_cls.return_value = mock_store

        mock_conn = MagicMock()
        mock_conn.fetch_fragments.side_effect = RuntimeError("OpenAlex API Timeout")
        mock_conn_cls.return_value = mock_conn

        embedder = MagicMock()
        auto_enrich = AutoEnrich(settings=settings, embedder=embedder)
        res = auto_enrich.try_enrich(
            sector_gics="5510", query_text="energía renovable", threshold=0.5
        )

        assert res is False


def test_maybe_auto_enrich_guard_enriched_sectors():
    ctx = MagicMock()
    ctx._enriched_sectors = set()
    ctx.settings = MagicMock()
    ctx.embedder = MagicMock()

    with patch("ic.domain.use_cases.auto_enrich.AutoEnrich") as mock_auto_enrich_cls:
        mock_instance = MagicMock()
        mock_instance.try_enrich.return_value = True
        mock_auto_enrich_cls.return_value = mock_instance

        from ic.domain.use_cases._n1_chapter_builders import _maybe_auto_enrich

        res1 = _maybe_auto_enrich(ctx, "5510", "energía renovable")
        assert res1 is True
        assert "5510" in ctx._enriched_sectors
        assert mock_instance.try_enrich.call_count == 1

        res2 = _maybe_auto_enrich(ctx, "5510", "energía renovable")
        assert res2 is False
        assert mock_instance.try_enrich.call_count == 1
