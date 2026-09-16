"""Modelos de chat para Ollama y OpenRouter compatibles con LangChain (DT-037)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from tenacity import retry, stop_after_attempt, wait_exponential

from ic.infrastructure.llm.gateway_errors import EmptyGenerationError
from ic.infrastructure.llm.gateway_pricing import CostTracker

logger = logging.getLogger(__name__)


class OllamaGatewayLLM(BaseChatModel):
    base_url: str
    model: str
    max_retries: int = 3
    timeout: int = 120
    cost_tracker: CostTracker | None = None

    model_config = {"arbitrary_types_allowed": True}

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
        def _call() -> dict:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": ollama_msgs,
                    "stream": False,
                    "keep_alive": 0,
                },  # noqa: E501
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()

        data = _call()
        content = data["message"]["content"]

        if self.cost_tracker is not None:
            tiempo_s = data.get("total_duration", 0) / 1e9
            tokens_in = data.get("prompt_eval_count", 0)
            tokens_out = data.get("eval_count", 0)
            self.cost_tracker.add_ollama_call(
                modelo=self.model,
                tiempo_s=tiempo_s,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

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
            json={"model": self.model, "messages": ollama_msgs, "stream": True, "keep_alive": 0},
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
                    if run_manager:
                        run_manager.on_llm_new_token(token, chunk=chunk)
                    yield chunk
                if data.get("done"):
                    break


class OpenRouterGatewayLLM(BaseChatModel):
    """Gateway httpx para OpenRouter (API OpenAI-compatible). Registra uso de tokens."""

    base_url: str
    model: str
    api_key: str
    max_retries: int = 3
    timeout: int = 180
    cost_tracker: CostTracker | None = None
    # Red de seguridad ALTA (no cap que trunque): acota la generación desbocada sin cortar síntesis
    # largas legítimas (~30 páginas ingeridas → salidas de varios miles de tokens son normales).
    max_tokens_output: int = 32000

    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        return "openrouter-gateway"

    def _to_openai_messages(self, messages: list[BaseMessage]) -> list[dict]:
        _TYPE_MAP = {"system": "system", "human": "user", "ai": "assistant"}
        return [{"role": _TYPE_MAP[m.type], "content": m.content} for m in messages]

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.cost_tracker and not self.cost_tracker.within_budget():
            raise RuntimeError(
                f"Presupuesto agotado (${self.cost_tracker.total_cost():.4f} USD). "
                "Aumentar LLM_BUDGET_LIMIT_USD en .env para continuar."
            )

        payload = {
            "model": self.model,
            "messages": self._to_openai_messages(messages),
            "max_tokens": self.max_tokens_output,
        }

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(min=2, max=30),
            reraise=True,
        )
        def _call() -> dict:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/aagudeloRN/informes-ic",
                    "X-Title": "InformesAuto-IC",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            # OpenRouter puede devolver HTTP 200 con {"error": {...}} cuando el modelo
            # no está disponible o hay rate-limit. Esto NO dispara raise_for_status().
            if "error" in data:
                err = data["error"]
                logger.warning("OpenRouter error en body (model=%s): %s", self.model, err)
                raise RuntimeError(f"OpenRouter error: {err}")
            if "choices" not in data or not data["choices"]:
                logger.error(
                    "OpenRouter respuesta inesperada (sin choices, model=%s): %s",
                    self.model,
                    data,
                )
                raise RuntimeError(f"OpenRouter sin 'choices' (model={self.model}): {data}")
            # Guard anti-crash (2026-08-03): el free tier (proveedor único) a veces devuelve
            # content=None o finish_reason "length"/null (generación desbocada/truncada). Antes eso
            # llegaba a AIMessage(content=None) → ValidationError → crash. Ahora es recuperable:
            # reintenta aquí y, si agota, ResilientChatModel cae al fallback.
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content")
            finish = choice.get("finish_reason")
            if content is None or (isinstance(content, str) and not content.strip()):
                raise EmptyGenerationError(
                    f"content vacío/None (model={self.model}, finish_reason={finish})"
                )
            if finish == "length":
                raise EmptyGenerationError(f"generación truncada por longitud (model={self.model})")
            return data

        data = _call()
        content = data["choices"][0]["message"]["content"]

        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        if self.cost_tracker:
            self.cost_tracker.add_call(self.model, tokens_in, tokens_out)

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        if self.cost_tracker and not self.cost_tracker.within_budget():
            raise RuntimeError("Presupuesto agotado.")

        payload = {
            "model": self.model,
            "messages": self._to_openai_messages(messages),
            "stream": True,
        }

        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/aagudeloRN/informes-ic",
                "X-Title": "InformesAuto-IC",
            },
            json=payload,
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    if "error" in chunk_data:
                        logger.error(
                            "OpenRouter stream error (model=%s): %s",
                            self.model,
                            chunk_data["error"],
                        )
                        raise RuntimeError(f"OpenRouter stream error: {chunk_data['error']}")
                    if "choices" not in chunk_data or not chunk_data["choices"]:
                        continue
                    delta = chunk_data["choices"][0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
                        if run_manager:
                            run_manager.on_llm_new_token(token, chunk=chunk)
                        yield chunk
