"""Ensamblador determinista de la sección 2.1 (Jugadores Clave) desde hechos del KB (DT-066/B2).

Da la vuelta al flujo previo: en vez de que el LLM redacte cada celda de las fichas (round-trip con
pérdida: hechos estructurados → texto → tabla del LLM → re-parseo), la tabla 2.1 se **ensambla**
directamente desde los campos ya conocidos del KB (``entidad_atributos``, vía
``list_ficha_atributos_by_sector``). Celdas deterministas donde hay dato; el LLM solo rellena huecos
(``seccion21_holes``) antes de llamar aquí. Puro: sin I/O ni dependencias de infraestructura.

Emite EXACTAMENTE el mismo markdown que producía ``chain_03`` para 2.1 (headings de tier + una tabla
vertical ``| Campo | Valor |`` por competidor), de modo que el flujo aguas abajo no cambia: el
renderer docx (``parse_markdown`` → ``TableBlock``) y la persistencia T3
(``parse_fichas_competidores``) siguen funcionando sin tocarse. Round-trip verificado por tests.

Regla de render (DT-066/c): se emiten SOLO las filas con dato real (orden ``FICHA_KEYS``); los
campos sin valor se **omiten** (nada de "Dato no disponible" — elimina el spam de las tablas). Un
competidor con solo nombre (± país) igual se lista: mejor una ficha mínima que un placeholder.
RN-001: solo se ensambla lo que ya está en el KB; este módulo no fabrica campos.
"""

from __future__ import annotations

from ic.domain.kb.ficha_parser import (
    FICHA_KEYS,
    TIER_GLOBAL,
    TIER_REGIONAL,
    TIER_STARTUP,
)
from ic.shared.text_utils import soften_caps

# Etiquetas humanas de cada tier (verdad de terreno DT064_FICHA_SPEC). El texto debe resolver por
# ``_tier_de_heading`` al tier correcto (round-trip con ``parse_fichas_competidores``).
TIER_LABELS: dict[str, str] = {
    TIER_GLOBAL: "Referentes Globales",
    TIER_REGIONAL: "Referentes Regionales LatAm/Colombia",
    TIER_STARTUP: "Startups y Disruptores del sector",
}
TIER_ORDER: tuple[str, ...] = (TIER_GLOBAL, TIER_REGIONAL, TIER_STARTUP)

# Etiqueta legible de cada campo canónico. En la ficha, ``pais_origen`` va en la fila "Nombre +
# País"; el resto son filas propias. Cada etiqueta de fila debe mapear de vuelta a su clave por
# ``_clave_de_etiqueta`` (round-trip). También la reusa el hole-filler (``seccion21_holes``).
CAMPO_LABEL: dict[str, str] = {
    "pais_origen": "País de origen",
    "resumen_estrategico": "Resumen estratégico",
    "portafolio": "Portafolio clave",
    "propuesta_valor": "Propuesta de valor",
    "canales_precios": "Canales y precios",
    "presencia_geografica": "Presencia geográfica",
    "mayor_fortaleza": "Mayor fortaleza",
    "factor_diferencial": "Factor innovador diferencial",
}

_TITULO_21 = "## 2.1. Jugadores Clave - Líderes del Mercado"


def _ficha_prosa(nombre: str, campos: dict[str, str]) -> str:
    """Mini-párrafo en prosa de un competidor. Solo incluye campos con dato (colapso)."""
    pais = (campos.get("pais_origen") or "").strip()
    # DT-UI04b (estilo): la data local de StartIA viene en MAYÚSCULAS → normalizar a caja legible
    # (nombre/país en Title Case preservando acrónimos; descripciones en caja de oración).
    encabezado = f"**{soften_caps(nombre, titulo=True)}**"
    if pais:
        encabezado += f" *({soften_caps(pais, titulo=True)})*"
    fragmentos: list[str] = []
    for clave in FICHA_KEYS:
        if clave == "pais_origen":
            continue
        valor = (campos.get(clave) or "").strip()
        if valor:
            fragmentos.append(soften_caps(valor).rstrip("."))
    if not fragmentos:
        return encabezado
    return encabezado + " — " + ". ".join(fragmentos) + "."


def assemble_seccion_21(
    tiers: dict[str, list[str]],
    fichas: dict[str, dict[str, str]],
    citas_por_tier: dict[str, str] | None = None,
) -> str:
    """Ensambla el markdown de la sección 2.1 desde los sujetos anclados y sus campos del KB. Puro.

    ``tiers`` mapea cada tier (``global``/``regional``/``startup``) a la lista ordenada de nombres
    anclados; ``fichas`` mapea nombre → campos conocidos (``list_ficha_atributos_by_sector``);
    ``citas_por_tier`` (opcional) añade una línea de citas APA al cierre de cada tier. Emite el
    heading ``## 2.1`` + un bloque por tier (``### <label>`` + una ficha por competidor). Los tiers
    y competidores sin fichas se omiten. Devuelve ``""`` si no hay nada que emitir (el llamador
    decide el fallback). RN-001: no fabrica; solo ensambla lo que recibe del KB.
    """
    citas = citas_por_tier or {}
    partes: list[str] = [_TITULO_21, ""]
    hubo_contenido = False
    for tier in TIER_ORDER:
        nombres = [n for n in tiers.get(tier, []) if n and n.strip()]
        if not nombres:
            continue
        fichas_tier = [(n, _ficha_prosa(n, fichas.get(n, {}))) for n in nombres]
        fichas_tier = [(n, md) for n, md in fichas_tier if md]
        if not fichas_tier:
            continue
        hubo_contenido = True
        partes.append(f"### {TIER_LABELS[tier]}")
        partes.append("")
        for _, md in fichas_tier:
            partes.append(md)
            partes.append("")
        cita = (citas.get(tier) or "").strip()
        if cita:
            partes.append(cita)
            partes.append("")
    if not hubo_contenido:
        return ""
    return "\n".join(partes).strip()
