"""Cadena LCEL para T22.4 (DT-054): identificación explícita de entidades competidoras.

Paso previo a la generación del Cap 2: dado el retrieval sectorial inicial, el LLM extrae los
nombres de las empresas competidoras **presentes en la evidencia**. Esos nombres alimentan
búsquedas web dirigidas por entidad (no solo por sector) para enriquecer las fichas de la
sección 2.1. RN-001: solo se anclan entidades presentes en las fuentes; nunca se fabrican.
"""

from __future__ import annotations

import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

# Máximo de entidades a explotar en búsquedas dirigidas (cota de latencia/coste).
MAX_ENTIDADES = 8

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_ARRAY_RE = re.compile(r"\[.*?\]", re.DOTALL)

SYSTEM_PROMPT_02B = (
    "Eres un analista de inteligencia competitiva. Tu única tarea es identificar los nombres de "
    "las EMPRESAS COMPETIDORAS que aparecen EXPLÍCITAMENTE en la evidencia proporcionada para el "
    "sector {sector_gics}.\n\n"
    "REGLAS (obligatorias):\n"
    "- Devuelve SOLO los nombres de empresas presentes en la evidencia. Está prohibido inventar, "
    "inferir o completar nombres que no aparezcan textualmente.\n"
    "- No incluyas la empresa analizada ni su grupo corporativo.\n"
    "- No incluyas gremios, entes reguladores, medios ni fuentes (p. ej. Euromonitor, DANE).\n"
    "- Nombres de empresa, no de productos ni marcas genéricas.\n"
    "- Responde EXCLUSIVAMENTE con un array JSON de strings, sin texto antes ni después. "
    'Ejemplo del formato exacto: ["Empresa A", "Empresa B", "Empresa C"].\n'
    "- Si la evidencia no contiene empresas competidoras claras, responde: []"
)

USER_PROMPT_02B = (
    "EVIDENCIA RECUPERADA (única fuente permitida):\n{retrieval_competidores}\n\n"
    "Extrae los nombres de las empresas competidoras del sector {sector_gics} presentes en la "
    "evidencia. Responde solo con el array JSON."
)


def parse_entidades(raw: str) -> list[str]:
    """Extrae la lista de nombres del texto del LLM. Puro: solo depura, no fabrica (RN-001).

    Tolera fences ```json / ``` y texto alrededor del array. Deduplica sin distinguir
    mayúsculas (conservando la primera aparición), descarta vacíos y limita a MAX_ENTIDADES.
    Devuelve [] si no hay un array JSON de strings parseable.
    """
    if not raw:
        return []
    texto = raw.strip()
    m = _FENCE_RE.search(texto)
    if m:
        texto = m.group(1).strip()
    m = _ARRAY_RE.search(texto)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    out: list[str] = []
    vistos: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            continue
        nombre = item.strip()
        clave = nombre.casefold()
        if not nombre or clave in vistos:
            continue
        vistos.add(clave)
        out.append(nombre)
        if len(out) >= MAX_ENTIDADES:
            break
    return out


def build_chain_entidades(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_02B),
        ("human", USER_PROMPT_02B),
    ])
    return prompt | llm | StrOutputParser()
