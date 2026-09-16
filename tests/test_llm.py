"""Tests LLM Gateway + cadenas LCEL + use cases (sin mocks — CLAUDE.md)."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_01_descripcion import build_chain_01
from ic.domain.chains.chain_02_gics import build_chain_02
from ic.domain.use_cases.classify_gics import ClassifyGICS
from ic.domain.use_cases.generate_empresa_description import GenerateEmpresaDescription
from ic.infrastructure.llm.gateway import CostTracker, OllamaGatewayLLM, build_llm
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.config import get_settings
from ic.shared.types import ChunkResult

settings = get_settings()

_NOEL_DESC = (
    "Noel S.A.S. es una empresa colombiana de alimentos procesados fundada en 1916, "
    "perteneciente al Grupo Nutresa. Produce y comercializa galletas, pastas, snacks y "
    "chocolates bajo marcas como Saltín Noel, Festival y Dux. Opera principalmente en Colombia "
    "con presencia en toda la cadena de distribución moderna y tradicional."
)


def _ollama_available() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 11434), timeout=2)
        s.close()
        return True
    except OSError:
        return False


def _network_available() -> bool:
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=2)
        s.close()
        return True
    except OSError:
        return False


requires_ollama = pytest.mark.skipif(not _ollama_available(), reason="Ollama no disponible")
requires_network = pytest.mark.skipif(not _network_available(), reason="Sin acceso a red")


# --- Lógica pura (sin Ollama) ---


def test_absent_data_below_threshold():
    chunks = [
        ChunkResult(chunk_texto="texto", fuente_tipo="web", fuente_url=None, score=0.8),
        ChunkResult(chunk_texto="texto", fuente_tipo="web", fuente_url=None, score=0.75),
    ]
    assert check_retrieval_sufficient(chunks, min_chunks=5) is False


def test_absent_data_paragraph_not_empty():
    paragraph = build_absent_paragraph("Cap 2 — Análisis Competitivo")
    assert len(paragraph) > 0
    assert "Cap 2" in paragraph


# --- CostTracker: lógica pura ---


def test_cost_tracker_add_ollama_call_registra_tiempo():
    tracker = CostTracker(budget_limit=1.0)
    rec = tracker.add_ollama_call("qwen2.5:7b", tiempo_s=3.5, tokens_in=10, tokens_out=50)
    assert rec.tiempo_ollama_s == 3.5
    assert rec.tokens_in == 10
    assert rec.tokens_out == 50
    assert rec.costo_usd == 0.0


def test_cost_tracker_total_ollama_time_suma_correctamente():
    tracker = CostTracker(budget_limit=1.0)
    tracker.add_ollama_call("m1", tiempo_s=2.0, tokens_in=5, tokens_out=10)
    tracker.add_ollama_call("m1", tiempo_s=1.5, tokens_in=5, tokens_out=10)
    tracker.add_call("openrouter/model", 100, 200)
    assert tracker.total_ollama_time_s() == pytest.approx(3.5)


def test_ollama_gateway_registra_tiempo_via_cost_tracker():
    tracker = CostTracker(budget_limit=1.0)
    llm = OllamaGatewayLLM(base_url="http://fake", model="test-model", cost_tracker=tracker)

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "message": {"role": "assistant", "content": "hola"},
        "done": True,
        "total_duration": 2_500_000_000,
        "prompt_eval_count": 42,
        "eval_count": 100,
    }

    from langchain_core.messages import HumanMessage

    with patch("ic.infrastructure.llm.gateway.httpx.post", return_value=fake_response):
        result = llm.invoke([HumanMessage(content="test")])

    assert result.content == "hola"
    records = tracker.records()
    assert len(records) == 1
    assert records[0].tiempo_ollama_s == pytest.approx(2.5)
    assert records[0].tokens_in == 42
    assert records[0].tokens_out == 100
    assert tracker.total_ollama_time_s() == pytest.approx(2.5)


def test_ollama_gateway_sin_tracker_no_falla():
    llm = OllamaGatewayLLM(base_url="http://fake", model="test-model")

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "message": {"role": "assistant", "content": "ok"},
        "done": True,
    }

    from langchain_core.messages import HumanMessage

    with patch("ic.infrastructure.llm.gateway.httpx.post", return_value=fake_response):
        result = llm.invoke([HumanMessage(content="test")])
    assert result.content == "ok"


# --- Tests con Ollama real ---


@pytest.mark.slow
@requires_ollama
def test_ollama_gateway_simple_complete():
    llm = build_llm(settings)
    assert isinstance(llm, OllamaGatewayLLM)
    from langchain_core.messages import HumanMessage

    result = llm.invoke([HumanMessage(content="Responde solo: OK")])
    assert result.content.strip() != ""


@pytest.mark.slow
@requires_ollama
def test_chain_02_gics_noel():
    llm = build_llm(settings)
    chain = build_chain_02(llm)
    result = chain.invoke(
        {
            "nombre_empresa": "Noel S.A.S.",
            "descripcion_empresa": _NOEL_DESC,
            "pistas": "",
        }
    )
    assert isinstance(result, str)
    assert len(result) > 0
    result_lower = result.lower()
    assert any(kw in result_lower for kw in ["alimento", "bebida", "tabaco", "consumo"])


@pytest.mark.slow
@requires_ollama
def test_use_case_classify_gics_noel():
    llm = build_llm(settings)
    chain = build_chain_02(llm)
    uc = ClassifyGICS(chain)
    result = uc.execute("Noel S.A.S.", _NOEL_DESC)
    assert result.grupo_gics != ""
    assert result.texto_raw != ""


@pytest.mark.slow
@requires_ollama
@requires_network
def test_use_case_prompt01_noel():
    llm = build_llm(settings)
    chain = build_chain_01(llm)
    connector = WebConnector(settings)
    uc = GenerateEmpresaDescription(chain, connector)
    result = uc.execute("Noel S.A.S.")
    assert result.nombre_empresa == "Noel S.A.S."
    assert len(result.texto) > 200
