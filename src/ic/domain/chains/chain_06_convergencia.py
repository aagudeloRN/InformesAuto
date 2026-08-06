"""Cadena LCEL para Capítulo 5 — Convergencia Empresarial en Áreas Estratégicas."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.domain.chains.chain_04_tendencias import (  # noqa: F401
    format_academic_sources,
    format_chunks_as_context,
)

SYSTEM_PROMPT_06 = (
    "Eres un consultor senior en estrategia empresarial y transformación digital con más de 15 años "  # noqa: E501
    "de experiencia asesorando empresas en América Latina. Tienes conocimiento profundo en análisis "  # noqa: E501
    "de tendencias tecnológicas, económicas y sociales, frameworks de competitividad y planificación "  # noqa: E501
    "estratégica.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Sustenta cada afirmación en los fragmentos de fuentes proporcionados.\n"
    "- Si un dato no está disponible, escribe exactamente: \"Dato no disponible en fuentes consultadas.\"\n"  # noqa: E501
    "- No inventar información. No inferir datos sin evidencia en el contexto.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta debe estar íntegramente en español latino neutro. "
    "Está prohibido usar chino, inglés u otro idioma.\n\n"
    "REGLAS DE ESTILO:\n"
    "- Tono ejecutivo y profesional, pero PROPOSITIVO (no imperativo): este es un documento de "
    "RECOMENDACIÓN y quien decide qué se hace es el lector (tomador de decisión), no el informe. "
    "Presenta cada acción como una oportunidad o alternativa a evaluar (\"una oportunidad es…\", "
    "\"la empresa podría…\", \"convendría explorar…\", \"se abre la posibilidad de…\", "
    "\"un camino posible es…\"). PROHIBIDO el modo imperativo y las construcciones de obligación "
    "dirigidas a la empresa: \"debe\", \"tiene que\", \"hay que\", \"debería\" en tono de mandato, "
    "\"implemente\", \"migre\", \"desarrolle\".\n"
    "- Evita muletillas: \"quizás\", \"en resumen\", \"por lo tanto\", \"cabe destacar\".\n"
    "- Sin adjetivos vacíos (innovador, disruptivo, revolucionario) salvo evidencia cuantificable.\n"  # noqa: E501
    "- Cada sección: texto corrido (storytelling), sin viñetas.\n"
    "- Varía el ritmo: alterna frases cortas (≤12 palabras) con frases más largas.\n"
    "- Sin mini-checklists ni meta-comentarios al final.\n"
    "- Sin citaciones inline en el cuerpo del texto.\n"
)

USER_PROMPT_06 = (
    "Genera el \"Capítulo 5. Convergencia Empresarial en las Áreas Estratégicas del Distrito\" "
    "para el informe de inteligencia competitiva de la empresa descrita a continuación.\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "HALLAZGOS DE CAPÍTULOS ANTERIORES (RAG sobre benchmarking, tendencias, ecosistema):\n"
    "{retrieval_caps_anteriores}\n\n"
    "CONTEXTO TERRITORIAL Y ÁREAS ESTRATÉGICAS DEL DISTRITO:\n"
    "{retrieval_convergencia_territorial}\n\n"
    "Inicia con el siguiente párrafo introductorio (transcríbelo exactamente):\n"
    "\"La convergencia empresarial analiza cómo las estrategias de la empresa se alinean con las "
    "prioridades del territorio y las tendencias del sector, identificando puntos de intersección que "  # noqa: E501
    "generan ventajas competitivas sostenibles y contribuyen al desarrollo regional.\"\n\n"
    "## 5.1 Área Estratégica: Sostenibilidad Ambiental\n\n"
    "Identifica oportunidades concretas para la empresa en sostenibilidad ambiental derivadas del "  # noqa: E501
    "contexto territorial y sectorial. Explica el por qué de cada oportunidad. Propone 3 acciones "  # noqa: E501
    "específicas con título en negrilla. Formato: storytelling sin viñetas. Mínimo 300 palabras.\n\n"  # noqa: E501
    "## 5.2 Área Estratégica: Transformación Digital y Gobierno Inteligente\n\n"
    "Ídem para transformación digital: cómo la empresa puede aprovechar las iniciativas de "
    "digitalización del sector y del territorio. Propone 3 acciones con título en negrilla. "
    "Mínimo 300 palabras.\n\n"
    "## 5.3 Área Estratégica: Desarrollo Social-Humano\n\n"
    "Ídem para desarrollo social: talento, inclusión, bienestar, responsabilidad empresarial "
    "en el contexto del sector y el territorio. Propone 3 acciones con título en negrilla. "
    "Mínimo 300 palabras.\n\n"
    "## 5.4 Área Estratégica: Desarrollo Económico\n\n"
    "Ídem para desarrollo económico: competitividad, exportaciones, empleo, encadenamientos "
    "productivos, inversión en el sector. Propone 3 acciones con título en negrilla. "
    "Mínimo 300 palabras.\n\n"
    "Reglas de presentación:\n"
    "- Cada acción: título en negrilla + párrafo de al menos 100 palabras.\n"
    "- No repetir ideas entre áreas.\n"
    "- Sin citaciones inline.\n"
)


def build_chain_06(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_06),
        ("human", USER_PROMPT_06),
    ])
    return prompt | llm | StrOutputParser()


_SYNTH_SYSTEM = (
    "Eres un consultor senior en estrategia empresarial. Integra los análisis de convergencia "
    "recibidos en un capítulo cohesivo. Conserva títulos en negrilla y tono ejecutivo. "
    "IDIOMA OBLIGATORIO: español latino neutro.\n\n"
    "ESTRUCTURA OBLIGATORIA: el capítulo tiene EXACTAMENTE 4 áreas estratégicas, ni una más:\n"
    "- ## 5.1 Área Estratégica: Sostenibilidad Ambiental\n"
    "- ## 5.2 Área Estratégica: Transformación Digital y Gobierno Inteligente\n"
    "- ## 5.3 Área Estratégica: Desarrollo Social-Humano\n"
    "- ## 5.4 Área Estratégica: Desarrollo Económico\n"
    "Está PROHIBIDO agregar, renumerar, dividir o inventar subsecciones más allá de 5.4 "
    "(nada de 5.5, 5.6, etc.). Integra todo el contenido recibido dentro de estas 4 áreas, "
    "elimina repeticiones y asegura transiciones fluidas."
)

_SYNTH_USER = (
    "Integra los siguientes análisis en el Capítulo 5. Convergencia Empresarial en las Áreas "
    "Estratégicas del Distrito, respetando EXACTAMENTE las 4 áreas (5.1 a 5.4) y sin crear "
    "subsecciones adicionales.\n\n"
    "Inicia con: \"La convergencia empresarial analiza cómo las estrategias de la empresa se "
    "alinean con las prioridades del territorio y las tendencias del sector, identificando puntos "  # noqa: E501
    "de intersección que generan ventajas competitivas sostenibles y contribuyen al desarrollo "
    "regional.\"\n\n"
    "{partes}"
)


def build_chain_06_synth(llm: object) -> Runnable:
    """Síntesis integradora: recibe {partes} (output de 3 ejes) y produce Cap 5 final."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYNTH_SYSTEM),
        ("human", _SYNTH_USER),
    ])
    return prompt | llm | StrOutputParser()
