"""Modulo de precios y seguimiento de costos de tokens (DT-037 / DT-040)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Precios en USD por token (in, out). Fuente: Google I Studio / OpenRouter (Sep 2026).
_PRICING: dict[str, tuple[float, float]] = {
    "nvidia/nemotron-3-super-120b-a12b:free": (0.0, 0.0),
    "nvidia/nemotron-3-ultra-550b-a55b:free": (0.0, 0.0),
    "openai/gpt-oss-120b:free": (0.0, 0.0),
    "google/gemma-3-27b-it": (0.10 / 1_000_000, 0.20 / 1_000_000),
    "google/gemma-3-12b-it": (0.05 / 1_000_000, 0.10 / 1_000_000),
    # Gemini pricing (Google I Studio, Sep 2026)
    "gemini-2.5-flash-lite": (0.075 / 1_000_000, 0.30 / 1_000_000),
    "gemini-2.5-flash": (0.075 / 1_000_000, 0.30 / 1_000_000),
    "gemini-2.5-pro": (1.25 / 1_000_000, 10.0 / 1_000_000),
}


@dataclass
class CallRecord:
    modelo: str
    tokens_in: int
    tokens_out: int
    costo_usd: float | None
    tiempo_ollama_s: float = 0.0


class CostTracker:
    def __init__(self, budget_limit: float) -> None:
        self._budget_limit = budget_limit
        self._calls: list[CallRecord] = field(default_factory=list)
        self._calls = []

    def add_call(self, modelo: str, tokens_in: int, tokens_out: int) -> CallRecord:
        costo: float | None = None
        if modelo in _PRICING:
            precio_in, precio_out = _PRICING[modelo]
            costo = tokens_in * precio_in + tokens_out * precio_out
        elif modelo.endswith(":free"):
            costo = 0.0
        elif modelo.startswith("gemini-"):
            # Fallback para modelos Gemini no catalogados explícitamente (usando tarifa flash-lite)
            precio_in, precio_out = _PRICING["gemini-2.5-flash-lite"]
            costo = tokens_in * precio_in + tokens_out * precio_out
        else:
            logger.warning(
                "Modelo LLM desconocido para cálculo de costos: %s. Registrando costo_usd=None.",
                modelo,
            )
            costo = None

        record = CallRecord(
            modelo=modelo, tokens_in=tokens_in, tokens_out=tokens_out, costo_usd=costo
        )
        self._calls.append(record)
        return record

    def add_local_call(self, tokens_in: int, tokens_out: int) -> None:
        """Compatibilidad con código legado — las llamadas locales no tienen costo."""
        self._calls.append(
            CallRecord(modelo="local", tokens_in=tokens_in, tokens_out=tokens_out, costo_usd=0.0)
        )

    def add_ollama_call(
        self, modelo: str, tiempo_s: float, tokens_in: int = 0, tokens_out: int = 0
    ) -> CallRecord:
        record = CallRecord(
            modelo=modelo,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            costo_usd=0.0,
            tiempo_ollama_s=tiempo_s,
        )
        self._calls.append(record)
        return record

    def total_ollama_time_s(self) -> float:
        return sum(r.tiempo_ollama_s for r in self._calls)

    def within_budget(self) -> bool:
        return self.total_cost() <= self._budget_limit

    def total_cost(self) -> float:
        return sum(r.costo_usd for r in self._calls if r.costo_usd is not None)

    def has_unknown_pricing(self) -> bool:
        return any(r.costo_usd is None for r in self._calls)

    def total_tokens(self) -> tuple[int, int]:
        return (
            sum(r.tokens_in for r in self._calls),
            sum(r.tokens_out for r in self._calls),
        )

    def records(self) -> list[CallRecord]:
        return list(self._calls)
