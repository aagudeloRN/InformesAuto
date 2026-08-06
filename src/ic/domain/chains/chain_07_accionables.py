"""Cadena LCEL para Capítulo 6 — Accionables Estratégicos."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.domain.chains.chain_04_tendencias import (  # noqa: F401
    format_academic_sources,
    format_chunks_as_context,
)

SYSTEM_PROMPT_07 = (
    "Eres un consultor estratégico senior con amplia experiencia en planificación empresarial "
    "y transformación organizacional en América Latina. Tu especialidad es traducir análisis "
    "sectoriales complejos en líneas de acción concretas que el tomador de decisión pueda "
    "evaluar y priorizar.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Cada accionable debe estar sustentado en evidencia de las fuentes proporcionadas.\n"
    "- Si no hay evidencia para un accionable, escribe: \"Dato no disponible en fuentes consultadas.\"\n"  # noqa: E501
    "- No inventar datos, cifras ni tendencias.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta en español latino neutro.\n\n"
    "REGLAS DE ESTILO:\n"
    "- Tono ejecutivo y profesional, pero PROPOSITIVO (no imperativo): es un documento de "
    "RECOMENDACIÓN; quien decide qué se implementa es el lector (tomador de decisión), no el "
    "informe. Presenta cada accionable como una oportunidad/alternativa a evaluar (\"esta línea "
    "de acción permitiría…\", \"representa una oportunidad de…\", \"la empresa podría…\", "
    "\"convendría evaluar…\"). PROHIBIDO el imperativo y la obligación dirigida a la empresa: "
    "\"debe\", \"tiene que\", \"hay que\", \"implemente\", \"migre\", \"desarrolle\".\n"
    "- Evita muletillas: \"quizás\", \"en resumen\", \"por lo tanto\", \"cabe destacar\".\n"
    "- Sin adjetivos vacíos salvo evidencia cuantificable.\n"
    "- Storytelling: texto corrido, sin viñetas.\n"
    "- Sin mini-checklists ni meta-comentarios al final.\n"
    "- Sin citaciones inline.\n"
)

USER_PROMPT_07 = (
    "Genera el \"Capítulo 6. Accionables Estratégicos\" para el informe de inteligencia "
    "competitiva de la empresa descrita a continuación.\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "HALLAZGOS DE LOS CAPÍTULOS ANTERIORES (benchmarking, tendencias, ecosistema, "
    "convergencia territorial):\n{hallazgos_caps_previos}\n\n"
    "ANÁLISIS CRUZADO (evidencia de fuentes):\n{retrieval_cruzado}\n\n"
    "Genera exactamente 6 accionables estratégicos que crucen los hallazgos de los capítulos "
    "anteriores. Cada accionable:\n"
    "- Comienza con un **título en negrilla** que etiquete la línea de acción (infinitivo neutro, "
    "p. ej. \"Diferenciación de la oferta\"; es una etiqueta, no una orden al lector).\n"
    "- Sigue con una descripción narrativa de al menos 150 palabras (storytelling, sin viñetas), "
    "en tono PROPOSITIVO: enmarca la acción como oportunidad a evaluar (\"la empresa podría…\", "
    "\"esta línea permitiría…\"), NUNCA como mandato (\"debe…\").\n"
    "- Referenciar explícitamente al menos un hallazgo concreto de los capítulos anteriores "
    "(un competidor del benchmarking, una tendencia, un actor del ecosistema o una "
    "oportunidad de convergencia), sin citación inline.\n"
    "- Cerrar con una justificación de por qué este accionable es prioritario, basada en los "
    "hallazgos del análisis.\n\n"
    "Los 6 accionables deben cubrir diferentes dimensiones: competitividad, transformación digital, "  # noqa: E501
    "sostenibilidad, talento, ecosistema y desarrollo de mercado. No repetir dimensiones.\n"
)


def build_chain_07(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_07),
        ("human", USER_PROMPT_07),
    ])
    return prompt | llm | StrOutputParser()
