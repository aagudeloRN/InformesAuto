"""T16.0-C: verifica que CachedWebConnector no llama al connector real en la 2ª búsqueda."""

from __future__ import annotations

from unittest.mock import MagicMock

from ic.infrastructure.sources.cached_connector import CachedWebConnector
from ic.shared.types import WebResult


def _make_result(url: str = "https://example.com") -> WebResult:
    return WebResult(url=url, title="T", content="contenido", snippet="s")


def _serialized(url: str = "https://example.com") -> list[dict]:
    return [{"url": url, "title": "T", "content": "contenido", "snippet": "s", "metadatos": None}]


class _FakeSettings:
    retrieval_cache_ttl_hours = 168


def test_cached_web_no_double_call():
    """Segunda búsqueda idéntica devuelve caché sin llamar al connector real."""
    raw_mock = MagicMock()
    raw_mock.search.return_value = [_make_result()]

    repo_mock = MagicMock()
    # 1ª llamada: miss → None; 2ª llamada: hit → payload serializado
    repo_mock.get_fresh.side_effect = [None, _serialized()]

    cached = CachedWebConnector(raw_mock, MagicMock(), _FakeSettings())
    cached._repo = repo_mock

    r1 = cached.search("query competidores")
    r2 = cached.search("query competidores")

    assert len(r1) == 1
    assert len(r2) == 1
    assert raw_mock.search.call_count == 1  # solo la 1ª corrida llama al connector real
    assert repo_mock.upsert.call_count == 1  # 1ª corrida guarda en caché


def test_cached_web_force_ddg_bypasses_cache():
    """force_ddg=True omite caché siempre."""
    raw_mock = MagicMock()
    raw_mock.search.return_value = [_make_result()]

    repo_mock = MagicMock()

    cached = CachedWebConnector(raw_mock, MagicMock(), _FakeSettings())
    cached._repo = repo_mock

    cached.search("query", force_ddg=True)
    cached.search("query", force_ddg=True)

    assert raw_mock.search.call_count == 2  # siempre llama al connector real
    repo_mock.get_fresh.assert_not_called()
    repo_mock.upsert.assert_not_called()


def test_cached_web_empty_results_not_stored():
    """Resultados vacíos no se guardan en caché."""
    raw_mock = MagicMock()
    raw_mock.search.return_value = []

    repo_mock = MagicMock()
    repo_mock.get_fresh.return_value = None

    cached = CachedWebConnector(raw_mock, MagicMock(), _FakeSettings())
    cached._repo = repo_mock

    cached.search("vacío")

    repo_mock.upsert.assert_not_called()
