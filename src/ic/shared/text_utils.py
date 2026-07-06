"""Utilidades de texto compartidas."""

import re

from ic.shared.types import WebResult

_CJK_RE = re.compile(
    "["
    "一-鿿"   # CJK Unified Ideographs
    "㐀-䶿"   # CJK Extension A
    "　-〿"   # CJK Symbols and Punctuation
    "぀-ヿ"   # Hiragana / Katakana
    "가-힯"   # Korean (Hangul Syllables)
    "＀-￯"   # Halfwidth / Fullwidth Forms
    "]"
)


def has_cjk_characters(text: str, threshold: int = 5) -> bool:
    """Devuelve True si el texto contiene al menos `threshold` caracteres CJK.

    Umbral > 1 para no rechazar textos con una sola mención de marca asiática.
    """
    return len(_CJK_RE.findall(text)) >= threshold


def format_web_results_as_context(results: list[WebResult], max_chars_per_result: int = 1500) -> str:
    """Formatea una lista de WebResult como contexto numerado para el LLM."""
    parts = []
    for i, r in enumerate(results, 1):
        meta = r.metadatos or {}
        año = meta.get("año", "s.f.")
        fuente = meta.get("fuente_nombre", "fuente desconocida")
        header = f"[{i}] {r.title} ({fuente}, {año})\nURL: {r.url}"
        body = r.content[:max_chars_per_result] if r.content else r.snippet[:300]
        parts.append(f"{header}\n{body}")
    return "\n\n---\n\n".join(parts)
