"""LLM Gateway - Ollama y OpenRouter como BaseChatModel de LangChain (ADR-002, DT-037)."""

from __future__ import annotations

import logging
from typing import Literal

import httpx  # noqa: F401

from ic.infrastructure.llm.gateway_errors import (
    EmptyGenerationError,
    RateLimitError,
    ResilientChatModel,
    is_empty_generation_error,
    is_rate_limit_error,
    is_transient_network_error,
)
from ic.infrastructure.llm.gateway_models import (
    OllamaGatewayLLM,
    OpenRouterGatewayLLM,
)
from ic.infrastructure.llm.gateway_pricing import (
    _PRICING,
    CallRecord,
    CostTracker,
)
from ic.shared.config import Settings

logger = logging.getLogger(__name__)

ModelTier = Literal["free", "free_alt", "synth", "paid", "fallback"]


def _provider_base_and_key(
    provider: str,
    settings: Settings,
    model: str | None = None,
) -> tuple[str, str, str | None]:
    """Resuelve base_url, api_key y headers extra para un provider."""
    if provider == "ollama":
        return settings.ollama_base_url, "ollama", None

    if provider == "google":
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        api_key = settings.gemini_api_key or ""
        return base_url, api_key, None

    if provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
        api_key = settings.openrouter_api_key or ""
        headers: dict[str, str] = {}
        if settings.openrouter_referer:
            headers["HTTP-Referer"] = settings.openrouter_referer
        if settings.openrouter_title:
            headers["X-Title"] = settings.openrouter_title
        header_str = (
            ",".join(f"{k}:{v}" for k, v in headers.items()) if headers else None
        )
        return base_url, api_key, header_str

    base_url = "https://openrouter.ai/api/v1"
    api_key = settings.openrouter_api_key or ""
    return base_url, api_key, None


def build_llm(
    settings: Settings,
    cost_tracker: CostTracker | None = None,
    timeout: float = 120.0,
) -> OllamaGatewayLLM:
    """Retorna un OllamaGatewayLLM configurado para el modelo local."""
    return OllamaGatewayLLM(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
        timeout=timeout,
        cost_tracker=cost_tracker,
    )


def build_api_llm(
    settings: Settings,
    tier: ModelTier = "free",
    cost_tracker: CostTracker | None = None,
    timeout: float = 120.0,
    model_override: str | None = None,
) -> OpenRouterGatewayLLM:
    """Retorna un OpenRouterGatewayLLM configurado segun el tier del router."""
    if model_override:
        model = model_override
        provider = "google" if "gemini" in model.lower() else "openrouter"
    elif tier == "free_alt":
        model = settings.openrouter_free_alt_model
        provider = "openrouter"
    elif tier == "synth":
        model = settings.gemini_synth_model
        provider = settings.synth_provider
    elif tier == "paid":
        model = settings.openrouter_model
        provider = "openrouter"
    elif tier == "fallback":
        model = settings.gemini_model
        provider = settings.fallback_provider
    else:
        model = settings.openrouter_free_model
        provider = "openrouter"

    base_url, api_key, headers = _provider_base_and_key(
        provider, settings, model=model
    )
    return OpenRouterGatewayLLM(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=settings.llm_temperature,
        timeout=timeout,
        cost_tracker=cost_tracker,
        extra_headers=headers,
    )


def build_resilient_api_llm(
    primary: OpenRouterGatewayLLM,
    fallback: OpenRouterGatewayLLM,
    max_retries: int = 2,
    base_backoff: float = 1.0,
) -> ResilientChatModel:
    """Construye un ResilientChatModel con reintentos y fallback."""
    return ResilientChatModel(
        primary=primary,
        fallback=fallback,
        max_retries=max_retries,
        base_backoff=base_backoff,
    )


__all__ = [
    "_PRICING",
    "CallRecord",
    "CostTracker",
    "EmptyGenerationError",
    "ModelTier",
    "OllamaGatewayLLM",
    "OpenRouterGatewayLLM",
    "RateLimitError",
    "ResilientChatModel",
    "build_api_llm",
    "build_llm",
    "build_resilient_api_llm",
    "httpx",
    "is_empty_generation_error",
    "is_rate_limit_error",
    "is_transient_network_error",
]
