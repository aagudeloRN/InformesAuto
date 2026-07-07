"""Tests para CostTracker y OpenRouterGatewayLLM (gateway Etapa B)."""

import pytest

from ic.infrastructure.llm.gateway import (
    _PRICING,
    CostTracker,
    build_api_llm,
    build_llm,
)
from ic.shared.config import get_settings

settings = get_settings()


# ── CostTracker ────────────────────────────────────────────────────────────────

def test_cost_tracker_local_calls_are_free():
    tracker = CostTracker(budget_limit=1.0)
    tracker.add_local_call(tokens_in=1000, tokens_out=500)
    assert tracker.total_cost() == 0.0
    assert tracker.within_budget()


def test_cost_tracker_free_model_is_zero():
    tracker = CostTracker(budget_limit=1.0)
    modelo = "nvidia/nemotron-3-super-120b-a12b:free"
    tracker.add_call(modelo, tokens_in=5000, tokens_out=2000)
    assert tracker.total_cost() == 0.0
    assert tracker.within_budget()


def test_cost_tracker_paid_model_calculates_cost():
    tracker = CostTracker(budget_limit=1.0)
    modelo = "google/gemma-3-27b-it"
    price_in, price_out = _PRICING[modelo]
    tracker.add_call(modelo, tokens_in=10_000, tokens_out=4_000)
    expected = 10_000 * price_in + 4_000 * price_out
    assert abs(tracker.total_cost() - expected) < 1e-10


def test_cost_tracker_budget_enforcement():
    tracker = CostTracker(budget_limit=0.001)
    modelo = "google/gemma-3-27b-it"
    # Simular llamadas hasta superar el presupuesto
    for _ in range(5):
        tracker.add_call(modelo, tokens_in=10_000, tokens_out=4_000)
    assert not tracker.within_budget()
    assert tracker.total_cost() > 0.001


def test_cost_tracker_accumulates_multiple_calls():
    tracker = CostTracker(budget_limit=10.0)
    tracker.add_local_call(500, 200)
    tracker.add_call("nvidia/nemotron-3-ultra-550b-a55b:free", 8000, 3000)
    tracker.add_call("google/gemma-3-27b-it", 5000, 1000)
    assert tracker.total_tokens() == (500 + 8000 + 5000, 200 + 3000 + 1000)
    assert len(tracker.records()) == 3


def test_cost_tracker_records_include_all_fields():
    tracker = CostTracker(budget_limit=1.0)
    record = tracker.add_call("google/gemma-3-27b-it", tokens_in=1000, tokens_out=500)
    assert record.modelo == "google/gemma-3-27b-it"
    assert record.tokens_in == 1000
    assert record.tokens_out == 500
    assert record.costo_usd >= 0.0


# ── Pricing table ──────────────────────────────────────────────────────────────

def test_pricing_table_has_free_nemotron_models():
    assert "nvidia/nemotron-3-super-120b-a12b:free" in _PRICING
    assert "nvidia/nemotron-3-ultra-550b-a55b:free" in _PRICING
    assert _PRICING["nvidia/nemotron-3-super-120b-a12b:free"] == (0.0, 0.0)
    assert _PRICING["nvidia/nemotron-3-ultra-550b-a55b:free"] == (0.0, 0.0)


def test_pricing_table_gemma_is_cheap():
    price_in, price_out = _PRICING["google/gemma-3-27b-it"]
    # Verificar que no supere $1/MTok en ninguna dirección
    assert price_in < 1.0 / 1_000_000
    assert price_out < 1.0 / 1_000_000


# ── build_api_llm factory ──────────────────────────────────────────────────────

def test_build_api_llm_raises_if_model_not_configured():
    """Si .env no tiene los modelos API, build_api_llm debe lanzar ValueError."""
    if settings.llm_api_free_model:
        pytest.skip("LLM_API_FREE_MODEL está configurado en .env")
    with pytest.raises(ValueError, match="no configurado en .env"):
        build_api_llm(settings, tier="free")


def test_build_llm_returns_ollama_gateway():
    from ic.infrastructure.llm.gateway import OllamaGatewayLLM
    llm = build_llm(settings)
    assert isinstance(llm, OllamaGatewayLLM)
    assert llm.model == settings.llm_local_analytic_model
