import time

import httpx

from ic.shared.config import Settings

_RETRY_WAITS = [0, 3, 8]  # segundos antes de cada intento; [0]=inmediato, luego cubre swap VRAM


class Embedder:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.llm_local_embed_model

    def embed(self, text: str) -> list[float]:
        last_exc: Exception | None = None
        for attempt, wait in enumerate(_RETRY_WAITS):
            if wait:
                time.sleep(wait)
            try:
                resp = httpx.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                    timeout=30,
                )
                resp.raise_for_status()
                return resp.json()["embedding"]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 500 and attempt < len(_RETRY_WAITS) - 1:
                    last_exc = exc
                    continue
                raise
        raise last_exc  # type: ignore[misc]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
