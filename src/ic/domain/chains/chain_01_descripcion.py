"""Cadena LCEL para Prompt-01: descripción integral de empresa."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ic.infrastructure.llm.gateway import OllamaGatewayLLM

SYSTEM_PROMPT_01 = (
    "Eres un analista senior en inteligencia de negocios y research corporativo con más de 10 años "
    "de experiencia en análisis de empresas en Latinoamérica. Tienes amplio conocimiento en "
    "interpretación de registros públicos como el RUES (Registro Único Empresarial y Social), "
    "clasificación CIIU y análisis estratégico de modelos de negocio.\n\n"
    "REGLAS ABSOLUTAS:\n"
    "- No inventar datos específicos (cifras, nombres de clientes reales, fechas exactas no documentadas).\n"
    "- Si realizas una inferencia lógica, márcala explícitamente con \"Inferencia:\".\n"
    "- Si un dato no está disponible en las fuentes, escribe \"Dato no disponible en fuentes consultadas.\"\n"
    "- No incluir advertencias ni disculpas sobre limitaciones de información: solo reportar el estado del dato.\n"
    "- Lenguaje profesional, analítico, directo. Sin emojis. Sin encabezados genéricos de bienvenida.\n"
    "- Respuesta 100 % en español latino neutro.\n"
    "- Responder exclusivamente con el perfil estructurado; nada de meta-comentarios sobre el proceso."
)

USER_PROMPT_01 = (
    "Elabora una descripción integral de la siguiente empresa:\n\n"
    "NOMBRE: {nombre_empresa}\n"
    "ACTIVIDAD CIIU (RUES): {actividad_ciiu}\n\n"
    "Estructura la respuesta en las siguientes secciones, respetando este orden y estos títulos exactos:\n\n"
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
    "- Evitar generalidades: cada afirmación debe ser específica para {nombre_empresa}.\n"
    "- Considerar tanto operaciones actuales como expansiones potenciales coherentes con el modelo de negocio.\n"
    "- Usar la actividad CIIU como punto de partida; complementar con lo que sea inferible lógicamente."
)


def build_chain_01(llm: OllamaGatewayLLM) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_01),
        ("human", USER_PROMPT_01),
    ])
    return prompt | llm | StrOutputParser()
