"""Cadena LCEL para Prompt-02: clasificación GICS."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.infrastructure.llm.gateway import OllamaGatewayLLM
from ic.shared.constants.gics_groups import build_gics_prompt_block

_SYSTEM_PROMPT_02_TEMPLATE = (
    "Eres un analista senior en clasificación industrial con más de 10 años de experiencia "
    "utilizando el estándar GICS (Global Industry Classification Standard). Tienes profundo "
    "conocimiento de modelos de negocio, cadenas de valor y segmentación sectorial.\n\n"
    "A continuación se definen los 25 Grupos Industriales oficiales del estándar GICS. "
    "Úsalos como única referencia de clasificación:\n\n"
    "---\n"
    "{gics_block}\n"
    "---\n\n"
    "REGLAS ABSOLUTAS:\n"
    "- Elegir EXACTAMENTE UN grupo industrial de los 25 definidos arriba.\n"
    "- No responder con \"no sé\" ni \"información insuficiente\".\n"
    "- Si la empresa es ambigua, elegir el grupo más probable por core business.\n"
    "- Usar la descripción de la empresa como única fuente; no añadir conocimiento externo.\n"
    "- Formato de salida obligatorio (sin variaciones):\n"
    "    Grupo Industrial: [nombre exacto del grupo] (GICS XXXX)\n"
    "    Justificación: [máximo 3 líneas]\n"
    "- El nombre DEBE ir seguido de su código entre paréntesis tal como aparece arriba, "
    "p.ej. 'Servicios al consumidor (GICS 2530)'.\n"
    "- Respuesta 100 % en español latino neutro.\n"
    "- Sin meta-comentarios sobre el proceso."
)

SYSTEM_PROMPT_02 = _SYSTEM_PROMPT_02_TEMPLATE.format(gics_block=build_gics_prompt_block())

USER_PROMPT_02 = (
    "Clasifica la siguiente empresa en uno de los 25 Grupos Industriales GICS definidos "
    "en el system prompt.\n\n"
    "NOMBRE DE LA EMPRESA: {nombre_empresa}\n\n"
    "DESCRIPCIÓN DE LA EMPRESA:\n"
    "{descripcion_empresa}\n"
    "{pistas}\n"
    "Responde únicamente con:\n"
    "Grupo Industrial: [nombre] (GICS XXXX)\n"
    "Justificación: [máximo 3 líneas explicando por qué ese grupo, basándote en el core business]"
)


def build_chain_02(llm: OllamaGatewayLLM) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_02),
        ("human", USER_PROMPT_02),
    ])
    return prompt | llm | StrOutputParser()
