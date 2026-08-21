"""Cadena LCEL para Cap 2.2 — División de Competidores (Grupos Estratégicos).

Recibe: closed_list_str, fichas_context, empresa_sector, feedback.
Produce: JSON string con {cuadrantes, intro, sintesis_incumbente, sintesis_entrante}.
Modelo inyectado — nunca hardcodeado (ADR-002).
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

_SYSTEM = (
    "Eres un analista de inteligencia competitiva experto en estrategia sectorial. "
    "Tu tarea es clasificar EXACTAMENTE las siguientes empresas competidoras en una "
    "matriz de grupos estratégicos 2×2, cruzando enfoque de mercado (Masivo/Volumen "
    "vs. Nicho/Premium) con naturaleza del modelo operativo (Jugadores Tradicionales "
    "vs. Entrantes Innovadores).\n\n"
    "LISTA CERRADA DE EMPRESAS A CLASIFICAR (no añadir ninguna otra):\n"
    "{closed_list_str}\n\n"
    "ATRIBUTOS DE FICHA DE CADA EMPRESA (usa solo esta información):\n"
    "{fichas_context}\n\n"
    "SECTOR DE LA EMPRESA ANALIZADA:\n"
    "{empresa_sector}\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. Clasifica ÚNICAMENTE las empresas de la lista cerrada. PROHIBIDO añadir nuevas marcas.\n"
    "2. Cada empresa debe quedar en EXACTAMENTE UN cuadrante.\n"
    "3. Si no tienes datos suficientes para clasificar un atributo, indícalo como "
    "'Dato no disponible en fuentes consultadas' en la síntesis narrativa; pero "
    "igual asigna la empresa al cuadrante más probable según los datos disponibles.\n"
    "4. Responde ÚNICAMENTE con el JSON especificado. Sin texto adicional antes o después.\n\n"
    "{feedback}"
)

_HUMAN = (
    "Clasifica las empresas de la lista cerrada en la matriz 2×2 y redacta la síntesis "
    "de presión competitiva.\n\n"
    'Responde SOLO con este JSON (sin markdown fences):\n'
    '{{\n'
    '  "cuadrantes": {{\n'
    '    "masivo_tradicional": ["..."],\n'
    '    "masivo_innovador":   ["..."],\n'
    '    "nicho_tradicional":  ["..."],\n'
    '    "nicho_innovador":    []\n'
    '  }},\n'
    '  "intro": "Párrafo introductorio (1-2 oraciones).",\n'
    '  "sintesis_incumbente": "Análisis de la defensa del incumbente.",\n'
    '  "sintesis_entrante": "Análisis del ataque del entrante y la servitización."\n'
    '}}'
)


def build_chain_cap2_22_division(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ])
    return prompt | llm | StrOutputParser()
