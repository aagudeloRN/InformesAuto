"""Cadena LCEL genérica para párrafos introductorios de capítulos (Fase 5F).

DT-055: el modelo local (con modo *thinking*) filtraba andamiaje del prompt en el
párrafo intro ("We need to produce a paragraph intro…", "Answer", "(In)"). El
saneador `sanitize_intro` retira ese meta-texto SIN fabricar contenido (RN-001):
solo elimina bloques de razonamiento y líneas meta en inglés; si tras sanear no
queda intro, devuelve "" (el llamador antepone el intro condicionalmente).
"""

import re

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

SYSTEM_INTRO = (
    "Eres un redactor de informes ejecutivos. Escribe SOLO en español latino neutro. "
    "Responde ÚNICAMENTE con el párrafo pedido: sin razonamiento, sin preámbulo, "
    "sin traducciones, sin etiquetas como 'Answer' o 'Respuesta', y sin texto en inglés."
)

USER_INTRO = (
    "Escribe un párrafo introductorio de 2 a 3 oraciones para el capítulo "
    "'{titulo}' del informe de inteligencia competitiva de {empresa}. "
    "El capítulo desarrolla el siguiente contenido:\n\n{resumen_cap}\n\n"
    "La introducción debe contextualizar el propósito del capítulo para un lector "
    "ejecutivo. Sin títulos, sin viñetas, sin meta-comentarios. "
    "Entrega directamente el párrafo, nada más."
)

# Bloque de razonamiento del modelo (qwen3 y similares).
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Marcador explícito de respuesta: se conserva solo lo que sigue al último.
_ANSWER_MARKER_RE = re.compile(
    r"(?:^|\n)\s*(?:final\s+answer|answer|respuesta)\s*[:\-–]?\s*",
    re.IGNORECASE,
)
# Líneas de razonamiento/meta en inglés (el intro válido va en español).
_REASONING_LINE_RE = re.compile(
    r"^\s*(?:"
    r"we\s+(?:need|should|must|have|want|can)\b|"
    r"let'?s\b|let\s+me\b|okay\b|ok\b|sure\b|first\b|now\b|"
    r"i\s+(?:will|need|should|'ll|am)\b|here'?s\b|"
    r"(?:the\s+)?(?:task|user|prompt|instruction|paragraph)\b"
    r")",
    re.IGNORECASE,
)
# Paréntesis-meta sueltos, p. ej. "(In)" o "(In English)".
_PAREN_META_RE = re.compile(r"^\s*\(\s*in\b.*?\)\s*$", re.IGNORECASE)


def sanitize_intro(text: str) -> str:
    """Retira andamiaje/razonamiento del intro sin fabricar contenido (RN-001).

    Elimina bloques ``<think>``, recorta hasta el último marcador 'Answer/Respuesta'
    y descarta líneas de razonamiento meta en inglés. Devuelve el párrafo limpio, o
    "" si tras sanear no queda intro utilizable.
    """
    if not text:
        return ""
    t = _THINK_RE.sub("", text)
    matches = list(_ANSWER_MARKER_RE.finditer(t))
    if matches:
        t = t[matches[-1].end() :]
    kept: list[str] = []
    for line in t.splitlines():
        s = line.strip()
        if not s:
            kept.append("")
            continue
        if _REASONING_LINE_RE.match(s) or _PAREN_META_RE.match(s):
            continue
        kept.append(line)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return cleaned


def build_chain_intro(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_INTRO),
            ("human", USER_INTRO),
        ]
    )
    return prompt | llm | StrOutputParser() | RunnableLambda(sanitize_intro)
