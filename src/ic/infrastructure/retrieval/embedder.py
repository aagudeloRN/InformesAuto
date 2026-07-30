from __future__ import annotations

import contextlib
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor

import httpx

from ic.shared.config import Settings

_RETRY_WAITS = [0, 3, 8]  # segundos antes de cada intento; [0]=inmediato, luego cubre swap VRAM


class Embedder:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.llm_local_embed_model
        self._keep_alive = settings.embedder_keep_alive
        self._batch_keep_alive = settings.embedder_batch_keep_alive
        self._max_workers = max(1, getattr(settings, "embedder_max_workers", 1))
        # Efectivo durante batch_mode(); None = usar _keep_alive (default seguro ADR-006)
        self._active_keep_alive: str | None = None

    @contextlib.contextmanager
    def batch_mode(self) -> Generator[None, None, None]:
        """Mantiene nomic-embed-text cargado durante el bloque (keep_alive positivo).

        Al salir, descarga el modelo explícitamente (keep_alive:0) para liberar VRAM.
        Reconcilia con ADR-006: el lote es explícito y acotado, nunca el default.
        """
        self._active_keep_alive = self._batch_keep_alive
        try:
            yield
        finally:
            self._active_keep_alive = None
            # Descarga el modelo para liberar VRAM (política ADR-006)
            try:
                httpx.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": "", "keep_alive": 0},
                    timeout=10,
                )
            except Exception:
                pass  # La descarga es best-effort; no abortar si Ollama no responde

    def embed(self, text: str) -> list[float]:
        keep_alive = self._active_keep_alive if self._active_keep_alive is not None else self._keep_alive  # noqa: E501
        last_exc: Exception | None = None
        for attempt, wait in enumerate(_RETRY_WAITS):
            if wait:
                time.sleep(wait)
            try:
                resp = httpx.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text, "keep_alive": keep_alive},
                    timeout=60,
                )
                resp.raise_for_status()
                return resp.json()["embedding"]
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                is_retryable = (
                    isinstance(exc, httpx.TimeoutException)
                    or (isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 500)
                )
                if is_retryable and attempt < len(_RETRY_WAITS) - 1:
                    last_exc = exc
                    continue
                raise
        raise last_exc  # type: ignore[misc]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embebe una lista de textos, preservando el orden.

        Con ``embedder_max_workers > 1`` lanza las peticiones en paralelo (ThreadPoolExecutor):
        cada ``embed`` es una llamada HTTP bloqueante que libera el GIL, así que la concurrencia
        solapa las peticiones a Ollama (~5x medido). El paralelismo solo es seguro con el modelo
        cargado (dentro de ``batch_mode()``); con keep_alive:0 por-petición causaría thrash de
        carga/descarga, por eso fuera de batch_mode conviene ``embedder_max_workers=1``.
        """
        if self._max_workers <= 1 or len(texts) <= 1:
            return [self.embed(t) for t in texts]
        workers = min(self._max_workers, len(texts))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(self.embed, texts))
