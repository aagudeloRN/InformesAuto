"""Tests DT-050/T3 — formateo del bloque de jugadores locales + invariante (fast, sin BD)."""

from ic.domain.kb.relevance import (
    CompetidorRow,
    LocalRow,
    filter_rank_competidores,
    format_jugadores_locales,
)


def test_format_vacio_es_string_vacio():
    # Invariante: sin locales (flag OFF o directorio sin sector) → "" → prompt idéntico.
    assert format_jugadores_locales([], []) == ""


def test_format_regionales_y_startups():
    reg = [LocalRow(nombre="Grupo Nutresa", ciudad="Medellín", actividad="Alimentos", tamano="20B")]
    st = [LocalRow(nombre="Foodology", ciudad="Bogotá", segmento="startup")]
    out = format_jugadores_locales(reg, st)
    assert "Referentes regionales" in out
    assert "Startups regionales" in out
    assert "- Grupo Nutresa — Medellín — Alimentos — 20B" in out
    assert "- Foodology — Bogotá" in out


def test_format_solo_regionales():
    out = format_jugadores_locales([LocalRow(nombre="Colombina")], [])
    assert "Referentes regionales" in out
    assert "Startups" not in out
    assert out.endswith("- Colombina")


def test_no_diluye_global_excluye_locales():
    # El path global filtra alcance=global; los locales del directorio no se cuelan (no diluye).
    filas = [
        CompetidorRow(nombre="Nestlé", nombre_normalizado="nestle", alcance="global"),
        CompetidorRow(nombre="Alpina Local", nombre_normalizado="alpina local", alcance="local"),
        CompetidorRow(nombre="Sin Clasificar", nombre_normalizado="sin clasificar", alcance=None),
    ]
    out = filter_rank_competidores(filas, alcance="global")
    assert out == ["Nestlé"]
