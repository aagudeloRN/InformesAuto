"""Fase 23 — embed_many paraleliza preservando orden; fallback serial con 1 worker.

Fast: no toca Ollama. Se sustituye ``Embedder.embed`` por una función determinista que codifica
el texto en el vector, para verificar que ``embed_many`` mantiene el orden pese a la concurrencia.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from ic.infrastructure.retrieval.embedder import Embedder


def _settings(max_workers: int):
    s = MagicMock()
    s.ollama_base_url = "http://127.0.0.1:11434"
    s.llm_local_embed_model = "nomic-embed-text"
    s.embedder_keep_alive = "0"
    s.embedder_batch_keep_alive = "5m"
    s.embedder_max_workers = max_workers
    return s


def _fake_embed(text: str):
    # Vector que codifica el índice → permite verificar el orden de salida.
    return [float(int(text))]


def test_embed_many_paralelo_preserva_orden():
    emb = Embedder(_settings(4))
    with patch.object(emb, "embed", side_effect=_fake_embed):
        out = emb.embed_many([str(i) for i in range(10)])
    assert out == [[float(i)] for i in range(10)]


def test_embed_many_serial_con_un_worker():
    emb = Embedder(_settings(1))
    with patch.object(emb, "embed", side_effect=_fake_embed):
        out = emb.embed_many([str(i) for i in range(5)])
    assert out == [[float(i)] for i in range(5)]


def test_embed_many_un_solo_texto_no_usa_pool():
    emb = Embedder(_settings(4))
    with patch.object(emb, "embed", side_effect=_fake_embed):
        assert emb.embed_many(["7"]) == [[7.0]]


def test_embed_many_realmente_solapa_las_llamadas():
    """Con llamadas lentas, el tiempo total en paralelo es muy inferior al serial."""
    emb = Embedder(_settings(4))

    def _slow(_text: str):
        time.sleep(0.05)
        return [0.0]

    with patch.object(emb, "embed", side_effect=_slow):
        t0 = time.time()
        emb.embed_many([str(i) for i in range(8)])  # 8 * 0.05 = 0.4s serial
        elapsed = time.time() - t0
    # Con 4 workers deberían ser ~2 tandas (~0.1s); holgado < 0.3s.
    assert elapsed < 0.3
