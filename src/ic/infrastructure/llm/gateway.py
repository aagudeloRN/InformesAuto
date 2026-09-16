"""LLM Gateway - Ollama y OpenRouter como BaseChatModel de LangChain (Tiers & Resiliency)."""

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
    provider_or_settings: str | Settings,
    settings_or_provider: Settings | str,
    model: str | None = None,
) -> tuple[str, str]:
    """Resuelve base_url y api_key para un provider."""
    if isinstance(provider_or_settings, Settings):
        settings = provider_or_settings
        provider = str(settings_or_provider).lower()
    else:
        provider = str(provider_or_settings).lower()
        settings = settings_or_provider  # type: ignore

    if provider == "ollama":
        return getattr(settings, "ollama_base_url", "http://localhost:11434"), "ollama"

    if provider in ("google", "gemini"):
        base_url = getattr(settings, "gemini_base_url", "https://generativelanguage.googleapis.com/v1beta/openai/")
        api_key = getattr(settings, "gemini_api_key", "") or ""
        return base_url, api_key

    base_url = getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1")
    api_key = getattr(settings, "openrouter_api_key", "") or ""
    return base_url, api_key


def build_llm(
    settings: Settings,
    cost_tracker: CostTracker | None = None,
    timeout: float = 120.0,
) -> OllamaGatewayLLM:
    """Retorna un OllamaGatewayLLM configurado para el modelo local."""
    model_name = getattr(settings, "llm_local_analytic_model", "mistral:7b")
    temp = getattr(settings, "llm_temperature", 0.0)
    return OllamaGatewayLLM(
        base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
        model=str(model_name),
        temperature=float(temp) if isinstance(temp, (int, float)) else 0.0,
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
        model = getattr(settings, "llm_api_free_alt_model", "")
        provider = getattr(settings, "llm_api_free_alt_provider", "openrouter")
    elif tier == "synth":
        model = getattr(settings, "llm_api_synth_model", "")
        provider = getattr(settings, "llm_api_synth_provider", "openrouter")
    elif tier == "paid":
        model = getattr(settings, "llm_api_paid_model", "")
        provider = getattr(settings, "llm_api_paid_provider", "openrouter")
    elif tier == "fallback":
        model = getattr(settings, "llm_api_fallback_model", "")
        provider = getattr(settings, "llm_api_fallback_provider", "openrouter")
    else:
        model = getattr(settings, "llm_api_free_model", "")
        provider = getattr(settings, "llm_api_free_provider", "openrouter")


    if not model or not isinstance(model, str):
        raise ValueError(f"Tier {tier!r} no configurado en .env")

    base_url, api_key = _provider_base_and_key(
        provider, settings, model=model
    )
    headers_str: str | None = None
    if provider == "openrouter":
        hdrs: dict[str, str] = {}
        ref = (getattr(settings, "llm_openrouter_referer", "")
           or getattr(settings, "openrouter_referer", ""))
        if ref:
            hdrs["HTTP-Referer"] = ref
        title = (getattr(settings, "llm_openrouter_title", "")
             or getattr(settings, "openrouter_title", ""))
        if title:
            hdrs["X-Title"] = title
        if hdrs:
            headers_str = ",".join(f"{k}:{v}" for k, v in hdrs.items())

    max_tokens = getattr(settings, "llm_api_max_tokens_output", None)
    if max_tokens is not None and not isinstance(max_tokens, int):
        try:
            max_tokens = int(max_tokens)
        except (ValueError, TypeError):
            max_tokens = None

    temp = getattr(settings, "llm_temperature", 0.0)
    return OpenRouterGatewayLLM(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=float(temp) if isinstance(temp, (int, float)) else 0.0,
        timeout=timeout,
        cost_tracker=cost_tracker,
        extra_headers=headers_str,
        max_tokens_output=max_tokens,
    )


def build_resilient_api_llm(
    settings: Settings,
    cost_tracker: CostTracker | None = None,
    tiers: list[ModelTier] | None = None,
    fallback: OpenRouterGatewayLLM | None = None,
    max_retries: int | None = None,
) -> ResilientChatModel:
    """Construye un ResilientChatModel a partir de los tiers configurados en Settings."""
    target_tiers: list[ModelTier] = (
        ["free", "free_alt", "synth", "paid"] if tiers is None else list(tiers)
    )

    constructed_tiers: list[OpenRouterGatewayLLM] = []
    for tier in target_tiers:
        if tier == "free":
            model_name = getattr(settings, "llm_api_free_model", "")
            if isinstance(model_name, str) and model_name:
                t = getattr(settings, "llm_api_timeout_free", 120.0)
                t_val = float(t) if isinstance(t, (int, float)) else 120.0
                constructed_tiers.append(
                    build_api_llm(settings, tier="free", cost_tracker=cost_tracker, timeout=t_val)
                )
        elif tier == "free_alt":
            model_name = getattr(settings, "llm_api_free_alt_model", "")
            if isinstance(model_name, str) and model_name:
                constructed_tiers.append(
                    build_api_llm(settings, tier="free_alt", cost_tracker=cost_tracker)
                )
        elif tier == "synth":
            model_name = getattr(settings, "llm_api_synth_model", "")
            if isinstance(model_name, str) and model_name:
                t = getattr(settings, "llm_api_timeout_synth", 120.0)
                t_val = float(t) if isinstance(t, (int, float)) else 120.0
                constructed_tiers.append(
                    build_api_llm(settings, tier="synth", cost_tracker=cost_tracker, timeout=t_val)
                )
        elif tier == "paid":
            model_name = getattr(settings, "llm_api_paid_model", "")
            if isinstance(model_name, str) and model_name:
                constructed_tiers.append(
                    build_api_llm(settings, tier="paid", cost_tracker=cost_tracker)
                )

    fallback_model = getattr(settings, "llm_api_fallback_model", "")
    if isinstance(fallback_model, str) and fallback_model:
        fb_tier = build_api_llm(settings, tier="fallback", cost_tracker=cost_tracker)
        if not any(t.model == fallback_model for t in constructed_tiers):
            constructed_tiers.append(fb_tier)


    if fallback is not None and not any(t.model == fallback.model for t in constructed_tiers):
        constructed_tiers.append(fallback)

    return ResilientChatModel(tiers=constructed_tiers)


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
    "_provider_base_and_key",
    "build_api_llm",
    "build_llm",
    "build_resilient_api_llm",
    "is_empty_generation_error",
    "is_rate_limit_error",
    "is_transient_network_error",
]
