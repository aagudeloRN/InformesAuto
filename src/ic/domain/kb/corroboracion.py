"""Gate de corroboración web de candidatos globales (DT-062) — puro, sin BD ni modelo.

RN-001/TIER 4: un nombre recomendado por el LLM (``fuente=llm``) NO se cita hasta que la evidencia
web lo corrobora. Este módulo cuenta, de forma determinista, en cuántos resultados web aparece el
nombre del candidato; el caso de uso decide el umbral (``discover_globales_min_corrob``).

Determinista y testeable con fixtures: solo cuenta menciones, no fabrica ni pondera.
"""

from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def _fold(texto: str) -> str:
    """Minúsculas, sin acentos y espacios colapsados. Puro (para match nombre↔texto web).

    Helper local (no importa ``normalize_entity`` de ``infrastructure/`` para no cruzar capas):
    aquí basta un plegado laxo; no quita sufijos societarios (queremos substring en prosa web).
    """
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return _WS.sub(" ", sin_acentos).strip()


def contar_corroboracion(nombre: str, textos: list[str]) -> int:
    """Nº de textos cuyo contenido (folded) contiene el nombre (folded). Puro.

    Cada texto es un resultado web distinto: el conteo aproxima "cuántas fuentes independientes
    mencionan al candidato". Un nombre vacío no corrobora nada.
    """
    objetivo = _fold(nombre)
    if not objetivo:
        return 0
    return sum(1 for t in textos if objetivo in _fold(t))


def es_corroborado(hits: int, min_hits: int) -> bool:
    """True si el nº de menciones alcanza el umbral (≥). Puro."""
    return hits >= min_hits
