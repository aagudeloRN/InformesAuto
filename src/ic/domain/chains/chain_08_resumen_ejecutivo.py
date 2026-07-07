"""Cadena LCEL para Resumen Ejecutivo (N3 — consume informe completo)."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

SYSTEM_PROMPT_08 = (
    "Eres un consultor estratégico de nivel C-Suite con más de 20 años de experiencia "
    "presentando análisis complejos a juntas directivas y altos ejecutivos en América Latina. "
    "Tu especialidad es sintetizar análisis extensos en narrativas ejecutivas concisas y "
    "orientadas a la decisión.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Basa el resumen exclusivamente en los capítulos proporcionados.\n"
    "- No añadir información que no esté en los capítulos.\n"
    "- Si un dato no está en los capítulos, omítelo sin mencionar su ausencia.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta en español latino neutro.\n\n"
    "REGLAS DE ESTILO:\n"
    "- Tono C-Level: directo, orientado a la acción, sin ambigüedades.\n"
    "- Prohibido: \"podría\", \"quizás\", \"en resumen\", \"por lo tanto\", \"cabe destacar\".\n"
    "- Sin adjetivos vacíos.\n"
    "- Texto corrido, sin viñetas ni listas.\n"
    "- Extensión: entre 400 y 600 palabras (una página ejecutiva).\n"
    "- Sin mini-checklists ni meta-comentarios al final.\n"
)

USER_PROMPT_08 = (
    "Genera el \"Resumen Ejecutivo\" para el informe de inteligencia competitiva de la empresa "
    "descrita a continuación, basándote exclusivamente en los capítulos del informe.\n\n"
    "EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "CAPÍTULOS DEL INFORME:\n{textos_capitulos}\n\n"
    "Estructura el resumen ejecutivo en este orden (texto corrido, sin encabezados de sección):\n\n"
    "1. **Gancho narrativo**: Abre con el hallazgo más relevante o la oportunidad más crítica "
    "del análisis. Máximo 2 frases.\n\n"
    "2. **Propósito**: Describe brevemente qué es la empresa y el alcance de este informe.\n\n"
    "3. **Problema u oportunidad central**: El desafío estratégico principal que enfrenta la "
    "empresa en su sector y territorio.\n\n"
    "4. **Solución estratégica**: La dirección estratégica recomendada a partir del análisis "
    "integrado de los capítulos.\n\n"
    "5. **Hallazgos clave**: Los 3 hallazgos más importantes del análisis (benchmarking, "
    "tendencias, ecosistema, convergencia territorial, accionables).\n\n"
    "6. **Conclusión y llamado a la acción**: Cierra con una frase que motive la acción inmediata.\n"  # noqa: E501
)


def build_chain_08(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_08),
        ("human", USER_PROMPT_08),
    ])
    return prompt | llm | StrOutputParser()
