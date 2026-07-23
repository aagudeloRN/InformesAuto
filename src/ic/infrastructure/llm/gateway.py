"""LLM Gateway — Ollama (local) y OpenRouter (API) como BaseChatModel de LangChain (ADR-002)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from tenacity import retry, stop_after_attempt, wait_exponential

from ic.shared.config import Settings

logger = logging.getLogger(__name__)

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
    tiempo_ollama_s: float = 0.0


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

    def add_ollama_call(
        self, modelo: str, tiempo_s: float, tokens_in: int = 0, tokens_out: int = 0
    ) -> CallRecord:
        record = CallRecord(
            modelo=modelo, tokens_in=tokens_in, tokens_out=tokens_out,
            costo_usd=0.0, tiempo_ollama_s=tiempo_s,
        )
        self._calls.append(record)
        return record

    def total_ollama_time_s(self) -> float:
        return sum(r.tiempo_ollama_s for r in self._calls)

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
    cost_tracker: CostTracker | None = None

    model_config = {"arbitrary_types_allowed": True}

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
        def _call() -> dict:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": ollama_msgs, "stream": False, "keep_alive": 0},  # noqa: E501
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()

        data = _call()
        content = data["message"]["content"]

        if self.cost_tracker is not None:
            tiempo_s = data.get("total_duration", 0) / 1e9
            tokens_in = data.get("prompt_eval_count", 0)
            tokens_out = data.get("eval_count", 0)
            self.cost_tracker.add_ollama_call(
                modelo=self.model, tiempo_s=tiempo_s,
                tokens_in=tokens_in, tokens_out=tokens_out,
            )

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
                logger.error(
                    "OpenRouter respuesta inesperada (sin choices, model=%s): %s",
                    self.model,
                    data,
                )
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
                        logger.error(
                            "OpenRouter stream error (model=%s): %s",
                            self.model,
                            chunk_data["error"],
                        )
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


_RATE_LIMIT_PATTERNS = ("rate limit", "resourceexhausted", "quota", "429", "too many requests")
_TRANSIENT_NETWORK_PATTERNS = ("incomplete chunked read", "peer closed connection")


def is_rate_limit_error(exc: Exception) -> bool:
    """Detecta errores de rate-limit/quota de OpenRouter (HTTP 429 o error en el body).

    OpenRouter puede indicar rate-limit de dos formas:
    1. HTTP 429 en el status (sí dispara raise_for_status).
    2. HTTP 200 con {"error": {...}} en el body (no dispara raise_for_status — DT-021).
    Ambos terminan como RuntimeError o HTTPStatusError con texto diagnóstico.
    """
    text = str(exc).lower()
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return True
    return any(p in text for p in _RATE_LIMIT_PATTERNS)


def is_transient_network_error(exc: Exception) -> bool:
    """Detecta cortes de red transitorios que justifican fallback de tier (DT-029).

    El tier free de OpenRouter puede cerrar la conexión con el cuerpo a medias
    (RemoteProtocolError: incomplete chunked read) sin que sea un rate-limit.
    En ese caso tiene sentido intentar el siguiente tier en lugar de abortar.
    """
    if isinstance(
        exc, (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.ReadTimeout)
    ):
        return True
    text = str(exc).lower()
    return any(p in text for p in _TRANSIENT_NETWORK_PATTERNS)


class RateLimitError(RuntimeError):
    """Excepción explícita de rate-limit para que ResilientChatModel la capture."""


class ResilientChatModel(BaseChatModel):
    """LLM con fallback automático de tier ante rate-limit de OpenRouter (DT-021, T15.3).

    Recibe una lista ordenada de modelos (free→free_alt→synth→paid). Si el tier
    actual lanza un error de rate-limit, cae al siguiente. Si todos fallan, re-raise
    el último error. Todos los tiers NO-rate-limit (5xx, timeout) se propagan inmediatamente.
    """

    tiers: list[Any]  # list[OpenRouterGatewayLLM] — Any para inyectabilidad en tests

    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        return "resilient-openrouter"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_exc: Exception | None = None
        for i, tier_llm in enumerate(self.tiers):
            try:
                return tier_llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
            except Exception as exc:
                if is_rate_limit_error(exc):
                    logger.warning(
                        "Rate-limit en tier %d (model=%s): %s. Intentando fallback.",
                        i, tier_llm.model, exc,
                    )
                    last_exc = exc
                    continue
                if is_transient_network_error(exc):
                    logger.warning(
                        "Error de red transitorio en tier %d (model=%s): %s. Intentando fallback.",
                        i, tier_llm.model, exc,
                    )
                    last_exc = exc
                    continue
                raise  # error no-recuperable → propagar inmediatamente
        raise last_exc  # type: ignore[misc]

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        last_exc: Exception | None = None
        for i, tier_llm in enumerate(self.tiers):
            try:
                yield from tier_llm._stream(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                return
            except Exception as exc:
                if is_rate_limit_error(exc):
                    logger.warning(
                        "Rate-limit en tier %d (model=%s, stream): %s. Intentando fallback.",
                        i, tier_llm.model, exc,
                    )
                    last_exc = exc
                    continue
                if is_transient_network_error(exc):
                    logger.warning(
                        "Error de red transitorio en tier %d (model=%s, stream): %s. "
                        "Intentando fallback.",
                        i, tier_llm.model, exc,
                    )
                    last_exc = exc
                    continue
                raise
        raise last_exc  # type: ignore[misc]


def build_llm(
    settings: Settings, cost_tracker: CostTracker | None = None
) -> OllamaGatewayLLM:
    """Construye el LLM local (Ollama). Usar para embeddings, Cap 1 y GICS."""
    return OllamaGatewayLLM(
        base_url=settings.ollama_base_url,
        model=settings.llm_local_analytic_model,
        max_retries=settings.llm_circuit_breaker_max_retries,
        timeout=settings.llm_local_timeout,
        cost_tracker=cost_tracker,
    )


_TIER_TIMEOUT_ATTR: dict[ModelTier, str] = {
    "free": "llm_api_timeout_free",
    "free_alt": "llm_api_timeout_free_alt",
    "synth": "llm_api_timeout_synth",
    "paid": "llm_api_timeout_paid",
}


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
    timeout_attr = _TIER_TIMEOUT_ATTR.get(tier, "llm_api_timeout_free")
    timeout = getattr(settings, timeout_attr, 180)
    return OpenRouterGatewayLLM(
        base_url=settings.openrouter_base_url,
        model=model,
        api_key=settings.openrouter_api_key,
        max_retries=settings.llm_circuit_breaker_max_retries,
        timeout=timeout,
        cost_tracker=cost_tracker,
    )


def build_resilient_api_llm(
    settings: Settings,
    tiers: list[ModelTier] | None = None,
    cost_tracker: CostTracker | None = None,
) -> ResilientChatModel:
    """Construye un LLM resiliente con fallback automático entre tiers (T15.3, DT-021).

    Orden default: free → free_alt → synth → paid.
    Solo incluye tiers con modelo configurado en .env.
    """
    tier_order: list[ModelTier] = tiers or ["free", "free_alt", "synth", "paid"]
    built: list[OpenRouterGatewayLLM] = []
    for t in tier_order:
        try:
            built.append(build_api_llm(settings, tier=t, cost_tracker=cost_tracker))
        except ValueError:
            pass  # tier no configurado → se omite silenciosamente
    if not built:
        raise ValueError(
            "No hay ningún tier de API configurado en .env. "
            "Configura al menos LLM_API_FREE_MODEL."
        )
    return ResilientChatModel(tiers=built)
