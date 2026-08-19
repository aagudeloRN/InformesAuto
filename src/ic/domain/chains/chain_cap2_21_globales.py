"""Cadena LCEL para perfiles de Referentes Globales (Cap 2.1.1).

Recibe: sector_gics, candidatos (lista de nombres), chunks_context (texto RAG).
Produce: prosa bajo encabezado '### Referentes Globales'.
Modelo inyectado — nunca hardcodeado (ADR-002).
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

_SYSTEM = (
    "Eres un analista de inteligencia competitiva experto en mercados globales. "
    "Tu tarea es redactar perfiles breves (2-3 párrafos por empresa) de los referentes "
    "GLOBALES de clase mundial del sector {sector_gics}.\n\n"
    "Para cada empresa en {candidatos} que tenga contexto en las fuentes, redacta:\n"
    "- Modelo de negocio y propuesta de valor\n"
    "- Mercados clave y presencia geográfica\n"
    "- Diferenciales competitivos frente a la empresa analizada\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "- Inicia la sección con el encabezado exacto: ### Referentes Globales\n"
    "- Usa SOLO información presente en las fuentes proporcionadas. NO inventes datos.\n"
    "- Si no hay suficiente información de una empresa, omítela de la prosa.\n"
    "- Redacta en español. Cita las fuentes mediante el texto del chunk cuando sea posible.\n"
    "- No incluyas a la empresa analizada ({nombre_empresa}) en los perfiles."
)

_HUMAN = (
    "Empresa analizada: {nombre_empresa}\n"
    "Sector GICS: {sector_gics}\n"
    "Candidatos globales identificados: {candidatos}\n\n"
    "Fuentes disponibles (RAG):\n{chunks_context}\n\n"
    "Redacta los perfiles de los referentes globales con el encabezado ### Referentes Globales."
)


def build_chain_cap2_21_globales(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ])
    return prompt | llm | StrOutputParser()
