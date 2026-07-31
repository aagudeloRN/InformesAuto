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
_NON_ALNUM = re.compile(r"[^\w\s]", re.UNICODE)
# Sufijos societarios que el LLM suele añadir al nombre ("JBS S.A.", "Tyson Foods, Inc.") pero que
# la prosa web rara vez repite literalmente → si se exigen, dan falsos negativos. Se quitan del
# candidato (needle) antes de buscar. Espejo mínimo de `normalize_entity` (no se importa de
# infrastructure/ para no cruzar capas; RN-001: solo normaliza, no fabrica).
_LEGAL_SUFFIXES = re.compile(
    r"\b(s a s|s a|ltda|s l|inc|corp|corporation|company|co|llc|plc|gmbh|ag|n v|c a|"
    r"e u|holdings?|group|international)\b"
)


def _fold(texto: str) -> str:
    """Minúsculas, sin acentos, sin puntuación y espacios colapsados. Puro.

    Se aplica a ambos lados del match (candidato y texto web) para que "Tyson Foods, Inc." y
    "tyson foods inc" plieguen igual. Helper local (no importa ``normalize_entity`` de
    ``infrastructure/`` para no cruzar capas).
    """
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    sin_punct = _NON_ALNUM.sub(" ", sin_acentos)
    return _WS.sub(" ", sin_punct).strip()


def _core(nombre: str) -> str:
    """Núcleo del nombre: folded, sin artículo inicial ni sufijos societarios. Puro."""
    s = _fold(nombre)
    s = _LEGAL_SUFFIXES.sub(" ", s)
    s = re.sub(r"^the\b", " ", s)
    return _WS.sub(" ", s).strip()


def contar_corroboracion(nombre: str, textos: list[str]) -> int:
    """Nº de textos web cuyo contenido menciona el núcleo del nombre del candidato. Puro.

    Cada texto es un resultado web distinto: el conteo aproxima "cuántas fuentes independientes
    mencionan al candidato". El match es por límite de palabra (evita que "jbs" case dentro de otra
    palabra) y tolerante a sufijos societarios/puntuación. Un nombre vacío no corrobora nada.
    """
    core = _core(nombre)
    if not core:
        return 0
    needle = f" {core} "
    return sum(1 for t in textos if needle in f" {_fold(t)} ")


def es_corroborado(hits: int, min_hits: int) -> bool:
    """True si el nº de menciones alcanza el umbral (≥). Puro."""
    return hits >= min_hits
