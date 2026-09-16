"""Cadena LCEL para DT-062: descubrimiento de competidores de CLASE MUNDIAL vía LLM.

Motor principal del componente global (2.1.1). El LLM tiene alto recall de actores globales
famosos y bajo riesgo de alucinar el *nombre* (Nestlé, Yili, Fonterra…), mientras que el corpus
EMIS está sesgado a lo local y no los menciona. Esta cadena solo produce **candidatos** (nombres);
la corroboración por web (RN-001/TIER 4) decide cuáles se anclan como ``verificado`` — ver
``domain/kb/corroboracion.py`` y ``domain/use_cases/discover_globales.py``.

Espejo de ``chain_02b_entidades``: parser puro (no fabrica; dedup; cota), modelo inyectado
(ADR-002, nunca hardcodeado). El nombre lo aporta el LLM; los atributos y la evidencia, la web.
"""

from __future__ import annotations

import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

# Máximo de candidatos globales a corroborar (cota de latencia/coste: cada uno dispara una
# búsqueda web dirigida). El recall global famoso cabe holgado en esta cota.
MAX_GLOBALES = 12

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_ARRAY_RE = re.compile(r"\[.*?\]", re.DOTALL)

SYSTEM_PROMPT_02C = (
    "Eres un analista de inteligencia competitiva con conocimiento de los líderes GLOBALES de cada "
    "industria. Tu tarea es listar las empresas de CLASE MUNDIAL (alcance global, referencia "
    "internacional) que COMPITEN con una empresa cuyos productos y servicios son:\n"
    "{productos}\n\n"
    "El sector general es {sector_gics} (úsalo solo como límite de dominio, NO amplíes a toda la "
    "industria: enfócate en los productos/servicios descritos arriba).\n\n"
    "REGLAS (obligatorias):\n"
    "- Solo empresas REALES y reconocidas GLOBALMENTE como líderes en ESOS productos/servicios.\n"
    "- NO incluyas jugadores de otras actividades del sector que NO compitan en esos productos.\n"
    "- NO incluyas jugadores puramente locales o regionales (esos son otro componente).\n"
    "- NO incluyas gremios, entes reguladores, medios ni fuentes (p. ej. Euromonitor, DANE).\n"
    "- Nombres de empresa, no de productos ni marcas genéricas.\n"
    "- Responde EXCLUSIVAMENTE con un array JSON de strings, sin texto antes ni después. "
    'Ejemplo del formato exacto: ["Empresa A", "Empresa B", "Empresa C"].\n'
    "- Si no conoces líderes globales claros para esos productos, responde: []"
)

USER_PROMPT_02C = (
    "Sector (límite de dominio): {sector_gics}.\n"
    "Productos y servicios de la empresa analizada:\n{productos}\n\n"
    "Lista las empresas de clase mundial que compiten en esos productos/servicios. "
    "Responde solo con el array JSON."
)


def parse_pares_globales(raw: str) -> list[str]:
    """Extrae la lista de nombres globales del texto del LLM. Puro: depura, no fabrica (RN-001).

    Tolera fences ```json / ``` y texto alrededor del array. Deduplica sin distinguir
    mayúsculas (conservando la primera aparición), descarta vacíos y limita a MAX_GLOBALES.
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
        if len(out) >= MAX_GLOBALES:
            break
    return out


def build_chain_pares_globales(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_02C),
            ("human", USER_PROMPT_02C),
        ]
    )
    return prompt | llm | StrOutputParser()
