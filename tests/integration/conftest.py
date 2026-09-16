"""Fixtures y configuracion para tests de integracion (US1, US2, US3)."""

import socket

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class EndlessFakeChatModel(FakeListChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        content = "## Seccion\nAnalisis sintetico [1].\n- Tendencia: Crecimiento."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


@pytest.fixture
def fake_chat_model():
    return EndlessFakeChatModel(responses=[])


def is_service_available(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def postgres_available() -> bool:
    return is_service_available("localhost", 5434) or is_service_available("127.0.0.1", 5432)


@pytest.fixture(scope="session")
def ollama_available() -> bool:
    return is_service_available("127.0.0.1", 11434)
