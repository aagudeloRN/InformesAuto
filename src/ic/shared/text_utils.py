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


_REFUSAL_PATTERNS = (
    "lo siento",
    "no es posible",
    "no puedo",
    "no me es posible",
    "no se puede determinar",
    "no se puede generar",
    "no se pudo",
    "no dispongo de",
    "no cuento con",
    "no hay suficiente informacion",
    "no se proporcion",
    "with the sources provided",  # el free a veces rehúsa en inglés
    "i cannot",
    "i'm sorry",
)
_AUSENCIA_MARKER = "dato no disponible"


def _sin_acentos_lower(text: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(c) != "Mn"
    )


def is_llm_refusal(text: str, ausencia_ratio: float = 0.5) -> bool:
    """True si el capítulo es una negativa del LLM en vez de contenido real (DT-064/T5).

    Dos señales, conservadoras para no marcar un capítulo legítimo con alguna ausencia puntual:
    - una **frase de rechazo** típica ("no es posible con las fuentes…", "lo siento…"), o
    - un texto corto dominado por "Dato no disponible" (ratio de líneas ≥ `ausencia_ratio`).

    El free/gratuito a veces rehúsa por variabilidad; se trata como fallo (igual que
    `has_cjk_characters`) para disparar retry/escalada en vez de emitir el rechazo.
    """
    if not text or not text.strip():
        return True
    norm = _sin_acentos_lower(text)
    if any(p in norm for p in _REFUSAL_PATTERNS):
        return True
    lineas = [ln for ln in text.splitlines() if ln.strip()]
    if len(lineas) <= 8:  # solo en capítulos cortos: uno largo con 1-2 ausencias es legítimo
        ausentes = sum(1 for ln in lineas if _AUSENCIA_MARKER in _sin_acentos_lower(ln))
        if lineas and ausentes / len(lineas) >= ausencia_ratio:
            return True
    return False


_HEADING_RE = re.compile(r"^\s*#{1,6}\s")
_FENCE_RE = re.compile(r"^\s*```")
_JSON_START_RE = re.compile(r"^\s*[{\[]", re.MULTILINE)


def strip_preamble(texto: str) -> str:
    """Elimina preámbulo espurio antes del contenido real del capítulo (DT-UI04c).

    Algunos modelos anteponen razonamiento, cercas de código (```` ``` ````) o JSON antes de
    la prosa/encabezado real, contaminando el .docx. Este saneo es **conservador**: solo poda
    lo que hay antes del primer encabezado markdown si ese preámbulo contiene cercas de código o
    JSON (ruido inequívoco); nunca descarta prosa legítima como un párrafo introductorio. Además
    desenvuelve una cerca de código que envuelva todo el documento. Puro y determinista.
    """
    if not texto:
        return texto
    lines = texto.split("\n")
    heading_idx = next((i for i, ln in enumerate(lines) if _HEADING_RE.match(ln)), None)
    dangling_fence = False
    if heading_idx:  # >0: hay encabezado y algo lo precede
        preamble = "\n".join(lines[:heading_idx])
        if "```" in preamble or _JSON_START_RE.search(preamble):
            dangling_fence = "```" in preamble  # el bloque envolvía el documento → limpiar cierre
            lines = lines[heading_idx:]
    # Desenvolver cerca de código que envuelve el documento completo (```markdown … ```).
    while lines and (not lines[0].strip() or _FENCE_RE.match(lines[0])):
        dangling_fence = dangling_fence or bool(_FENCE_RE.match(lines[0]))
        lines.pop(0)
    if dangling_fence:
        while lines and (not lines[-1].strip() or _FENCE_RE.match(lines[-1])):
            lines.pop()
    return "\n".join(lines).strip("\n")


def format_web_results_as_context(
    results: list[WebResult], max_chars_per_result: int = 1500
) -> str:
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
