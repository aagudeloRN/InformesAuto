"""Cadena LCEL para perfiles de Startups y Disruptores (Cap 2.1.3).

Recibe: sector_gics, nombre_empresa, locales_context (texto de StartIA),
internacionales_context (texto web). Los locales aparecen PRIMERO.
Modelo inyectado — nunca hardcodeado (ADR-002).
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

_SYSTEM = (
    "Eres un analista de inteligencia competitiva especializado en startups "
    "y empresas disruptoras. "
    "Tu tarea es redactar perfiles breves (1-2 párrafos) de las startups "
    "y disruptores del sector {sector_gics}.\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "- Inicia la sección con el encabezado exacto: ### Startups y Disruptores del sector\n"
    "- Presenta PRIMERO las startups LOCALES (colombianas/LatAm), luego las internacionales.\n"
    "- Para cada empresa describe: modelo de negocio disruptivo, propuesta de valor diferenciada.\n"
    "- Usa SOLO información presente en las fuentes. NO inventes datos.\n"
    "- No incluyas a la empresa analizada ({nombre_empresa}).\n"
    "- Redacta en español."
)

_HUMAN = (
    "Empresa analizada: {nombre_empresa}\n"
    "Sector GICS: {sector_gics}\n\n"
    "Startups LOCALES (del directorio StartIA — presentar primero):\n{locales_context}\n\n"
    "Disruptores internacionales (fuentes web — presentar después):\n{internacionales_context}\n\n"
    "Redacta los perfiles con el encabezado ### Startups y Disruptores del sector."
)


def build_chain_cap2_21_startups(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ])
    return prompt | llm | StrOutputParser()
