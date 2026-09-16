"""Tests T15.3 + DT-029 — Resiliencia free-tier: detector 429/red + ResilientChatModel."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

# ---------------------------------------------------------------------------
# is_rate_limit_error — detector 429
# ---------------------------------------------------------------------------


def test_detects_http_429_status():
    from ic.infrastructure.llm.gateway import is_rate_limit_error

    resp = MagicMock()
    resp.status_code = 429
    exc = httpx.HTTPStatusError("429", request=MagicMock(), response=resp)
    assert is_rate_limit_error(exc) is True


def test_detects_rate_limit_in_body_text():
    from ic.infrastructure.llm.gateway import is_rate_limit_error

    exc = RuntimeError("OpenRouter error: {'code': 429, 'message': 'Rate limit exceeded'}")
    assert is_rate_limit_error(exc) is True


def test_detects_resourceexhausted_in_body():
    from ic.infrastructure.llm.gateway import is_rate_limit_error

    exc = RuntimeError("OpenRouter error: ResourceExhausted 32/32 requests per minute")
    assert is_rate_limit_error(exc) is True


def test_detects_quota_in_body():
    from ic.infrastructure.llm.gateway import is_rate_limit_error

    exc = RuntimeError("quota exceeded for this model")
    assert is_rate_limit_error(exc) is True


def test_does_not_flag_regular_5xx():
    from ic.infrastructure.llm.gateway import is_rate_limit_error

    resp = MagicMock()
    resp.status_code = 500
    exc = httpx.HTTPStatusError("500", request=MagicMock(), response=resp)
    assert is_rate_limit_error(exc) is False


def test_does_not_flag_timeout():
    from ic.infrastructure.llm.gateway import is_rate_limit_error

    exc = httpx.TimeoutException("timeout")
    assert is_rate_limit_error(exc) is False


# ---------------------------------------------------------------------------
# ResilientChatModel — fallback de tier
# ---------------------------------------------------------------------------


def _make_tier(content="respuesta del tier"):
    """Crea un mock de OpenRouterGatewayLLM que devuelve contenido exitosamente."""
    tier = MagicMock()
    tier.model = "test-model"
    tier._generate.return_value = ChatResult(
        generations=[ChatGeneration(message=AIMessage(content=content))]
    )
    return tier


def _make_failing_tier(exc: Exception):
    """Crea un mock de OpenRouterGatewayLLM que lanza la excepción dada."""
    tier = MagicMock()
    tier.model = "failing-model"
    tier._generate.side_effect = exc
    return tier


def _resilient(tiers):
    from ic.infrastructure.llm.gateway import ResilientChatModel

    return ResilientChatModel(tiers=tiers)


def test_resilient_uses_first_tier_on_success():
    """Si el primer tier responde OK, no se toca el fallback."""
    t1 = _make_tier("respuesta de t1")
    t2 = _make_tier("respuesta de t2")

    model = _resilient([t1, t2])
    result = model._generate([HumanMessage(content="hola")])

    assert result.generations[0].message.content == "respuesta de t1"
    t2._generate.assert_not_called()


def test_resilient_falls_to_second_tier_on_rate_limit():
    """Ante un 429 en el primer tier, cae al segundo y devuelve su respuesta."""
    rate_exc = RuntimeError("rate limit exceeded")
    t1 = _make_failing_tier(rate_exc)
    t2 = _make_tier("respuesta fallback")

    model = _resilient([t1, t2])
    result = model._generate([HumanMessage(content="hola")])

    t1._generate.assert_called_once()
    t2._generate.assert_called_once()
    assert result.generations[0].message.content == "respuesta fallback"


def test_resilient_propagates_non_rate_limit_immediately():
    """Un error 500 (no rate-limit) se propaga sin intentar el fallback."""
    resp = MagicMock()
    resp.status_code = 500
    http_exc = httpx.HTTPStatusError("500", request=MagicMock(), response=resp)

    t1 = _make_failing_tier(http_exc)
    t2 = _make_tier("no debería llegar aquí")

    model = _resilient([t1, t2])
    with pytest.raises(httpx.HTTPStatusError):
        model._generate([HumanMessage(content="hola")])

    t2._generate.assert_not_called()


def test_resilient_raises_after_all_tiers_exhausted():
    """Si todos los tiers lanzan rate-limit, re-raise el último error."""

    exc1 = RuntimeError("rate limit tier1")
    exc2 = RuntimeError("rate limit tier2")
    t1 = _make_failing_tier(exc1)
    t2 = _make_failing_tier(exc2)

    model = _resilient([t1, t2])
    with pytest.raises(RuntimeError, match="rate limit tier2"):
        model._generate([HumanMessage(content="hola")])


def test_resilient_falls_through_multiple_rate_limits():
    """Cascada: t1 429 → t2 429 → t3 OK."""
    t1 = _make_failing_tier(RuntimeError("rate limit"))
    t2 = _make_failing_tier(RuntimeError("resourceexhausted"))
    t3 = _make_tier("ok desde t3")

    model = _resilient([t1, t2, t3])
    result = model._generate([HumanMessage(content="hola")])

    assert result.generations[0].message.content == "ok desde t3"
    t1._generate.assert_called_once()
    t2._generate.assert_called_once()
    t3._generate.assert_called_once()


# ---------------------------------------------------------------------------
# build_resilient_api_llm — construcción
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# is_transient_network_error — DT-029
# ---------------------------------------------------------------------------


def test_detects_remote_protocol_error():
    from ic.infrastructure.llm.gateway import is_transient_network_error

    exc = httpx.RemoteProtocolError(
        "peer closed connection without sending complete message body (incomplete chunked read)"
    )
    assert is_transient_network_error(exc) is True


def test_detects_read_error():
    from ic.infrastructure.llm.gateway import is_transient_network_error

    exc = httpx.ReadError("connection reset by peer")
    assert is_transient_network_error(exc) is True


def test_detects_connect_error():
    from ic.infrastructure.llm.gateway import is_transient_network_error

    exc = httpx.ConnectError("connection refused")
    assert is_transient_network_error(exc) is True


def test_detects_read_timeout():
    from ic.infrastructure.llm.gateway import is_transient_network_error

    exc = httpx.ReadTimeout("timed out", request=MagicMock())
    assert is_transient_network_error(exc) is True


def test_detects_incomplete_chunked_read_text():
    from ic.infrastructure.llm.gateway import is_transient_network_error

    exc = RuntimeError("incomplete chunked read")
    assert is_transient_network_error(exc) is True


def test_does_not_flag_rate_limit_as_transient():
    from ic.infrastructure.llm.gateway import is_transient_network_error

    exc = RuntimeError("rate limit exceeded")
    assert is_transient_network_error(exc) is False


def test_does_not_flag_http_500_as_transient():
    from ic.infrastructure.llm.gateway import is_transient_network_error

    resp = MagicMock()
    resp.status_code = 500
    exc = httpx.HTTPStatusError("500", request=MagicMock(), response=resp)
    assert is_transient_network_error(exc) is False


def test_resilient_falls_to_second_tier_on_remote_protocol_error():
    """RemoteProtocolError en tier 1 → fallback a tier 2 (DT-029)."""
    network_exc = httpx.RemoteProtocolError(
        "peer closed connection without sending complete message body (incomplete chunked read)"
    )
    t1 = _make_failing_tier(network_exc)
    t2 = _make_tier("respuesta desde tier 2")

    model = _resilient([t1, t2])
    result = model._generate([HumanMessage(content="hola")])

    t1._generate.assert_called_once()
    t2._generate.assert_called_once()
    assert result.generations[0].message.content == "respuesta desde tier 2"


def test_resilient_propagates_http_500_without_fallback():
    """HTTP 500 sigue propagándose inmediatamente (sin fallback)."""
    resp = MagicMock()
    resp.status_code = 500
    http_exc = httpx.HTTPStatusError("500", request=MagicMock(), response=resp)

    t1 = _make_failing_tier(http_exc)
    t2 = _make_tier("no debería llegar aquí")

    model = _resilient([t1, t2])
    with pytest.raises(httpx.HTTPStatusError):
        model._generate([HumanMessage(content="hola")])

    t2._generate.assert_not_called()


# ---------------------------------------------------------------------------
# build_resilient_api_llm — construcción
# ---------------------------------------------------------------------------


def test_build_resilient_api_llm_skips_unconfigured_tiers():
    """Los tiers sin modelo en .env se omiten silenciosamente."""
    from ic.infrastructure.llm.gateway import ResilientChatModel, build_resilient_api_llm

    settings = MagicMock()
    settings.openrouter_base_url = "https://openrouter.ai/api/v1"
    settings.openrouter_api_key = "sk-test"
    settings.llm_circuit_breaker_max_retries = 3
    settings.llm_api_free_model = "free-model"
    settings.llm_api_free_alt_model = ""  # no configurado
    settings.llm_api_synth_model = "synth-model"
    settings.llm_api_paid_model = ""  # no configurado
    settings.llm_api_timeout_free = 180
    settings.llm_api_timeout_synth = 180

    model = build_resilient_api_llm(settings)

    assert isinstance(model, ResilientChatModel)
    assert len(model.tiers) == 2  # free + synth, free_alt y paid omitidos
    assert model.tiers[0].model == "free-model"
    assert model.tiers[1].model == "synth-model"
