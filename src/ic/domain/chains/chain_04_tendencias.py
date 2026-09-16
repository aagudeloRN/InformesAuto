"""Cadena LCEL para Capítulo 3 — Análisis Tendencial."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.infrastructure.citation.apa_formatter import format_chunks_with_meta
from ic.shared.types import ChunkResult

SYSTEM_PROMPT_04 = (
    "Eres un analista estratégico senior especializado en inteligencia de mercado y análisis "
    "sectorial, con más de 10 años asesorando grandes corporaciones del sector {sector_gics} en "
    "América Latina.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Sustenta cada afirmación clave con datos de las fuentes proporcionadas.\n"
    "- Indica el nivel de confianza (Alto/Medio/Bajo) de las afirmaciones clave y justifícalo.\n"
    '- Si un dato no está disponible, escribe exactamente: "Dato no disponible en fuentes consultadas."\n'  # noqa: E501
    "- No inventar información bajo ninguna circunstancia.\n"
    "- No menciones escasez de fuentes; solo reporta el estado del dato.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta debe estar íntegramente en español latino neutro. "
    "Está prohibido usar chino, inglés u otro idioma.\n\n"
    "REGLAS DE ESTILO:\n"
    '- Tono ejecutivo y directo. Prohibido: "podría", "quizás", "en resumen", '
    '"por lo tanto", "cabe destacar", "es importante mencionar".\n'
    "- Sin adjetivos vacíos (innovador, disruptivo, revolucionario) salvo que haya evidencia cuantificable.\n"  # noqa: E501
    "- Cada sección narrativa: texto corrido (storytelling), sin viñetas ni listas.\n"
    "- Varía el ritmo: alterna frases cortas (≤12 palabras) con frases más largas.\n"
    "- Sin mini-checklists ni meta-comentarios al final.\n"
    "- Sin citaciones inline en las secciones narrativas.\n"
    "- No emitas bloques de código ni cercas ``` ni JSON: responde en prosa Markdown plana. "
    "La respuesta debe empezar directamente con el párrafo introductorio, sin preámbulo.\n"
)

USER_PROMPT_04 = (
    'Genera el "Capítulo 3. Análisis Sectorial Tendencial" para el informe de inteligencia '
    "competitiva de la empresa descrita a continuación.\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "CONTEXTO SECTORIAL Y TENDENCIAS (recuperado por RAG — usar como fuente primaria):\n"
    "{retrieval_sector}\n\n"
    "FUENTES ACADÉMICAS (OpenAlex):\n{fuentes_academicas}\n\n"
    "Desarrolla exactamente las siguientes secciones en este orden:\n\n"
    "Inicia obligatoriamente con el siguiente párrafo introductorio (transcríbelo exactamente):\n"
    '"El análisis tendencial describe las tendencias del sector empresarial, identificando '
    "cambios tecnológicos, económicos y sociales que impactan la industria. Este análisis "
    "permite anticipar oportunidades y riesgos, orientando la toma de decisiones estratégicas "
    'con una visión de corto, mediano y largo plazo."\n\n'
    "## 3.1. Tendencias Tecnológicas, Económicas y Sociales del Sector\n\n"
    "Desarrolla 6 tendencias de alto impacto para el sector de la empresa: "
    "2 Tecnológicas, 2 Económicas, 2 Sociales. "
    "Preséntálas en este orden: Tecnológica 1, Tecnológica 2, Económica 1, Económica 2, "
    "Social 1, Social 2. "
    "Cada tendencia: título explicativo en negrilla + texto corrido estilo storytelling "
    "(sin viñetas, 2 párrafos respirables). "
    "Contexto aplicable a la disrupción del sector de la empresa.\n\n"
    "## 3.2. Tendencias MECE — Mutuamente Excluyentes y Colectivamente Exhaustivas\n\n"
    "Genera EXACTAMENTE 4 tendencias estratégicas sin solapamientos, asignadas así:\n"
    "1. Crecimiento / Captura de Mercado\n"
    "2. Optimización Operativa / Costos\n"
    "3. Innovación / Nuevos Productos o Servicios\n"
    "4. Mitigación de Riesgos / Alianzas Estratégicas\n\n"
    'Para cada una (texto corrido, sin viñetas, sin etiquetas "Título/Escenario/Implicancias"):\n'
    "- **[Título accionable orientado a negocio]** (en negrilla)\n"
    "- Narrativa ejecutiva con datos cuantitativos post-2026 y horizonte temporal "
    "(Corto: 0-2 años / Mediano: 2-5 años / Largo: +5 años).\n"
    "- Implicaciones estratégicas en tono imperativo: qué decisión tomar y resultado esperado.\n\n"
    "## 3.3. Casos de Éxito\n\n"
    "### Casos Globales\n"
    "Un caso real por cada tendencia MECE (4 casos). "
    "Cada caso: título sugestivo en negrilla + storytelling sin viñetas (empresa, qué hizo, resultado). "  # noqa: E501
    "Profundidad: al menos 150 palabras por caso.\n\n"
    "### Casos Locales\n"
    "Un caso de startup/scaleup en Medellín, Antioquia o Colombia por cada tendencia Tecnológica "
    "(2 casos). "
    "Mismo formato que los globales. Profundidad: al menos 150 palabras por caso.\n"
    "RESTRICCIÓN SECTORIAL OBLIGATORIA: los casos locales deben pertenecer al sector GICS "
    "{sector_gics} de la empresa analizada. Si no hay casos locales del mismo sector en las "
    'fuentes, escribe exactamente: "Dato no disponible en fuentes consultadas." — NO uses casos '
    "de otros sectores aunque sean de Medellín, Antioquia o Colombia."
)


def format_chunks_as_context(chunks: list[ChunkResult]) -> str:
    """Delega en format_chunks_with_meta: incluye autor/año, nunca nombre de archivo (DT-033)."""
    return format_chunks_with_meta(chunks)


def format_academic_sources(web_results: list) -> str:
    if not web_results:
        return "No se encontraron fuentes académicas disponibles en este momento."
    parts = []
    for i, r in enumerate(web_results, 1):
        meta = r.metadatos or {}
        año = meta.get("año", "s.f.")
        fuente = meta.get("fuente_nombre", "Fuente desconocida")
        autor = meta.get("autor", "")
        encabezado = f"[A{i}] {r.title} ({autor + ', ' if autor else ''}{año}, {fuente})"
        parts.append(f"{encabezado}\n{r.content[:500]}")
    return "\n\n---\n\n".join(parts)


def build_chain_04(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_04),
            ("human", USER_PROMPT_04),
        ]
    )
    return prompt | llm | StrOutputParser()
