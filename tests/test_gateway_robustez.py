"""Robustez del gateway LLM (2026-08-03): guard de generación vacía + provider Gemini + fallback.

Motivado por crashes reales del free tier (content=None / finish_reason "length"). Unit, sin red.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ic.infrastructure.llm.gateway import (
    EmptyGenerationError,
    ResilientChatModel,
    _provider_base_and_key,
    build_api_llm,
    build_resilient_api_llm,
    is_empty_generation_error,
)
from ic.shared.config import Settings


def _tier_ok(content="ok"):
    t = MagicMock()
    t.model = "ok-model"
    t._generate.return_value = ChatResult(
        generations=[ChatGeneration(message=AIMessage(content=content))]
    )
    return t


def _tier_fail(exc):
    t = MagicMock()
    t.model = "fail-model"
    t._generate.side_effect = exc
    return t


# --------------------------------------------------------------------------- guard empty generation


def test_is_empty_generation_error():
    assert is_empty_generation_error(EmptyGenerationError("vacío")) is True
    assert is_empty_generation_error(RuntimeError("otra cosa")) is False


def test_resilient_cae_al_fallback_ante_generacion_vacia():
    t1 = _tier_fail(EmptyGenerationError("content=None"))
    t2 = _tier_ok("rescatado por el fallback")
    model = ResilientChatModel(tiers=[t1, t2])
    result = model._generate([HumanMessage(content="hola")])
    t1._generate.assert_called_once()
    t2._generate.assert_called_once()
    assert result.generations[0].message.content == "rescatado por el fallback"


def test_todos_los_tiers_vacios_degradan_a_string_vacio_sin_crashear():
    # Antes: crash por AIMessage(content=None). Ahora: degrada a "" → Fase 1 cae al caché.
    t1 = _tier_fail(EmptyGenerationError("content=None"))
    t2 = _tier_fail(EmptyGenerationError("finish_reason=length"))
    model = ResilientChatModel(tiers=[t1, t2])
    result = model._generate([HumanMessage(content="hola")])
    assert result.generations[0].message.content == ""


# --------------------------------------------------------------------------- provider + fallback


def test_provider_resolver_gemini_vs_openrouter():
    s = Settings(
        openrouter_base_url="https://or",
        openrouter_api_key="ORK",
        gemini_base_url="https://gemini",
        gemini_api_key="GK",
    )
    assert _provider_base_and_key(s, "openrouter") == ("https://or", "ORK")
    assert _provider_base_and_key(s, "gemini") == ("https://gemini", "GK")
    # provider desconocido → cae a openrouter (no rompe .env existentes)
    assert _provider_base_and_key(s, "desconocido") == ("https://or", "ORK")


def test_build_api_llm_synth_usa_gemini_y_max_tokens():
    s = Settings(
        llm_api_synth_model="gemini-2.5-flash",
        llm_api_synth_provider="gemini",
        gemini_base_url="https://gemini",
        gemini_api_key="GK",
        llm_api_max_tokens_output=32000,
    )
    m = build_api_llm(s, tier="synth")
    assert m.base_url == "https://gemini"
    assert m.api_key == "GK"
    assert m.model == "gemini-2.5-flash"
    assert m.max_tokens_output == 32000


def test_build_resilient_anexa_el_fallback():
    s = Settings(
        openrouter_api_key="ORK",
        llm_api_free_model="nemotron:free",
        llm_api_fallback_model="openrouter/free",
    )
    model = build_resilient_api_llm(s, tiers=["free"])
    modelos = [t.model for t in model.tiers]
    assert "nemotron:free" in modelos
    assert "openrouter/free" in modelos  # fallback anexado al final
    assert modelos[-1] == "openrouter/free"
