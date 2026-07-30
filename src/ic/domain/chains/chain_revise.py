"""Cadena LCEL de revisión de capítulo (DT-059/T3) — el "optimizer" del loop.

Genérica y reusada por todos los capítulos (web e integración): reescribe un borrador
corrigiendo las carencias que el juez señaló (`faltantes`), **anclada en la evidencia**
provista y sin inventar (RN-001: solo lo sustentado; ausencias declaradas, no rellenadas).

El modelo se inyecta como `Runnable` (ADR-002). Los caps web pasan evidencia **enriquecida**
por una re-búsqueda dirigida (Reflexion con herramientas); los de integración pasan la
evidencia ya recuperada (solo re-síntesis).
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

SYSTEM_PROMPT_REVISE = (
    "Eres un consultor senior de inteligencia competitiva. Recibes un borrador del capítulo "
    "'{capitulo_nombre}', la lista de carencias detectadas por un evaluador y la evidencia "
    "disponible. Tu tarea es reescribir el capítulo COMPLETO corrigiendo esas carencias.\n\n"
    "REGLAS (obligatorias):\n"
    "- Corrige cada carencia listada, respetando la estructura y el tono esperados del capítulo.\n"
    "- Ancla toda afirmación en la EVIDENCIA proporcionada. Está prohibido inventar cifras, "
    "nombres o citas. Si un dato pedido no está en la evidencia, decláralo como ausente en vez "
    "de fabricarlo.\n"
    "- Conserva lo que ya estaba bien; no elimines contenido correcto al corregir.\n"
    "- Mantén las citas (Autor, año) existentes que la evidencia respalde; no cites nombres de "
    "archivo.\n"
    "- Devuelve SOLO el texto del capítulo reescrito, sin comentarios sobre los cambios.\n\n"
    "CRITERIOS DE CALIDAD DEL CAPÍTULO:\n{criterios_capitulo}"
)

USER_PROMPT_REVISE = (
    "BORRADOR ACTUAL:\n{borrador_actual}\n\n"
    "CARENCIAS A CORREGIR:\n{faltantes}\n\n"
    "EVIDENCIA DISPONIBLE (única fuente permitida):\n{evidencia}\n\n"
    "Reescribe el capítulo '{capitulo_nombre}' corrigiendo las carencias, anclado en la evidencia."
)


def build_chain_revise(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_REVISE),
        ("human", USER_PROMPT_REVISE),
    ])
    return prompt | llm | StrOutputParser()
