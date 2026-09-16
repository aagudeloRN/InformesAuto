"""Fake LLM model for integration tests."""

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class EndlessFakeChatModel(FakeListChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        content = "## Seccion\nAnalisis sintetico [1].\n- Tendencia: Crecimiento."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
