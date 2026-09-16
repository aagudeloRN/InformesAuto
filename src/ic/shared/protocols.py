"""Protocolos estructurales para el dominio — sin dependencias de librerías externas.

Permite que domain/use_cases/ anote tipos de cadenas LLM sin importar LangChain
directamente (Constitution II: agnosticismo de dependencias).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class InvokableChain(Protocol):
    """Contrato mínimo de una cadena LLM inyectable en use cases del dominio."""

    def invoke(self, payload: dict[str, Any]) -> Any: ...
