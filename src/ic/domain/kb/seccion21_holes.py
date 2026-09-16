"""Orquestación del hole-filling de la sección 2.1 (DT-066/B2). Puro salvo la cadena inyectada.

Calcula, para cada competidor anclado, los campos de ficha que faltan (``FICHA_KEYS`` sin valor en
el KB) y los rellena invocando la cadena ``chain_03b_ficha_fields`` con la evidencia RAG. Es el
puente entre los hechos deterministas del KB y ``assemble_seccion_21``: tras esto, las fichas llevan
lo del KB + lo que la evidencia soporte para los huecos.

Cotas (presupuesto ADR-002): se procesan como máximo ``max_competidores`` competidores con huecos
(los primeros en orden de tiers → prioriza globales anclados). Cada competidor = una llamada al LLM.
RN-001: los valores rellenados son ``candidato`` (los devuelve ``rellenados`` para persistirlos
citados); ``null``/frases de ausencia no entran (las filtra ``parse_ficha_fields``). Sin cadena o
sin huecos → devuelve las fichas intactas y ``{}``.
"""

from __future__ import annotations

import logging

from langchain_core.runnables import Runnable

from ic.domain.chains.chain_03b_ficha_fields import parse_ficha_fields
from ic.domain.kb.ficha_parser import FICHA_KEYS
from ic.domain.kb.seccion21_assembler import CAMPO_LABEL, TIER_ORDER

logger = logging.getLogger(__name__)


def compute_holes(campos: dict[str, str]) -> list[str]:
    """Campos canónicos (``FICHA_KEYS``) sin valor útil en la ficha. Preserva el orden canónico."""
    return [k for k in FICHA_KEYS if not (campos.get(k) or "").strip()]


def _nombres_ordenados(tiers: dict[str, list[str]]) -> list[str]:
    """Nombres anclados en orden de tiers (global → regional → startup), sin duplicar."""
    orden: list[str] = []
    vistos: set[str] = set()
    for tier in TIER_ORDER:
        for nombre in tiers.get(tier, []):
            clave = (nombre or "").strip().casefold()
            if clave and clave not in vistos:
                vistos.add(clave)
                orden.append(nombre)
    return orden


def _format_campos_faltantes(faltantes: list[str]) -> str:
    """Lista legible ``clave — Etiqueta`` de los campos a extraer (guía el JSON del LLM)."""
    return "\n".join(f"- {k}: {CAMPO_LABEL[k]}" for k in faltantes)


def fill_holes(
    tiers: dict[str, list[str]],
    fichas: dict[str, dict[str, str]],
    chain: Runnable | None,
    sector_gics: str,
    evidencia_rag: str,
    max_competidores: int,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Rellena los huecos de ficha de los competidores anclados desde la evidencia. Acotado.

    Devuelve ``(fichas_enriquecidas, rellenados)``: la primera es una copia de ``fichas`` con los
    huecos completados; la segunda son SOLO los valores nuevos por competidor (para persistirlos
    como ``candidato`` citado). No muta ``fichas``. ``chain=None`` o ``max_competidores<=0`` → sin
    cambios. RN-001: un valor solo se añade si el campo estaba vacío y la evidencia lo soporta.
    """
    enriquecidas: dict[str, dict[str, str]] = {n: dict(c) for n, c in fichas.items()}
    rellenados: dict[str, dict[str, str]] = {}
    if chain is None or max_competidores <= 0 or not evidencia_rag.strip():
        return enriquecidas, rellenados
    procesados = 0
    for nombre in _nombres_ordenados(tiers):
        if procesados >= max_competidores:
            break
        faltantes = compute_holes(enriquecidas.get(nombre, {}))
        if not faltantes:
            continue
        procesados += 1
        try:
            raw = chain.invoke(
                {
                    "nombre": nombre,
                    "sector_gics": sector_gics,
                    "evidencia_rag": evidencia_rag,
                    "campos_faltantes": _format_campos_faltantes(faltantes),
                }
            )
        except Exception:  # noqa: BLE001 — el hole-filling es un boost; nunca rompe la corrida.
            logger.warning("hole-filling falló para %r", nombre, exc_info=True)
            continue
        nuevos = parse_ficha_fields(raw, set(faltantes))
        if not nuevos:
            continue
        campos = enriquecidas.setdefault(nombre, {})
        for clave, valor in nuevos.items():
            if not (campos.get(clave) or "").strip():  # no pisa lo del KB
                campos[clave] = valor
                rellenados.setdefault(nombre, {})[clave] = valor
    logger.info(
        "hole-filling: %d competidores procesados, %d con datos nuevos",
        procesados,
        len(rellenados),
    )
    return enriquecidas, rellenados
