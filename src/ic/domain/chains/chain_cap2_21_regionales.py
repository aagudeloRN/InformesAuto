"""Cadena LCEL para perfiles de Referentes Regionales LatAm/Colombia (Cap 2.1.2).

Recibe: sector_gics, nombre_empresa, empresas_emis (lista), chunks_emis_context, chunks_web_context.
Produce: prosa bajo '### Referentes Regionales LatAm/Colombia'.
Fuente primaria: EMIS. Web solo como complemento.
Modelo inyectado — nunca hardcodeado (ADR-002).
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

_SYSTEM = (
    "Eres un analista de inteligencia competitiva especializado en mercados de LatAm y Colombia. "
    "Tu tarea es redactar perfiles breves (2-3 párrafos) de los referentes REGIONALES "
    "(LatAm/Colombia) del sector {sector_gics}.\n\n"
    "Empresas identificadas en fuentes EMIS: {empresas_emis}\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "- Inicia la sección con el encabezado exacto: ### Referentes Regionales LatAm/Colombia\n"
    "- Basa los perfiles PRINCIPALMENTE en los chunks EMIS. El contexto web es secundario.\n"
    "- Usa SOLO información presente en las fuentes. NO inventes datos.\n"
    "- Si una empresa del listado no tiene contexto suficiente en EMIS, omítela.\n"
    "- No incluyas a la empresa analizada ({nombre_empresa}) en los perfiles.\n"
    "- Redacta en español."
)

_HUMAN = (
    "Empresa analizada: {nombre_empresa}\n"
    "Sector GICS: {sector_gics}\n"
    "Empresas en fuentes EMIS: {empresas_emis}\n\n"
    "Fuentes EMIS (primarias):\n{chunks_emis_context}\n\n"
    "Fuentes web complementarias:\n{chunks_web_context}\n\n"
    "Redacta los perfiles con el encabezado ### Referentes Regionales LatAm/Colombia."
)


def build_chain_cap2_21_regionales(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            ("human", _HUMAN),
        ]
    )
    return prompt | llm | StrOutputParser()
