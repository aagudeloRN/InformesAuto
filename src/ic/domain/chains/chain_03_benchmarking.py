"""Cadena LCEL para Prompt-03: Capítulo 2 — Análisis Competitivo."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.infrastructure.citation.apa_formatter import format_chunks_with_meta
from ic.infrastructure.llm.gateway import OllamaGatewayLLM
from ic.shared.types import ChunkResult

SYSTEM_PROMPT_03 = (
    "Eres un consultor senior en estrategia empresarial y análisis competitivo global con más "
    "de 10 años de experiencia en benchmarking en la industria de bienes de consumo. Tienes "
    "especialización en inteligencia de mercado y tendencias disruptivas (FoodTech).\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Sustenta cada afirmación con datos concretos o porcentajes de las fuentes proporcionadas.\n"
    "- Cita cada párrafo con la fuente en formato: (Autor, año). Ejemplo: (Fortune Business Insights, 2026).\n"  # noqa: E501
    "- Si un dato no está disponible en las fuentes, escribe: \"Dato no disponible en fuentes consultadas.\"\n"  # noqa: E501
    "- No inventar información bajo ninguna circunstancia.\n"
    "- No mencionar escasez o poca disponibilidad de fuentes; solo reportar el estado del dato.\n"
    "- No incluir a la empresa analizada ni a su grupo corporativo como competidor.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta debe estar íntegramente en español latino neutro. "
    "Está prohibido usar chino, inglés u otro idioma. "
    "Si detectas que escribes en otro idioma, detente y reescribe en español.\n\n"
    "REGLAS DE FORMATO Y ESTILO (aplicar en todo el documento):\n"
    "- Sección 2.1 — Jugadores Clave: presentar cada actor como una ficha/tabla individual, "
    "agrupada por subcategoría (Líderes Globales / Referentes Regionales LatAm/Colombia / "
    "Startups FoodTech). Cada ficha cubre los 8 puntos: nombre+país, resumen estratégico, "
    "portafolio clave, propuesta de valor, canales y precios, presencia geográfica, "
    "mayor fortaleza, factor innovador diferencial.\n"
    "- Sección 2.2 — Síntesis de Presión Competitiva: texto corrido tipo storytelling. "
    "Sin viñetas. Sin listas. Sin títulos intermedios dentro de la síntesis.\n"
    "- Sección 2.4 — Focos (Innovación / Inversión / Talento): cada foco es un bloque "
    "de texto corrido independiente, tipo storytelling. Sin viñetas dentro de cada foco.\n"
    "- Sección 2.5 — Análisis de Brechas: cada pregunta se responde en texto corrido, "
    "tipo storytelling. Sin viñetas.\n"
    "- Estilo general para 2.2, 2.4 y 2.5:\n"
    "    * Variar el ritmo: alternar frases cortas (≤12 palabras) con frases más largas.\n"
    "    * Máximo 1 ejemplo concreto por párrafo.\n"
    "    * Prohibido: \"en resumen\", \"por lo tanto\", \"cabe destacar\", \"es importante mencionar\".\n"  # noqa: E501
    "    * Sin adjetivos vacíos (innovador, disruptivo, revolucionario) salvo que haya evidencia "
    "cuantificable en las fuentes.\n"
    "    * Cada párrafo: entre 80 y 150 palabras.\n"
    "    * Mantener longitud total de cada sección dentro de ±10 % respecto a su extensión natural.\n"  # noqa: E501
    "- Sin mini-checklists ni meta-comentarios al final de ninguna sección.\n"
    "- Sin citaciones inline en la sección 2.2 (la síntesis es editorial; las citas van en 2.1).\n"
    "- FORMATO DE FICHAS (sección 2.1): cada ficha debe ser una tabla markdown con pipes. "
    "Ejemplo de formato:\n"
    "| Campo | Valor |\n"
    "|-------|-------|\n"
    "| Nombre + País | Nestlé — Suiza |\n"
    "Usar exactamente este formato de tabla markdown para CADA competidor en 2.1."
)

USER_PROMPT_03 = (
    "Genera el \"Capítulo 2. Análisis Competitivo\" para el informe de inteligencia competitiva "
    "de la empresa descrita a continuación.\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n"
    "{descripcion_empresa}\n\n"
    "FICHAS DE COMPETIDORES (recuperadas por RAG — usar como única fuente para este capítulo):\n"
    "{retrieval_competidores}\n\n"
    "Desarrolla exactamente las siguientes secciones en este orden:\n\n"
    "## 2.1. Jugadores Clave - Líderes del Mercado\n\n"
    "Identifica y analiza 14 actores: 8 líderes globales, 3 referentes regionales (LatAm/Colombia) "  # noqa: E501
    "y 3 startups/FoodTech disruptivas.\n"
    "Para cada actor, una ficha/tabla con los 8 puntos indicados en el system prompt.\n"
    "Agrupa por subcategoría: ### Referentes Globales / ### Referentes Regionales LatAm/Colombia / "  # noqa: E501
    "### Startups / FoodTech Disruptivas.\n\n"
    "## 2.2. División de Competidores\n\n"
    "Genera una matriz 2×2 que clasifique los 14 actores cruzando:\n"
    "- Eje X: Enfoque de Mercado (Masivo/Volumen ↔ Nicho/Premium)\n"
    "- Eje Y: Nivel de Disrupción (Jugadores Tradicionales ↔ Entrantes Innovadores)\n\n"
    "Luego escribe la \"Síntesis de Presión Competitiva\" como texto corrido (storytelling), "
    "sin viñetas, aplicando las reglas de estilo del system prompt.\n\n"
    "## 2.4. Módulos de Innovación, Inversión y RRHH\n\n"
    "Análisis sectorial global (no por empresa). Tres bloques independientes:\n"
    "### Foco de Innovación\n"
    "### Foco de Inversión\n"
    "### Foco de Talento\n"
    "Cada bloque: texto corrido (storytelling), sin viñetas.\n\n"
    "## 2.5. Análisis de Brechas\n\n"
    "Responde estas dos preguntas en texto corrido (storytelling), sin viñetas:\n"
    "- ¿Qué oportunidades no están cubriendo los líderes globales?\n"
    "- ¿Qué estrategias están usando las startups para ganar cuota de mercado?\n\n"
    "## RADAR DE POSICIONAMIENTO (emitir AL FINAL, después de todo el texto anterior)\n\n"
    "Basándote en el análisis de la sección 2.1, emite EXACTAMENTE el siguiente bloque JSON "
    "(reemplaza los nombres y valores con los competidores reales analizados; scores de 1 a 5):\n\n"
    "```radar_json\n"
    '{{\n'
    '  "dimensions": ["Innovación", "Inversión", "Presencia global", "Sostenibilidad", "Digital"],'
    '\n'
    '  "competidores": {{\n'
    '    "Nombre Competidor 1": [4.5, 4.0, 5.0, 3.5, 4.0],\n'
    '    "Nombre Competidor 2": [3.0, 3.5, 4.5, 3.0, 3.5]\n'
    '  }}\n'
    '}}\n'
    "```\n\n"
    "Incluye de 4 a 8 competidores clave de la sección 2.1. "
    "No emitas ningún texto después del bloque ```radar_json```."
)


def format_chunks_as_context(chunks: list[ChunkResult]) -> str:
    """Delega en format_chunks_with_meta para incluir autor/año y permitir citas inline."""
    return format_chunks_with_meta(chunks)


def build_chain_03(llm: OllamaGatewayLLM) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_03),
        ("human", USER_PROMPT_03),
    ])
    return prompt | llm | StrOutputParser()
