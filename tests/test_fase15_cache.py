"""Tests T15.2 — Caché de retrieval web/OpenAlex (Fase 15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_settings(ttl_hours=168):
    s = MagicMock()
    s.retrieval_cache_ttl_hours = ttl_hours
    return s


def _make_web_result(url="http://test.com"):
    from ic.shared.types import WebResult
    return WebResult(url=url, title="Test", content="contenido de prueba")


# ---------------------------------------------------------------------------
# RetrievalCacheRepository — lógica de hash y serialización
# ---------------------------------------------------------------------------


def test_cache_hash_includes_connector_and_max_results():
    """Hash distinto para (connector, max_results) diferentes sobre la misma query."""
    from ic.data.repositories.retrieval_cache_repo import _make_hash

    h1 = _make_hash("web", "empresa colombia", 5)
    h2 = _make_hash("web", "empresa colombia", 10)
    h3 = _make_hash("openalex", "empresa colombia", 5)

    assert h1 != h2
    assert h1 != h3
    assert h2 != h3


def test_cache_hash_is_deterministic():
    from ic.data.repositories.retrieval_cache_repo import _make_hash

    h1 = _make_hash("web", "consulta de prueba", 5)
    h2 = _make_hash("web", "consulta de prueba", 5)
    assert h1 == h2


def test_cache_get_fresh_miss():
    """Devuelve None cuando la query no está en caché."""
    from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    repo = RetrievalCacheRepository(db)
    result = repo.get_fresh("web", "nueva consulta", 5)
    assert result is None


def test_cache_get_fresh_hit():
    """Devuelve el payload cuando la entrada existe y no expiró."""
    from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository
    from ic.data.models.retrieval_cache import RetrievalCache

    row = MagicMock(spec=RetrievalCache)
    row.payload = [{"url": "http://x.com"}]

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = row

    repo = RetrievalCacheRepository(db)
    result = repo.get_fresh("web", "consulta", 5)
    assert result == [{"url": "http://x.com"}]


def test_cache_upsert_insert_when_missing():
    """Cuando no existe entrada, upsert hace INSERT (add + commit)."""
    from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    repo = RetrievalCacheRepository(db)
    repo.upsert("web", "q", 5, [{"url": "http://a.com"}], ttl_hours=168)

    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_cache_upsert_update_when_existing():
    """Cuando ya existe entrada, upsert actualiza sin hacer INSERT."""
    from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository
    from ic.data.models.retrieval_cache import RetrievalCache

    existing = MagicMock(spec=RetrievalCache)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing

    repo = RetrievalCacheRepository(db)
    new_payload = [{"url": "http://b.com"}]
    repo.upsert("web", "q", 5, new_payload, ttl_hours=24)

    db.add.assert_not_called()
    db.commit.assert_called_once()
    assert existing.payload == new_payload


# ---------------------------------------------------------------------------
# CachedWebConnector — call_count y bypass
# ---------------------------------------------------------------------------


def _make_cached_web(connector, db=None, ttl=168):
    from ic.infrastructure.sources.cached_connector import CachedWebConnector
    settings = _make_settings(ttl)
    if db is None:
        db = MagicMock()
    return CachedWebConnector(connector=connector, db=db, settings=settings)


def test_cached_web_miss_then_hit():
    """Primera búsqueda llama al connector; la segunda (idéntica) es cache hit."""
    from ic.infrastructure.sources.cached_connector import CachedWebConnector
    from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository

    connector = MagicMock()
    connector.search.return_value = [_make_web_result()]

    # Primera llamada: miss. Segunda: hit.
    db = MagicMock()
    repo = MagicMock(spec=RetrievalCacheRepository)
    repo.get_fresh.side_effect = [
        None,                                          # 1ª: miss
        [{"url": "http://test.com", "title": "Test",  # 2ª: hit
          "content": "contenido de prueba", "snippet": "", "metadatos": None}],
    ]

    with patch(
        "ic.infrastructure.sources.cached_connector.RetrievalCacheRepository",
        return_value=repo,
    ):
        cached = CachedWebConnector(connector=connector, db=db, settings=_make_settings())
        r1 = cached.search("consulta")
        r2 = cached.search("consulta")

    assert connector.search.call_count == 1
    assert r1[0].url == "http://test.com"
    assert r2[0].url == "http://test.com"


def test_cached_web_force_ddg_bypasses_cache():
    """force_ddg=True no consulta ni guarda en caché."""
    from ic.infrastructure.sources.cached_connector import CachedWebConnector
    from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository

    connector = MagicMock()
    connector.search.return_value = [_make_web_result("http://ddg.com")]

    db = MagicMock()
    repo = MagicMock(spec=RetrievalCacheRepository)

    with patch(
        "ic.infrastructure.sources.cached_connector.RetrievalCacheRepository",
        return_value=repo,
    ):
        cached = CachedWebConnector(connector=connector, db=db, settings=_make_settings())
        cached.search("q", force_ddg=True)
        cached.search("q", force_ddg=True)

    assert connector.search.call_count == 2
    repo.get_fresh.assert_not_called()
    repo.upsert.assert_not_called()


def test_cached_openalex_miss_then_hit():
    """Primera búsqueda a OpenAlex llama al connector; la segunda es cache hit."""
    from ic.infrastructure.sources.cached_connector import CachedOpenAlexConnector
    from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository

    connector = MagicMock()
    connector.search.return_value = [_make_web_result("https://openalex.org/W1")]

    db = MagicMock()
    repo = MagicMock(spec=RetrievalCacheRepository)
    repo.get_fresh.side_effect = [
        None,
        [{"url": "https://openalex.org/W1", "title": "Paper",
          "content": "abstract", "snippet": "", "metadatos": None}],
    ]

    with patch(
        "ic.infrastructure.sources.cached_connector.RetrievalCacheRepository",
        return_value=repo,
    ):
        cached = CachedOpenAlexConnector(connector=connector, db=db, settings=_make_settings())
        r1 = cached.search("machine learning Colombia")
        r2 = cached.search("machine learning Colombia")

    assert connector.search.call_count == 1
    assert r2[0].url == "https://openalex.org/W1"
