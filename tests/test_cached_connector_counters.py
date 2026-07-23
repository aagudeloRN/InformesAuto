"""T17.1 (DT-026): contadores de hits/misses en Cached*Connector + CacheCounter compartido."""

from __future__ import annotations

from unittest.mock import MagicMock

from ic.infrastructure.sources.cached_connector import (
    CacheCounter,
    CachedOpenAlexConnector,
    CachedWebConnector,
)
from ic.shared.types import WebResult


def _make_result(url: str = "https://example.com") -> WebResult:
    return WebResult(url=url, title="T", content="contenido", snippet="s")


def _serialized(url: str = "https://example.com") -> list[dict]:
    return [{"url": url, "title": "T", "content": "contenido", "snippet": "s", "metadatos": None}]


class _FakeSettings:
    retrieval_cache_ttl_hours = 168


def test_web_counter_one_miss_then_one_hit():
    """1 MISS (búsqueda nueva) + 1 HIT (repetida) incrementan el contador compartido."""
    raw_mock = MagicMock()
    raw_mock.search.return_value = [_make_result()]

    repo_mock = MagicMock()
    repo_mock.get_fresh.side_effect = [None, _serialized()]  # miss, luego hit

    counter = CacheCounter()
    cached = CachedWebConnector(raw_mock, MagicMock(), _FakeSettings(), counter=counter)
    cached._repo = repo_mock

    cached.search("competidores nestle")  # miss
    cached.search("competidores nestle")  # hit

    assert counter.misses == 1
    assert counter.hits == 1
    # Atributos de instancia también reflejan lo mismo (observabilidad directa).
    assert cached.misses == 1
    assert cached.hits == 1


def test_web_counter_force_ddg_not_counted():
    """force_ddg=True omite la caché por completo: no cuenta hit ni miss."""
    raw_mock = MagicMock()
    raw_mock.search.return_value = [_make_result()]

    counter = CacheCounter()
    cached = CachedWebConnector(raw_mock, MagicMock(), _FakeSettings(), counter=counter)
    cached._repo = MagicMock()

    cached.search("x", force_ddg=True)
    cached.search("x", force_ddg=True)

    assert counter.hits == 0
    assert counter.misses == 0


def test_shared_counter_aggregates_across_connectors():
    """Un CacheCounter compartido agrega hits/misses de múltiples instancias (como el pipeline)."""
    counter = CacheCounter()

    repo_a = MagicMock()
    repo_a.get_fresh.return_value = None  # miss
    conn_a = CachedWebConnector(MagicMock(), MagicMock(), _FakeSettings(), counter=counter)
    conn_a._repo = repo_a
    conn_a._connector.search.return_value = [_make_result()]

    repo_b = MagicMock()
    repo_b.get_fresh.return_value = _serialized()  # hit
    conn_b = CachedOpenAlexConnector(MagicMock(), MagicMock(), _FakeSettings(), counter=counter)
    conn_b._repo = repo_b

    conn_a.search("q1")  # miss
    conn_b.search("q2")  # hit

    assert counter.hits == 1
    assert counter.misses == 1
