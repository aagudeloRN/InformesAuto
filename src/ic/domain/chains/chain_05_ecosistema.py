"""Cadena LCEL para Capítulo 4 — Ecosistema Empresarial."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.domain.chains.chain_04_tendencias import (  # noqa: F401
    format_academic_sources,
    format_chunks_as_context,
)

SYSTEM_PROMPT_05 = (
    "Eres un analista estratégico senior especializado en mapeo de ecosistemas empresariales "
    "y análisis de cadenas de valor, con experiencia en los sectores industriales de "
    "América Latina.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Sustenta cada afirmación clave con datos de las fuentes proporcionadas.\n"
    "- Si un dato no está disponible, escribe exactamente: \"Dato no disponible en fuentes consultadas.\"\n"  # noqa: E501
    "- No inventar actores, alianzas ni relaciones bajo ninguna circunstancia.\n"
    "- No menciones escasez de fuentes; solo reporta el estado del dato.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta debe estar íntegramente en español latino neutro. "
    "Está prohibido usar chino, inglés u otro idioma.\n\n"
    "REGLAS DE ESTILO:\n"
    "- Tono ejecutivo y directo. Prohibido: \"podría\", \"quizás\", \"en resumen\", "
    "\"por lo tanto\", \"cabe destacar\", \"es importante mencionar\".\n"
    "- Sin adjetivos vacíos (innovador, disruptivo, revolucionario) salvo que haya evidencia cuantificable.\n"  # noqa: E501
    "- Cada actor o categoría: ficha estructurada con nombre, rol y relevancia estratégica.\n"
    "- Sin mini-checklists ni meta-comentarios al final.\n"
    "- Sin citaciones inline en las secciones narrativas.\n"
)

USER_PROMPT_05 = (
    "Genera el \"Capítulo 4. Ecosistema Empresarial\" para el informe de inteligencia "
    "competitiva de la empresa descrita a continuación.\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "CONTEXTO DEL ECOSISTEMA (recuperado por RAG — usar como fuente primaria):\n"
    "{retrieval_sector}\n\n"
    "FUENTES WEB ADICIONALES:\n{fuentes_web}\n\n"
    "Desarrolla exactamente las siguientes secciones en este orden:\n\n"
    "Inicia obligatoriamente con el siguiente párrafo introductorio (transcríbelo exactamente):\n"
    "\"El análisis del ecosistema empresarial identifica los actores clave que conforman la "
    "cadena de valor de la industria: proveedores, clientes, aliados, reguladores y agentes "
    "disruptores. Conocer este entorno permite a la empresa posicionarse estratégicamente, "
    "anticipar dependencias críticas y detectar oportunidades de colaboración o diferenciación.\"\n\n"  # noqa: E501
    "## 4.1. Ecosistema Local (Medellín / Colombia)\n\n"
    "Mapea los actores del ecosistema nacional relevantes para la empresa. "
    "Para cada categoría, presenta fichas con: **Nombre del actor** — Rol en el ecosistema — "
    "Relevancia estratégica para la empresa. Cubre estas categorías:\n"
    "- Proveedores clave (materia prima, tecnología, servicios)\n"
    "- Clientes tipo (segmentos principales)\n"
    "- Gremios y asociaciones sectoriales\n"
    "- Reguladores y entidades de control\n\n"
    "## 4.2. Ecosistema Global\n\n"
    "Mapea los actores internacionales que influyen en la industria de la empresa. "
    "Mismo formato de fichas. Cubre estas categorías:\n"
    "- Partners y aliados estratégicos internacionales\n"
    "- Organismos sectoriales internacionales\n"
    "- Grandes clientes o mercados de exportación relevantes\n\n"
    "## 4.3. Actores Disruptores\n\n"
    "Identifica startups, scale-ups y tecnologías emergentes que están reconfigurando "
    "el sector a nivel global y latinoamericano. "
    "Para cada actor: **Nombre** — Modelo de negocio disruptivo — Amenaza u oportunidad "
    "para la empresa — Horizonte de impacto (Corto: 0-2 años / Mediano: 2-5 años / Largo: +5 años). "  # noqa: E501
    "Incluye al menos 4 actores disruptores con evidencia de mercado."
)


def build_chain_05(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_05),
        ("human", USER_PROMPT_05),
    ])
    return prompt | llm | StrOutputParser()
