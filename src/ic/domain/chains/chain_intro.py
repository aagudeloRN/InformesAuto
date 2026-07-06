"""Cadena LCEL genérica para párrafos introductorios de capítulos (Fase 5F)."""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

SYSTEM_INTRO = "Eres un redactor de informes ejecutivos. Escribe SOLO en español latino neutro."

USER_INTRO = (
    "Escribe un párrafo introductorio de 2 a 3 oraciones para el capítulo "
    "'{titulo}' del informe de inteligencia competitiva de {empresa}. "
    "El capítulo desarrolla el siguiente contenido:\n\n{resumen_cap}\n\n"
    "La introducción debe contextualizar el propósito del capítulo para un lector "
    "ejecutivo. Sin títulos, sin viñetas, sin meta-comentarios."
)


def build_chain_intro(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_INTRO),
        ("human", USER_INTRO),
    ])
    return prompt | llm | StrOutputParser()
