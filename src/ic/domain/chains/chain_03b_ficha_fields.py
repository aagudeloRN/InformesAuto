"""Cadena LCEL para DT-066/B2: rellenar campos de ficha faltantes desde evidencia (hole-filler).

En el flujo determinista de la sección 2.1, las celdas con dato salen del KB; los **huecos** (campos
sin valor de un competidor anclado) se rellenan aquí, uno a uno, con una tarea de EXTRACCIÓN
estructurada: dado el nombre del competidor y la evidencia RAG, devolver un JSON
``{clave: valor|null}`` solo para los campos pedidos. Tarea constreñida → menos variable.

RN-001: solo se extrae lo que la evidencia soporta; ``null`` (o frase de ausencia) → el campo se
omite, NUNCA se fabrica ni se persiste. El parseo reusa ``_es_valor_util`` del parser de fichas para
que un hueco rellenado no reintroduzca el "veneno" del KB (frases de ausencia) que DT-065 purgó.
"""

from __future__ import annotations

import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.domain.kb.ficha_parser import _es_valor_util

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)

SYSTEM_PROMPT_03B = (
    "Eres un analista de inteligencia competitiva. Tu única tarea es EXTRAER datos de la ficha de "
    "UNA empresa competidora a partir de la evidencia proporcionada, sin redactar ni opinar.\n\n"
    "REGLAS (obligatorias):\n"
    "- Devuelve un valor SOLO si está sustentado en la evidencia. Está prohibido inventar, inferir "
    "o completar datos que no aparezcan en las fuentes.\n"
    "- Si un campo no está soportado por la evidencia, su valor debe ser null. No escribas frases "
    'como "Dato no disponible": usa null.\n'
    "- Cada valor: 1–2 frases concretas, con cifras cuando la evidencia las dé (empleados, países, "
    "US$, marcas). Sin adjetivos vacíos.\n"
    "- IDIOMA: español latino neutro. Prohibido otro idioma.\n"
    "- Responde EXCLUSIVAMENTE con un objeto JSON cuyas claves sean EXACTAMENTE las claves pedidas "
    "(las de la lista CAMPOS A EXTRAER), sin texto antes ni después."
)

USER_PROMPT_03B = (
    "EMPRESA: {nombre}\n"
    "SECTOR: {sector_gics}\n\n"
    "EVIDENCIA RECUPERADA (única fuente permitida):\n{evidencia_rag}\n\n"
    "CAMPOS A EXTRAER (usa EXACTAMENTE estas claves en el JSON; valor null si la evidencia no lo "
    "soporta):\n{campos_faltantes}\n\n"
    "Responde solo con el objeto JSON."
)


def parse_ficha_fields(raw: str, claves_validas: set[str]) -> dict[str, str]:
    """Extrae los campos rellenados del texto del LLM. Puro: depura, no fabrica (RN-001).

    Tolera fences ```json / ``` y texto alrededor del objeto. Conserva solo las claves pedidas cuyo
    valor sea un string útil (``_es_valor_util``: descarta null, vacío y frases de ausencia).
    Devuelve {} si no hay objeto JSON parseable.
    """
    if not raw:
        return {}
    texto = raw.strip()
    m = _FENCE_RE.search(texto)
    if m:
        texto = m.group(1).strip()
    m = _OBJ_RE.search(texto)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for clave, valor in data.items():
        if clave not in claves_validas or not isinstance(valor, str):
            continue
        v = valor.strip()
        if v and _es_valor_util(v):
            out[clave] = v
    return out


def build_chain_ficha_fields(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_03B),
            ("human", USER_PROMPT_03B),
        ]
    )
    return prompt | llm | StrOutputParser()
