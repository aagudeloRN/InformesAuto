"""DT-066/B2 — Ensamblador determinista de la sección 2.1 (puro).

Fast: sin BD ni LLM. Verifica el colapso de vacíos (nada de "Dato no disponible"), el orden de tiers
y el round-trip crítico: lo ensamblado debe re-parsearse a los mismos hechos (garantiza que la
persistencia T3 y el render docx siguen funcionando sin tocarse).
"""

from __future__ import annotations

from ic.domain.kb.ficha_parser import (
    TIER_GLOBAL,
    TIER_REGIONAL,
    TIER_STARTUP,
    parse_fichas_competidores,
)
from ic.domain.kb.seccion21_assembler import assemble_seccion_21

_FICHAS = {
    "Nestlé": {
        "pais_origen": "Suiza",
        "resumen_estrategico": "Líder mundial en alimentos y bebidas.",
        "portafolio": "Galletas, snacks y confitería.",
        "presencia_geografica": "189 países.",
        "factor_diferencial": "Nutrición personalizada.",
    },
    "Colombina": {"pais_origen": "Colombia", "portafolio": "Confitería y galletas."},
    "NotCo": {"factor_diferencial": "IA para formular recetas."},
}
_TIERS = {
    TIER_GLOBAL: ["Nestlé"],
    TIER_REGIONAL: ["Colombina"],
    TIER_STARTUP: ["NotCo"],
}


def test_assemble_emite_tiers_en_orden_con_titulo():
    md = assemble_seccion_21(_TIERS, _FICHAS)
    assert "## 2.1. Jugadores Clave" in md
    i_g = md.index("Referentes Globales")
    i_r = md.index("Referentes Regionales")
    i_s = md.index("Startups")
    assert i_g < i_r < i_s  # orden global → regional → startup


def test_assemble_colapsa_vacios_sin_placeholder():
    md = assemble_seccion_21(_TIERS, _FICHAS)
    # No estampa ninguna variante de ausencia (elimina el spam de "no disponible").
    assert "no disponible" not in md.lower()
    assert "no especific" not in md.lower()
    # Colombina no tiene presencia/canales → esas filas NO aparecen para ella.
    bloque_col = md[md.index("Colombina") : md.index("NotCo")]
    assert "Presencia geográfica" not in bloque_col
    assert "Canales y precios" not in bloque_col
    assert "Confitería" in bloque_col  # el campo con dato sí


def test_assemble_competidor_solo_con_diferenciador_se_lista():
    # NotCo solo tiene factor_diferencial (sin país): igual se emite con nombre + su campo.
    md = assemble_seccion_21(_TIERS, _FICHAS)
    assert "NotCo" in md
    assert "IA para formular recetas" in md


def test_round_trip_assemble_parse_recupera_hechos():
    # Lo ensamblado se re-parsea a los MISMOS hechos → T3 y el render docx no se rompen.
    md = assemble_seccion_21(_TIERS, _FICHAS)
    fichas = {f.nombre: f for f in parse_fichas_competidores(md)}
    assert set(fichas) == {"Nestlé", "Colombina", "NotCo"}
    assert fichas["Nestlé"].tier == TIER_GLOBAL
    assert fichas["Nestlé"].campos["pais_origen"] == "Suiza"
    assert fichas["Nestlé"].campos["resumen_estrategico"].startswith("Líder mundial")
    assert fichas["Nestlé"].campos["portafolio"].startswith("Galletas")
    assert fichas["Nestlé"].campos["presencia_geografica"] == "189 países."
    assert fichas["Nestlé"].campos["factor_diferencial"].startswith("Nutrición")
    assert fichas["Colombina"].tier == TIER_REGIONAL
    assert fichas["Colombina"].campos["pais_origen"] == "Colombia"
    assert "presencia_geografica" not in fichas["Colombina"].campos
    assert fichas["NotCo"].tier == TIER_STARTUP
    assert fichas["NotCo"].campos["factor_diferencial"].startswith("IA")


def test_assemble_incluye_citas_por_tier():
    md = assemble_seccion_21(
        {TIER_GLOBAL: ["Nestlé"]},
        _FICHAS,
        citas_por_tier={TIER_GLOBAL: "(Euromonitor, 2024. Statista, 2025.)"},
    )
    assert "(Euromonitor, 2024. Statista, 2025.)" in md


def test_assemble_vacio_devuelve_cadena_vacia():
    assert assemble_seccion_21({}, {}) == ""
    # Sin tiers ni fichas no hay nada que emitir.
    assert assemble_seccion_21({}, _FICHAS) == ""


def test_assemble_competidor_solo_nombre_se_lista():
    # Un global anclado sin datos aún (KB frío): el NOMBRE es el hecho anclado → se lista igual
    # (mejor una ficha mínima que omitir un competidor real). Sin filas de campo, sin placeholder.
    md = assemble_seccion_21({TIER_GLOBAL: ["Fantasma"]}, {})
    assert "Fantasma" in md
    assert "no disponible" not in md.lower()


def test_assemble_omite_tier_sin_nombres():
    md = assemble_seccion_21({TIER_GLOBAL: ["Nestlé"]}, _FICHAS)
    assert "Referentes Globales" in md
    assert "Referentes Regionales" not in md
    assert "Startups" not in md
