"""LLM Gateway — wrapper httpx sobre Ollama como BaseChatModel de LangChain (ADR-002)."""

from typing import Any, Iterator

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from tenacity import retry, stop_after_attempt, wait_exponential

from ic.shared.config import Settings


class OllamaGatewayLLM(BaseChatModel):
    base_url: str
    model: str
    max_retries: int = 3
    timeout: int = 120

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
        def _call() -> str:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": ollama_msgs, "stream": False},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        content = _call()
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
            json={"model": self.model, "messages": ollama_msgs, "stream": True},
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                import json

                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
                    if run_manager:
                        run_manager.on_llm_new_token(token, chunk=chunk)
                    yield chunk
                if data.get("done"):
                    break


class CostTracker:
    def __init__(self, budget_limit: float) -> None:
        self._budget_limit = budget_limit
        self._total_cost: float = 0.0
        self._tokens_in: int = 0
        self._tokens_out: int = 0

    def add_local_call(self, tokens_in: int, tokens_out: int) -> None:
        self._tokens_in += tokens_in
        self._tokens_out += tokens_out

    def within_budget(self) -> bool:
        return self._total_cost <= self._budget_limit

    def total_cost(self) -> float:
        return self._total_cost

    def total_tokens(self) -> tuple[int, int]:
        return self._tokens_in, self._tokens_out


def build_llm(settings: Settings) -> OllamaGatewayLLM:
    return OllamaGatewayLLM(
        base_url=settings.ollama_base_url,
        model=settings.llm_local_analytic_model,
        max_retries=settings.llm_circuit_breaker_max_retries,
    )
