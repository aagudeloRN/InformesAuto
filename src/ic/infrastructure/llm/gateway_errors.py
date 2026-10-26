"""Manejo de errores, rate-limits y modelo resiliente con fallback (DT-037)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

logger = logging.getLogger(__name__)

_RATE_LIMIT_PATTERNS = ("rate limit", "resourceexhausted", "quota", "429", "too many requests")
_TRANSIENT_NETWORK_PATTERNS = ("incomplete chunked read", "peer closed connection")


def is_rate_limit_error(exc: Exception) -> bool:
    """Detecta errores de rate-limit/quota de OpenRouter (HTTP 429 o error en el body).

    OpenRouter puede indicar rate-limit de dos formas:
    1. HTTP 429 en el status (sí dispara raise_for_status).
    2. HTTP 200 con {"error": {...}} en el body (no dispara raise_for_status — DT-021).
    Ambos terminan como RuntimeError o HTTPStatusError con texto diagnóstico.
    """
    text = str(exc).lower()
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return True
    return any(p in text for p in _RATE_LIMIT_PATTERNS)


def is_transient_network_error(exc: Exception) -> bool:
    """Detecta cortes de red transitorios que justifican fallback de tier (DT-029).

    El tier free de OpenRouter puede cerrar la conexión con el cuerpo a medias
    (RemoteProtocolError: incomplete chunked read) sin que sea un rate-limit.
    En ese caso tiene sentido intentar el siguiente tier en lugar de abortar.
    """
    if isinstance(
        exc, (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.ReadTimeout)
    ):
        return True
    text = str(exc).lower()
    return any(p in text for p in _TRANSIENT_NETWORK_PATTERNS)


def is_model_unavailable_error(exc: Exception) -> bool:
    """Detecta HTTP 404 de OpenRouter: el modelo/endpoint ya no existe para esta cuenta.

    Pasa con los modelos ``:free`` cuando el proveedor retira el despliegue (2026-10-26). Justifica
    fallback de tier: reintentar el mismo modelo no sirve.
    """
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404


class RateLimitError(RuntimeError):
    """Excepción explícita de rate-limit para que ResilientChatModel la capture."""


class EmptyGenerationError(RuntimeError):
    """Generación vacía/None o truncada por longitud (free tier degradado, 2026-08-03).

    ResilientChatModel la trata como recuperable → cae al siguiente tier (fallback). Evita el crash
    por ``AIMessage(content=None)`` y convierte la fragilidad del modelo en degradación recuperable.
    """


def is_empty_generation_error(exc: Exception) -> bool:
    """True si el fallo es una generación vacía/truncada → justifica fallback de tier."""
    return isinstance(exc, EmptyGenerationError)


class ResilientChatModel(BaseChatModel):
    """LLM con fallback automático de tier ante rate-limit de OpenRouter (DT-021, T15.3).

    Recibe una lista ordenada de modelos (free→free_alt→synth→paid). Si el tier
    actual lanza un error de rate-limit, cae al siguiente. Si todos fallan, re-raise
    el último error. Todos los tiers NO-rate-limit (5xx, timeout) se propagan inmediatamente.
    """

    tiers: list[Any]  # list[OpenRouterGatewayLLM] — Any para inyectabilidad en tests

    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        return "resilient-openrouter"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_exc: Exception | None = None
        for i, tier_llm in enumerate(self.tiers):
            try:
                return tier_llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
            except Exception as exc:
                # Recuperables → cae al siguiente tier: rate-limit, red transitoria, o generación
                # vacía/truncada (free tier degradado, 2026-08-03).
                if (
                    is_rate_limit_error(exc)
                    or is_transient_network_error(exc)
                    or is_empty_generation_error(exc)
                    or is_model_unavailable_error(exc)
                ):
                    logger.warning(
                        "Fallo recuperable en tier %d (model=%s): %s. Intentando fallback.",
                        i,
                        tier_llm.model,
                        exc,
                    )
                    last_exc = exc
                    continue
                raise  # error no-recuperable → propagar inmediatamente
        # Todos los tiers agotados. Si fue por generación vacía, DEGRADAR a content="" en vez de
        # crashear: Fase 1 (commit_best) caerá al capítulo cacheado bueno. Otro caso → re-raise.
        if is_empty_generation_error(last_exc):
            logger.error(
                "Todos los tiers devolvieron generación vacía → se degrada a content='' (%s)",
                last_exc,
            )
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])
        raise last_exc  # type: ignore[misc]

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        last_exc: Exception | None = None
        for i, tier_llm in enumerate(self.tiers):
            try:
                yield from tier_llm._stream(messages, stop=stop, run_manager=run_manager, **kwargs)
                return
            except Exception as exc:
                if is_rate_limit_error(exc):
                    logger.warning(
                        "Rate-limit en tier %d (model=%s, stream): %s. Intentando fallback.",
                        i,
                        tier_llm.model,
                        exc,
                    )
                    last_exc = exc
                    continue
                if is_model_unavailable_error(exc):
                    logger.warning(
                        "Modelo no disponible (404) en tier %d (model=%s, stream): %s. "
                        "Intentando fallback.",
                        i,
                        tier_llm.model,
                        exc,
                    )
                    last_exc = exc
                    continue
                if is_transient_network_error(exc):
                    logger.warning(
                        "Error de red transitorio en tier %d (model=%s, stream): %s. "
                        "Intentando fallback.",
                        i,
                        tier_llm.model,
                        exc,
                    )
                    last_exc = exc
                    continue
                raise
        raise last_exc  # type: ignore[misc]
