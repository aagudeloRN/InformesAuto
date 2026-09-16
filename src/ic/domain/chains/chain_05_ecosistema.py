"""Cadena LCEL para Capítulo 4 — Ecosistema Empresarial."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.domain.chains.chain_04_tendencias import (  # noqa: F401
    format_academic_sources,
    format_chunks_as_context,
)

SYSTEM_PROMPT_05 = (
    "Eres un analista estratégico senior especializado en movimientos corporativos y dinámica "
    "de ecosistemas empresariales (inversiones, integraciones, fusiones y adquisiciones, joint "
    "ventures y alianzas), con más de 10 años de experiencia en el sector {sector_gics} en "
    "América Latina.\n\n"
    "REGLAS DE CONTENIDO:\n"
    "- Sustenta cada evento con datos de las fuentes proporcionadas (empresas, montos, fechas).\n"
    '- Si un dato no está disponible, escribe exactamente: "Dato no disponible en fuentes consultadas."\n'  # noqa: E501
    "- No inventar eventos, montos, actores ni relaciones bajo ninguna circunstancia.\n"
    "- No menciones escasez de fuentes; solo reporta el estado del dato.\n"
    "- IDIOMA OBLIGATORIO: Toda la respuesta debe estar íntegramente en español latino neutro. "
    "Está prohibido usar chino, inglés u otro idioma.\n\n"
    "REGLAS DE ESTILO:\n"
    '- Tono ejecutivo y directo. Prohibido: "podría", "quizás", "en resumen", '
    '"por lo tanto", "cabe destacar", "es importante mencionar".\n'
    "- Sin adjetivos vacíos (innovador, disruptivo, revolucionario) salvo que haya evidencia cuantificable.\n"  # noqa: E501
    "- Cada evento es un bloque con: título en negrilla + narrativa breve de la ejecución + "
    "capacidad estratégica adquirida + vulnerabilidad mitigada.\n"
    "- Sin mini-checklists ni meta-comentarios al final.\n"
    "- Sin citaciones inline en las secciones narrativas.\n"
)

# Plantilla del formato de evento, reutilizada por los 5 subcapítulos (3 eventos c/u).
_FORMATO_EVENTO = (
    "Presenta EXACTAMENTE 3 eventos. Para cada evento:\n"
    "- **[Título del evento]** (en negrilla): actores involucrados y, si consta, monto y año.\n"
    "- Ejecución: cómo se materializó el movimiento (texto corrido, sin viñetas).\n"
    "- Capacidad estratégica adquirida: qué gana la empresa/actor con el movimiento.\n"
    "- Vulnerabilidad mitigada: qué riesgo o dependencia reduce.\n"
    "Si no hay 3 eventos con evidencia en las fuentes, presenta los que existan y, para el "
    'resto, escribe exactamente: "Dato no disponible en fuentes consultadas."\n\n'
)

# Subsecciones del Cap 4 como datos (DT-058): (id, título, encabezado descriptivo, consulta RAG).
# El capítulo es adaptativo: cada subsección se gatea por su propio retrieval en
# generate_ecosistema y solo se emiten las que tienen evidencia suficiente (ADR-002).
SUBSECCIONES: list[tuple[str, str, str, str]] = [
    (
        "4.1",
        "Inversiones",
        "Inversiones relevantes en empresas, startups o capacidad productiva del sector.",
        "inversiones capital riesgo capacidad productiva startups",
    ),
    (
        "4.2",
        "Integraciones Verticales",
        "Movimientos de integración hacia proveedores o canales de distribución.",
        "integración vertical proveedores canales distribución",
    ),
    (
        "4.3",
        "Fusiones y Adquisiciones (M&A)",
        "Operaciones de fusión o adquisición entre actores del sector.",
        "fusiones adquisiciones M&A compra de empresas",
    ),
    (
        "4.4",
        "Joint Ventures",
        "Empresas conjuntas y sociedades de riesgo compartido entre actores del sector.",
        "joint venture sociedad conjunta riesgo compartido alianza",
    ),
    (
        "4.5",
        "Alianzas de Compra y Abastecimiento",
        "Acuerdos de compra, abastecimiento o colaboración comercial entre actores del sector.",
        "alianzas compra abastecimiento colaboración comercial",
    ),
]


def build_secciones_solicitadas(activas: list[tuple[str, str, str, str]]) -> str:
    """Ensambla los bloques de instrucción SOLO de las subsecciones activas (DT-058).

    Las subsecciones sin evidencia suficiente se omiten por completo (no se pide al modelo que
    rellene con "Dato no disponible"), preservando la numeración original de las presentes.
    """
    bloques = [
        f"## {sid}. {titulo}\n\n{descripcion}\n" + _FORMATO_EVENTO
        for sid, titulo, descripcion, _query in activas
    ]
    return "".join(bloques).rstrip()


USER_PROMPT_05 = (
    'Genera el "Capítulo 4. Panorama del Ecosistema" para el informe de inteligencia '
    "competitiva de la empresa descrita a continuación.\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n{descripcion_empresa}\n\n"
    "CLASIFICACIÓN SECTORIAL:\n{sector_gics}\n\n"
    "CONTEXTO DEL ECOSISTEMA (recuperado por RAG — usar como fuente primaria):\n"
    "{retrieval_sector}\n\n"
    "FUENTES WEB ADICIONALES:\n{fuentes_web}\n\n"
    "Este capítulo analiza los MOVIMIENTOS del ecosistema del sector (no un mapa de actores). "
    "Prioriza eventos del sector {sector_gics} con foco en Colombia y América Latina cuando la "
    "evidencia lo permita.\n\n"
    "Inicia obligatoriamente con el siguiente párrafo introductorio (transcríbelo exactamente):\n"
    '"El panorama del ecosistema analiza los movimientos corporativos que reconfiguran la '
    "cadena de valor del sector: inversiones, integraciones verticales, fusiones y adquisiciones, "
    "joint ventures y alianzas de abastecimiento. Comprender estos movimientos permite anticipar "
    'cambios en la estructura competitiva y detectar oportunidades de posicionamiento."\n\n'
    "Desarrolla EXACTAMENTE las siguientes secciones en este orden (no agregues otras):\n\n"
    "{secciones_solicitadas}"
)


def build_chain_05(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_05),
            ("human", USER_PROMPT_05),
        ]
    )
    return prompt | llm | StrOutputParser()
