"""Coherencia interna del informe (Fase 22, T22.1, Q1).

Funciones puras (Dependency Agnosticism): construyen el contexto de "hallazgos de capítulos
anteriores" que alimenta al Cap 6 (Accionables) para que sus recomendaciones referencien
explícitamente el análisis previo (benchmarking, tendencias, ecosistema, convergencia), en
lugar de derivarse solo del retrieval.
"""

from __future__ import annotations


def build_caps_summary(
    caps: list[tuple[str, str]], max_chars_per_cap: int = 600
) -> str:
    """Une resúmenes etiquetados de capítulos previos para inyectarlos en un prompt.

    `caps` es una lista de pares (etiqueta, texto). Cada texto se recorta a
    `max_chars_per_cap` caracteres (por límite de contexto) y se antepone su etiqueta. Los
    capítulos con texto vacío o en blanco se ignoran. Devuelve el bloque unido, o "" si no
    hay contenido.
    """
    partes: list[str] = []
    for etiqueta, texto in caps:
        if not texto or not texto.strip():
            continue
        recorte = texto.strip()
        if len(recorte) > max_chars_per_cap:
            recorte = recorte[:max_chars_per_cap].rstrip() + "…"
        partes.append(f"## {etiqueta}\n{recorte}")
    return "\n\n---\n\n".join(partes)
