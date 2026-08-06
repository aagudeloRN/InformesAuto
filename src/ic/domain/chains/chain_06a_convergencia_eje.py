"""Chain LCEL genérico para UN eje de convergencia (RN-009).

Recibe el nombre del eje, sus instrucciones específicas y el contexto RAG,
y genera la sección narrativa para ese eje.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

SYSTEM_PROMPT_06A = (
    "Eres un consultor senior en estrategia empresarial con más de 15 años de experiencia "
    "asesorando empresas en América Latina. Analizas UN eje de convergencia específico.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Sustenta cada afirmación en los fragmentos de fuentes proporcionados.\n"
    "- Si un dato no está disponible, escribe exactamente: \"Dato no disponible en fuentes consultadas.\"\n"  # noqa: E501
    "- No inventar información. No inferir datos sin evidencia en el contexto.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta debe estar íntegramente en español latino neutro.\n\n"
    "REGLAS DE ESTILO:\n"
    "- Tono ejecutivo y profesional, pero PROPOSITIVO (no imperativo): es un documento de "
    "RECOMENDACIÓN; quien decide qué se hace es el lector (tomador de decisión), no el informe. "
    "Presenta cada acción como oportunidad/alternativa a evaluar (\"una oportunidad es…\", \"la "
    "empresa podría…\", \"convendría explorar…\", \"se abre la posibilidad de…\"). PROHIBIDO el "
    "imperativo y la obligación dirigida a la empresa: \"debe\", \"tiene que\", \"hay que\", "
    "\"implemente\", \"migre\", \"desarrolle\".\n"
    "- Evita muletillas: \"quizás\", \"en resumen\", \"por lo tanto\".\n"
    "- Sin adjetivos vacíos salvo evidencia cuantificable.\n"
    "- Texto corrido (storytelling), sin viñetas. Mínimo 200 palabras por sub-sección.\n"
    "- Sin citaciones inline en el cuerpo del texto.\n"
)

USER_PROMPT_06A = (
    "Genera la sección de convergencia para el eje: **{eje_nombre}**\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "CONTEXTO TERRITORIAL Y SECTORIAL (RAG):\n{retrieval_context}\n\n"
    "INSTRUCCIONES DEL EJE:\n{eje_instrucciones}\n\n"
    "Escribe en texto corrido sin viñetas. Propón 3 acciones concretas con título en negrilla "
    "y párrafo de al menos 100 palabras cada una. No repitas ideas de otros ejes.\n"
)


def build_chain_06a(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_06A),
        ("human", USER_PROMPT_06A),
    ])
    return prompt | llm | StrOutputParser()


# Definición de los 3 ejes (RN-009)
EJE_TECNOLOGICO = {
    "eje_nombre": "Convergencia Tecnológica",
    "eje_instrucciones": (
        "## 5.1 Sostenibilidad Ambiental\n"
        "Identifica oportunidades concretas para la empresa en sostenibilidad ambiental derivadas "
        "del contexto territorial y sectorial. Propón 3 acciones con título en negrilla.\n\n"
        "## 5.2 Transformación Digital y Gobierno Inteligente\n"
        "Cómo la empresa puede aprovechar las iniciativas de digitalización del sector y del territorio. "  # noqa: E501
        "Propón 3 acciones con título en negrilla."
    ),
}

EJE_MERCADO = {
    "eje_nombre": "Convergencia de Mercado",
    "eje_instrucciones": (
        "## 5.4 Desarrollo Económico\n"
        "Analiza competitividad, exportaciones, empleo, encadenamientos productivos e inversión "
        "en el sector. Propón 3 acciones con título en negrilla."
    ),
}

EJE_SOCIAL = {
    "eje_nombre": "Convergencia Competitiva y Social",
    "eje_instrucciones": (
        "## 5.3 Desarrollo Social-Humano\n"
        "Analiza talento, inclusión, bienestar y responsabilidad empresarial en el contexto "
        "del sector y el territorio. Propón 3 acciones con título en negrilla."
    ),
}
