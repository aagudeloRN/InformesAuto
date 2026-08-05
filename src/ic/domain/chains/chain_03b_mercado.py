"""Cadena LCEL para la sección 2.3 Mercado (Cap 2 — Análisis Competitivo).

Implementa el patrón Noel (source_prompts 4/5): tamaño de mercado, segmentos y una
tabla de mercado por región. Es N1, se ensambla dentro del Capítulo 2 entre 2.2 y 2.4
(ver assembler.py). RN-001 preservada: sin datos → "Dato no disponible en fuentes
consultadas." (DT-044, T21.6).
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.infrastructure.citation.apa_formatter import format_chunks_with_meta
from ic.shared.types import ChunkResult

SYSTEM_PROMPT_03B = (
    "Eres un analista senior de inteligencia de mercado con más de 10 años dimensionando "
    "mercados en el sector {sector_gics} en América Latina.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Sustenta cada cifra (tamaño de mercado, crecimiento, participación) con datos de las "
    "fuentes proporcionadas; indica el año de referencia.\n"
    "- Si un dato no está disponible, escribe exactamente: \"Dato no disponible en fuentes consultadas.\"\n"  # noqa: E501
    "- No inventar cifras ni proyecciones bajo ninguna circunstancia.\n"
    "- No menciones escasez de fuentes; solo reporta el estado del dato.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta debe estar íntegramente en español latino neutro. "
    "Está prohibido usar chino, inglés u otro idioma.\n\n"
    "REGLAS DE ESTILO:\n"
    "- Tono ejecutivo y directo. Prohibido: \"podría\", \"quizás\", \"en resumen\", "
    "\"por lo tanto\", \"cabe destacar\", \"es importante mencionar\".\n"
    "- Los párrafos narrativos van en texto corrido (storytelling), sin viñetas.\n"
    "- Sin mini-checklists ni meta-comentarios al final. Sin citaciones inline en la narrativa.\n"
)

USER_PROMPT_03B = (
    "Genera EXCLUSIVAMENTE la sección \"2.3. Mercado\" del Capítulo 2 para el informe de "
    "inteligencia competitiva de la empresa descrita a continuación. No generes otras secciones.\n\n"  # noqa: E501
    "DESCRIPCIÓN DE LA EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "DATOS DE MERCADO (recuperados por RAG — usar como única fuente):\n{retrieval_mercado}\n\n"
    "Desarrolla en este orden, iniciando con el encabezado \"## 2.3. Mercado\":\n\n"
    "1. **Tamaño y crecimiento del mercado**: dimensiona el mercado del sector (valor total, "
    "TAM/SAM si consta) y su tasa de crecimiento, con año de referencia. Texto corrido.\n\n"
    "2. **Segmentos de mercado**: describe los principales segmentos y su peso relativo. "
    "Texto corrido.\n\n"
    "3. **Drivers y barreras**: factores que impulsan o frenan el mercado. Texto corrido.\n\n"
    "4. **Mercado por región**: si las fuentes contienen datos geográficos, describe en texto "
    "corrido los mercados con datos disponibles (p. ej. Norteamérica, Europa, América Latina, "
    "Asia-Pacífico). Menciona solo las regiones con evidencia concreta; omite las que no "
    "aparezcan en las fuentes (no escribas 'Dato no disponible')."
)


def format_chunks_as_context(chunks: list[ChunkResult]) -> str:
    """Delega en format_chunks_with_meta: incluye autor/año, nunca nombre de archivo (DT-033)."""
    return format_chunks_with_meta(chunks)


def build_chain_03b(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_03B),
        ("human", USER_PROMPT_03B),
    ])
    return prompt | llm | StrOutputParser()
