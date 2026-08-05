"""Cadena LCEL del juez de calidad (DT-059/T1) — LLM-judge con la rúbrica v1.0.

Puntúa UN capítulo en las 5 dimensiones de la rúbrica (E/P/V/F/T, 0–3) y lista las
carencias accionables (`faltantes`) que alimentan al revisor. El modelo se inyecta como
`Runnable` (ADR-002: sin nombres de modelo en código; el evaluador lo construye el
orquestador con `build_resilient_api_llm`/`build_llm`, Nemotron/OpenRouter con Ollama de
fallback). La salida cruda la parsea `parse_rubric_score` (puro, testeable).

Los criterios por-capítulo (`CRITERIOS_CAPITULO`) se derivan de `docs/eval/RUBRICA_CALIDAD.md
§2` — no se re-fabrican: el juez reusa la rúbrica existente (F20).
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

# Criterios de aceptación por capítulo (resumen fiel de RUBRICA_CALIDAD.md §2, patrón Noel).
# Clave = nombre del capítulo tal como se cablea en el orquestador (self_review_hooks).
CRITERIOS_CAPITULO: dict[str, str] = {
    "Cap 2 — Análisis Competitivo": (
        "E: subcapítulos 2.1 Jugadores Clave (Globales/Regionales LatAm/Startups), 2.2 División "
        "de competidores (matriz 2x2 + síntesis), 2.3 Mercado, 2.4 Innovación/Inversión/RRHH, "
        "2.5 Brechas. P: ~14 actores descritos con datos reales (portafolio, presencia, estrategia), "  # noqa: E501
        "cifras de cuota/ingresos cuando las fuentes las proveen. "
        "V: cada actor citado (Autor, año), nunca nombre de archivo, empresa analizada excluida. "
        "F: 2.1 en PROSA (NO tablas) — un mini-párrafo por actor con formato **Nombre** *(País)* — "
        "descripción; sin radar, sin tabla de mercado por región (sección 2.3 en texto corrido). "
        "T: 2.1 mini-párrafos; 2.2/2.4/2.5 storytelling ejecutivo sin viñetas."
    ),
    "Cap 3 — Análisis Sectorial Tendencial": (
        "E: intro fija + 3.1 seis tendencias (2 T/2 E/2 S) + 3.2 cuatro MECE + 3.3 casos globales "
        "y locales. P: títulos sugestivos, datos cuantitativos post-2026, horizonte temporal, "
        "casos >=150 palabras (empresa/qué hizo/resultado). V: nivel de confianza justificado, "
        "casos locales del mismo sector GICS, sin inventar. F: capítulo narrativo (sin tablas "
        "obligatorias). T: ejecutivo, sin 'podría/quizás', storytelling."
    ),
    "Cap 4 — Panorama Ecosistema": (
        "E: 4.1 Inversiones, 4.2 Integraciones verticales, 4.3 M&A, 4.4 Joint ventures, 4.5 "
        "Alianzas de compra (subsecciones con evidencia; se omiten las que no la tengan). P: por "
        "evento título + ejecución + capacidad estratégica adquirida + vulnerabilidad mitigada; "
        "foco ecosistema local (Medellín/Antioquia/Colombia). V: cada evento citado, empresas "
        "reales distintas de la analizada, sin relleno. F: narrativo con títulos en negrilla. "
        "T: analítico, objetivo, storytelling sin viñetas."
    ),
    "Cap 5 — Convergencia Empresarial": (
        "E: exactamente 4 áreas (5.1 Sostenibilidad Ambiental, 5.2 Transformación Digital y "
        "Gobierno Inteligente, 5.3 Desarrollo Social-Humano, 5.4 Desarrollo Económico). P: por "
        "área oportunidad concreta + justificación + 3 acciones con título en negrilla (>=100 "
        "palabras c/u), >=300 palabras por área, sin repetir ideas. V: derivado de caps previos + "
        "contexto territorial. F: narrativo. T: consultor senior, storytelling sin viñetas."
    ),
    "Cap 6 — Accionables Estratégicos": (
        "E: exactamente 6 accionables, cada uno con título en negrilla + descripción + "
        "justificación. P: cruzan hallazgos de Caps 2/3/4/5, ejecutables, >=150 palabras, 6 "
        "dimensiones distintas (competitividad, transformación digital, sostenibilidad, talento, "
        "ecosistema, mercado). V: cada accionable referencia un hallazgo concreto de un capítulo "
        "previo. F: narrativo. T: consultivo, sin 'Accionable N:', storytelling."
    ),
}

SYSTEM_PROMPT_JUDGE = (
    "Eres un evaluador experto de informes de inteligencia competitiva. Puntúas UN capítulo "
    "según una rúbrica fija, con rigor y SOLO con base en el texto proporcionado. No inventas "
    "méritos que el texto no demuestre.\n\n"
    "Califica el capítulo '{capitulo_nombre}' en 5 dimensiones, cada una de 0 a 3:\n"
    "- E (Estructura): ¿están los subcapítulos esperados, en orden y numeración correctos?\n"
    "- P (Profundidad): datos concretos, cifras y nombres propios vs generalidades de relleno.\n"
    "- V (Evidencia/Citación): afirmaciones sustentadas y trazables (APA), ausencias declaradas.\n"
    "- F (Formato/Visuales): formato correcto según los criterios del capítulo "
    "(prosa, tablas o figuras según se especifique).\n"
    "- T (Tono): ejecutivo, storytelling sin viñetas, sin muletillas de IA, español neutro.\n\n"
    "Escala: 0=ausente/no cumple; 1=presente pero deficiente; 2=cumple con carencias menores; "
    "3=equivalente al patrón de referencia.\n\n"
    "CRITERIOS ESPECÍFICOS DE ESTE CAPÍTULO:\n{criterios_capitulo}\n\n"
    "Responde EXCLUSIVAMENTE con un objeto JSON, sin texto antes ni después, con esta forma "
    'exacta: {{"E":n,"P":n,"V":n,"F":n,"T":n,"faltantes":["carencia accionable 1", "..."]}}. '
    "Cada n es un entero 0–3. 'faltantes' lista, en imperativo y accionable, lo que falta para "
    "que las dimensiones con menos de 2 lleguen al patrón (vacío si todo está en 2 o 3)."
)

USER_PROMPT_JUDGE = (
    "TEXTO DEL CAPÍTULO A EVALUAR (única fuente permitida):\n\n{texto_capitulo}\n\n"
    "Puntúa el capítulo '{capitulo_nombre}' y responde solo con el objeto JSON."
)


def build_chain_judge(llm: object) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_JUDGE),
        ("human", USER_PROMPT_JUDGE),
    ])
    return prompt | llm | StrOutputParser()
