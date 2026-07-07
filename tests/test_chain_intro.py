"""Tests para la cadena LCEL de párrafos introductorios (chain_intro)."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables import Runnable

from ic.domain.chains.chain_intro import build_chain_intro

_SAMPLE_INPUT = {
    "titulo": "Análisis Competitivo",
    "empresa": "Noel S.A.S.",
    "resumen_cap": "Este capítulo examina los competidores globales y regionales en el sector de alimentos.",  # noqa: E501
}


def test_chain_intro_builds():
    fake_llm = FakeListChatModel(responses=["Intro de prueba."])
    chain = build_chain_intro(fake_llm)
    assert isinstance(chain, Runnable)


def test_chain_intro_invoke_returns_string():
    fake_llm = FakeListChatModel(responses=["Párrafo introductorio de prueba."])
    chain = build_chain_intro(fake_llm)
    result = chain.invoke(_SAMPLE_INPUT)
    assert isinstance(result, str)
    assert len(result) > 0


def test_chain_intro_propagates_llm_response():
    expected = "Este es el párrafo introductorio generado por el modelo."
    fake_llm = FakeListChatModel(responses=[expected])
    chain = build_chain_intro(fake_llm)
    result = chain.invoke(_SAMPLE_INPUT)
    assert result == expected


@pytest.mark.slow
def test_chain_intro_slow_ollama():
    import socket

    try:
        s = socket.create_connection(("127.0.0.1", 11434), timeout=2)
        s.close()
    except OSError:
        pytest.skip("Ollama no disponible")

    from ic.infrastructure.llm.gateway import build_llm
    from ic.shared.config import get_settings

    settings = get_settings()
    llm = build_llm(settings)
    chain = build_chain_intro(llm)
    result = chain.invoke(_SAMPLE_INPUT)
    assert isinstance(result, str)
    assert len(result) > 30
