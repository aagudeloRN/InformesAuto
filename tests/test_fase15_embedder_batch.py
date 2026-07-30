"""Tests T15.1 — Embedder batch_mode (Fase 15)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_settings(keep_alive="0", batch_keep_alive="5m"):
    s = MagicMock()
    s.ollama_base_url = "http://127.0.0.1:11434"
    s.llm_local_embed_model = "nomic-embed-text"
    s.embedder_keep_alive = keep_alive
    s.embedder_batch_keep_alive = batch_keep_alive
    s.embedder_max_workers = 1  # serial en estos tests (aíslan el comportamiento de keep_alive)
    return s


def _fake_embedding_response():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"embedding": [0.1] * 768}
    return resp


# ---------------------------------------------------------------------------
# Default mode: keep_alive = "0"
# ---------------------------------------------------------------------------


def test_embed_default_uses_keep_alive_zero():
    """En modo default el body lleva keep_alive='0'."""
    from ic.infrastructure.retrieval.embedder import Embedder

    settings = _make_settings()
    embedder = Embedder(settings)

    with patch("httpx.post", return_value=_fake_embedding_response()) as mock_post:
        embedder.embed("texto de prueba")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["keep_alive"] == "0"


# ---------------------------------------------------------------------------
# Batch mode: keep_alive = batch value during block; 0 on exit
# ---------------------------------------------------------------------------


def test_batch_mode_uses_batch_keep_alive():
    """Dentro de batch_mode, el body lleva el keep_alive de lote."""
    from ic.infrastructure.retrieval.embedder import Embedder

    settings = _make_settings(batch_keep_alive="5m")
    embedder = Embedder(settings)

    with patch("httpx.post", return_value=_fake_embedding_response()) as mock_post:
        with embedder.batch_mode():
            embedder.embed("texto en lote")

    # La 1ª llamada es el embed; la última es la descarga al salir del ctx manager
    calls = mock_post.call_args_list
    embed_calls = [c for c in calls if c[1]["json"].get("prompt")]
    assert embed_calls, "No se hizo ninguna llamada de embedding"
    assert embed_calls[0][1]["json"]["keep_alive"] == "5m"


def test_batch_mode_discharges_on_exit():
    """Al salir de batch_mode se emite una llamada de descarga con keep_alive=0."""
    from ic.infrastructure.retrieval.embedder import Embedder

    settings = _make_settings(batch_keep_alive="5m")
    embedder = Embedder(settings)

    with patch("httpx.post", return_value=_fake_embedding_response()) as mock_post:
        with embedder.batch_mode():
            embedder.embed("texto en lote")

    calls = mock_post.call_args_list
    # La última llamada es la descarga
    last_call = calls[-1]
    assert last_call[1]["json"]["keep_alive"] == 0
    assert last_call[1]["json"]["prompt"] == ""


def test_batch_mode_restores_default_after_exit():
    """Tras cerrar batch_mode, el siguiente embed vuelve al keep_alive default."""
    from ic.infrastructure.retrieval.embedder import Embedder

    settings = _make_settings(keep_alive="0", batch_keep_alive="5m")
    embedder = Embedder(settings)

    with patch("httpx.post", return_value=_fake_embedding_response()) as mock_post:
        with embedder.batch_mode():
            embedder.embed("dentro del lote")
        embedder.embed("fuera del lote")

    calls = mock_post.call_args_list
    # La última embed (no la descarga) debe llevar keep_alive="0"
    # Orden: [embed_lote, descarga_salida, embed_fuera]
    outside_embed = calls[-1]
    assert outside_embed[1]["json"]["keep_alive"] == "0"


def test_batch_mode_discharges_even_on_exception():
    """batch_mode descarga el modelo aunque el bloque lance una excepción."""
    from ic.infrastructure.retrieval.embedder import Embedder

    settings = _make_settings(batch_keep_alive="5m")
    embedder = Embedder(settings)

    discharge_calls = []

    def fake_post(*args, **kwargs):
        discharge_calls.append(kwargs["json"].get("keep_alive"))
        return _fake_embedding_response()

    with patch("httpx.post", side_effect=fake_post):
        with pytest.raises(RuntimeError):
            with embedder.batch_mode():
                raise RuntimeError("fallo simulado")

    # Debe haber una llamada con keep_alive=0 (la descarga)
    assert 0 in discharge_calls
