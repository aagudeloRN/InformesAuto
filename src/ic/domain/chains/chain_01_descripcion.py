"""Cadena LCEL para Prompt-01: descripción integral de empresa.

Cadena de fallback automática:
  1. OpenRouter free primario  (ej: Nemotron Super 120B)
  2. OpenRouter free alternativo (ej: Llama 3.3 70B)
  3. Ollama local              (ej: qwen3:8b — siempre disponible)
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

SYSTEM_PROMPT_01 = (
    "Eres un analista senior en inteligencia de negocios y research corporativo con más de 10 años "
    "de experiencia en análisis de empresas en Latinoamérica.\n\n"
    "REGLAS ABSOLUTAS — NINGUNA TIENE EXCEPCIÓN:\n"
    "1. IDIOMA: Tu respuesta DEBE estar íntegramente en español latino neutro. "
    "Está terminantemente prohibido usar chino, inglés u otro idioma. "
    "Si detectas que empiezas a escribir en otro idioma, detente y reescribe en español.\n"
    "2. FUENTES: Usa EXCLUSIVAMENTE la información del contexto web proporcionado en el prompt. "
    "No inventes datos que no estén en ese contexto.\n"
    "3. AUSENCIA: Si un dato específico no aparece en el contexto, escribe exactamente: "
    '"Dato no disponible en fuentes consultadas."\n'
    '4. INFERENCIAS: Si realizas una inferencia lógica a partir del contexto, márcala con "Inferencia:".\n'  # noqa: E501
    "5. FORMATO: Sin emojis. Sin encabezados genéricos. Sin meta-comentarios. "
    "Solo el perfil estructurado solicitado."
)

USER_PROMPT_01 = (
    "Elabora una descripción integral de la siguiente empresa basándote ÚNICAMENTE en el contexto web "  # noqa: E501
    "provisto más abajo. No uses conocimiento propio: todo lo que escribas debe poder rastrearse al contexto.\n\n"  # noqa: E501
    "NOMBRE: {nombre_empresa}\n"
    "ACTIVIDAD CIIU (RUES): {actividad_ciiu}\n\n"
    "CONTEXTO WEB (única fuente autorizada para este capítulo):\n"
    "{web_context}\n\n"
    "Estructura la respuesta en las siguientes secciones, respetando este orden y estos títulos exactos:\n\n"  # noqa: E501
    "## Descripción general\n"
    "## Productos y servicios\n"
    "## Segmentos de clientes\n"
    "## Modelo de negocio\n"
    "## Cobertura geográfica\n"
    "## Canales de venta y distribución\n"
    "## Fuentes de ingresos\n"
    "## Posicionamiento competitivo\n"
    "## Oportunidades y riesgos\n\n"
    "Requisitos por sección:\n"
    "- Cada sección: mínimo 2 párrafos, máximo 4.\n"
    "- Párrafos de 80–150 palabras cada uno.\n"
    "- Toda afirmación específica (cifras, fechas, nombres) debe venir del contexto web. "
    "Si no está en el contexto, declara ausencia en lugar de inventar.\n"
    "- Respuesta 100 % en español latino neutro. Ningún carácter en otro idioma."
)


def build_chain_01(llms: BaseChatModel | list[BaseChatModel]) -> Runnable:
    """Construye la cadena para Cap 1 con fallback automático entre LLMs.

    Acepta un único LLM o una lista ordenada por prioridad.
    Si el primero falla (rate limit, error 5xx, timeout), LangChain
    intenta automáticamente el siguiente via with_fallbacks().
    """
    if not isinstance(llms, list):
        llms = [llms]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_01),
            ("human", USER_PROMPT_01),
        ]
    )
    parser = StrOutputParser()

    chains = [prompt | llm | parser for llm in llms]
    if len(chains) == 1:
        return chains[0]
    return chains[0].with_fallbacks(chains[1:])
