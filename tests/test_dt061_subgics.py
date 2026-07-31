"""DT-061/T1 — Resolver puro de sub-código GICS (granularidad food/beverage/tobacco).

Fast (sin BD ni modelo): mapa keyword → sub-código de la descripción de la empresa. Determinista;
None fuera del grupo 3020 o sin señal (invariante: anclaje a nivel de grupo).
"""

from __future__ import annotations

from ic.shared.constants.gics_groups import (
    SUB_GICS_302010_BEVERAGES,
    SUB_GICS_302020_FOOD,
    SUB_GICS_302030_TOBACCO,
    resolve_sub_gics,
)


def test_lacteos_resuelve_food():
    desc = "Empresa colombiana de productos lácteos: leche, yogurt y quesos."
    assert resolve_sub_gics(desc, "3020") == SUB_GICS_302020_FOOD


def test_bebidas_resuelve_beverages():
    desc = "Compañía de bebidas gaseosas y jugos."
    assert resolve_sub_gics(desc, "3020") == SUB_GICS_302010_BEVERAGES


def test_tabaco_resuelve_tobacco():
    desc = "Tabacalera productora de cigarrillos."
    assert resolve_sub_gics(desc, "3020") == SUB_GICS_302030_TOBACCO


def test_tabaco_prima_sobre_otros_por_especificidad():
    # El orden de evaluación prioriza tabaco aunque el texto mencione alimentos.
    desc = "Grupo con línea de tabaco y snacks alimenticios."
    assert resolve_sub_gics(desc, "3020") == SUB_GICS_302030_TOBACCO


def test_insensible_a_acentos_y_mayusculas():
    assert resolve_sub_gics("PRODUCTOS LÁCTEOS", "3020") == SUB_GICS_302020_FOOD


def test_sin_senal_devuelve_none():
    assert resolve_sub_gics("Servicios generales del sector.", "3020") is None


def test_otro_grupo_devuelve_none():
    # Invariante: fuera de 3020 no se refina (aunque el texto tenga keywords).
    assert resolve_sub_gics("productos lácteos", "2510") is None


def test_descripcion_vacia_devuelve_none():
    assert resolve_sub_gics(None, "3020") is None
    assert resolve_sub_gics("", "3020") is None
