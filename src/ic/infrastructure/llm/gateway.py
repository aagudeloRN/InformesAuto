"""LLM Gateway — Ollama (local) y OpenRouter (API) como BaseChatModel de LangChain (ADR-002)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from tenacity import retry, stop_after_attempt, wait_exponential

from ic.shared.config import Settings

# Precios en USD por token (in, out). Los modelos :free tienen costo $0.
_PRICING: dict[str, tuple[float, float]] = {
    "nvidia/nemotron-3-super-120b-a12b:free": (0.0, 0.0),
    "nvidia/nemotron-3-ultra-550b-a55b:free": (0.0, 0.0),
    "openai/gpt-oss-120b:free": (0.0, 0.0),
    "google/gemma-3-27b-it": (0.10 / 1_000_000, 0.20 / 1_000_000),
    "google/gemma-3-12b-it": (0.05 / 1_000_000, 0.10 / 1_000_000),
}

ModelTier = Literal["free", "free_alt", "synth", "paid"]


@dataclass
class CallRecord:
    modelo: str
    tokens_in: int
    tokens_out: int
    costo_usd: float


class CostTracker:
    def __init__(self, budget_limit: float) -> None:
        self._budget_limit = budget_limit
        self._calls: list[CallRecord] = field(default_factory=list)
        self._calls = []

    def add_call(self, modelo: str, tokens_in: int, tokens_out: int) -> CallRecord:
        precio_in, precio_out = _PRICING.get(modelo, (0.0, 0.0))
        costo = tokens_in * precio_in + tokens_out * precio_out
        record = CallRecord(
            modelo=modelo, tokens_in=tokens_in, tokens_out=tokens_out, costo_usd=costo
        )
        self._calls.append(record)
        return record

    def add_local_call(self, tokens_in: int, tokens_out: int) -> None:
        """Compatibilidad con código legado — las llamadas locales no tienen costo."""
        self._calls.append(
            CallRecord(modelo="local", tokens_in=tokens_in, tokens_out=tokens_out, costo_usd=0.0)
        )

    def within_budget(self) -> bool:
        return self.total_cost() <= self._budget_limit

    def total_cost(self) -> float:
        return sum(r.costo_usd for r in self._calls)

    def total_tokens(self) -> tuple[int, int]:
        return (
            sum(r.tokens_in for r in self._calls),
            sum(r.tokens_out for r in self._calls),
        )

    def records(self) -> list[CallRecord]:
        return list(self._calls)


class OllamaGatewayLLM(BaseChatModel):
    base_url: str
    model: str
    max_retries: int = 3
    timeout: int = 120

    @property
    def _llm_type(self) -> str:
        return "ollama-gateway"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        _TYPE_MAP = {"system": "system", "human": "user", "ai": "assistant"}
        ollama_msgs = [{"role": _TYPE_MAP[m.type], "content": m.content} for m in messages]

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(min=1, max=10),
            reraise=True,
        )
        def _call() -> str:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": ollama_msgs, "stream": False, "keep_alive": 0},  # noqa: E501
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        content = _call()
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        _TYPE_MAP = {"system": "system", "human": "user", "ai": "assistant"}
        ollama_msgs = [{"role": _TYPE_MAP[m.type], "content": m.content} for m in messages]

        with httpx.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": ollama_msgs, "stream": True, "keep_alive": 0},
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
                    if run_manager:
                        run_manager.on_llm_new_token(token, chunk=chunk)
                    yield chunk
                if data.get("done"):
                    break


class OpenRouterGatewayLLM(BaseChatModel):
    """Gateway httpx para OpenRouter (API OpenAI-compatible). Registra uso de tokens."""

    base_url: str
    model: str
    api_key: str
    max_retries: int = 3
    timeout: int = 180
    cost_tracker: CostTracker | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        return "openrouter-gateway"

    def _to_openai_messages(self, messages: list[BaseMessage]) -> list[dict]:
        _TYPE_MAP = {"system": "system", "human": "user", "ai": "assistant"}
        return [{"role": _TYPE_MAP[m.type], "content": m.content} for m in messages]

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.cost_tracker and not self.cost_tracker.within_budget():
            raise RuntimeError(
                f"Presupuesto agotado (${self.cost_tracker.total_cost():.4f} USD). "
                "Aumentar LLM_BUDGET_LIMIT_USD en .env para continuar."
            )

        payload = {
            "model": self.model,
            "messages": self._to_openai_messages(messages),
        }

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(min=2, max=30),
            reraise=True,
        )
        def _call() -> dict:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/aagudeloRN/informes-ic",
                    "X-Title": "InformesAuto-IC",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            # OpenRouter puede devolver HTTP 200 con {"error": {...}} cuando el modelo
            # no está disponible o hay rate-limit. Esto NO dispara raise_for_status().
            if "error" in data:
                err = data["error"]
                logger.warning("OpenRouter error en body (model=%s): %s", self.model, err)
                raise RuntimeError(f"OpenRouter error: {err}")
            if "choices" not in data or not data["choices"]:
                logger.error("OpenRouter respuesta inesperada (sin choices, model=%s): %s", self.model, data)
                raise RuntimeError(f"OpenRouter sin 'choices' (model={self.model}): {data}")
            return data

        data = _call()
        content = data["choices"][0]["message"]["content"]

        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        if self.cost_tracker:
            self.cost_tracker.add_call(self.model, tokens_in, tokens_out)

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        if self.cost_tracker and not self.cost_tracker.within_budget():
            raise RuntimeError("Presupuesto agotado.")

        payload = {
            "model": self.model,
            "messages": self._to_openai_messages(messages),
            "stream": True,
        }

        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/aagudeloRN/informes-ic",
                "X-Title": "InformesAuto-IC",
            },
            json=payload,
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    if "error" in chunk_data:
                        logger.error("OpenRouter stream error (model=%s): %s", self.model, chunk_data["error"])
                        raise RuntimeError(f"OpenRouter stream error: {chunk_data['error']}")
                    if "choices" not in chunk_data or not chunk_data["choices"]:
                        continue
                    delta = chunk_data["choices"][0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
                        if run_manager:
                            run_manager.on_llm_new_token(token, chunk=chunk)
                        yield chunk


def build_llm(settings: Settings) -> OllamaGatewayLLM:
    """Construye el LLM local (Ollama). Usar para embeddings, Cap 1 y GICS."""
    return OllamaGatewayLLM(
        base_url=settings.ollama_base_url,
        model=settings.llm_local_analytic_model,
        max_retries=settings.llm_circuit_breaker_max_retries,
        timeout=settings.llm_local_timeout,
    )


def build_api_llm(
    settings: Settings,
    tier: ModelTier = "free",
    cost_tracker: CostTracker | None = None,
) -> OpenRouterGatewayLLM:
    """Construye LLM de API (OpenRouter).

    tier='free'  → Nemotron Super (Caps 2, 3, 4 analíticos)
    tier='synth' → Nemotron Ultra (Caps 5, 6, Resumen — síntesis)
    tier='paid'  → Gemma 3 27B (respaldo si free tiene rate limit)
    """
    model_map: dict[ModelTier, str] = {
        "free": settings.llm_api_free_model,
        "free_alt": settings.llm_api_free_alt_model,
        "synth": settings.llm_api_synth_model,
        "paid": settings.llm_api_paid_model,
    }
    model = model_map[tier]
    if not model:
        raise ValueError(
            f"Modelo para tier='{tier}' no configurado en .env "
            f"(LLM_API_FREE_MODEL / LLM_API_SYNTH_MODEL / LLM_API_PAID_MODEL)"
        )
    return OpenRouterGatewayLLM(
        base_url=settings.openrouter_base_url,
        model=model,
        api_key=settings.openrouter_api_key,
        max_retries=settings.llm_circuit_breaker_max_retries,
        cost_tracker=cost_tracker,
    )
