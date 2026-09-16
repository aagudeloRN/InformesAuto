"""DT-061/T2 — Filtro de relevancia puro (medios/métricas + restricción por sub-actividad).

Fast (sin BD ni modelo): fixtures deterministas. Reproduce el caso Alpina — dado el KB del grupo
3020, con sub_gics food debe devolver pares food y EXCLUIR bebidas/tabaco/medios/métricas.
"""

from __future__ import annotations

import pytest

from ic.domain.kb.relevance import (
    CompetidorRow,
    es_ruido_competidor,
    filter_rank_competidores,
)


@pytest.mark.parametrize(
    "nombre_norm",
    [
        "food and beverage industry news",
        "beverage industry news",
        "profitmargin",
        "profit peremployee",
        "ebitda",
        "revenue",
        "",
    ],
)
def test_es_ruido_detecta_medios_y_metricas(nombre_norm):
    assert es_ruido_competidor(nombre_norm) is True


@pytest.mark.parametrize(
    "nombre_norm",
    [
        "colanta",
        "alqueria",
        "nestle",
        "postobon sa",
        "coca cola co",
        "danone",
    ],
)
def test_es_ruido_no_marca_empresas_reales(nombre_norm):
    assert es_ruido_competidor(nombre_norm) is False


def _kb_3020():
    """KB del grupo 3020 tal como quedó en Alpina: food + bebidas + tabaco + medios + métricas."""
    return [
        CompetidorRow("Colanta", "colanta", "302020", verificado=True, n_chunks=4, n_menciones=4),
        CompetidorRow("Alquería", "alqueria", "302020", verificado=True, n_chunks=3, n_menciones=3),
        CompetidorRow("Nutresa", "nutresa", None, verificado=False, n_chunks=12, n_menciones=20),
        CompetidorRow(
            "Postobón SA", "postobon sa", None, verificado=False, n_chunks=20, n_menciones=40
        ),
        CompetidorRow(
            "Coca-Cola Co", "coca cola co", "302010", verificado=False, n_chunks=15, n_menciones=30
        ),
        CompetidorRow(
            "British American Tobacco",
            "british american tobacco",
            "302030",
            verificado=False,
            n_chunks=10,
            n_menciones=10,
        ),
        CompetidorRow(
            "Beverage Industry News",
            "beverage industry news",
            None,
            verificado=False,
            n_chunks=8,
            n_menciones=8,
        ),
        CompetidorRow(
            "ProfitMargin", "profitmargin", None, verificado=False, n_chunks=6, n_menciones=6
        ),
    ]


def test_sub_food_restringe_a_pares_food_verificados():
    nombres = filter_rank_competidores(_kb_3020(), sub_gics="302020")
    # Solo los pares food (verificados); bebidas/tabaco/medios/métricas excluidos.
    assert nombres == ["Colanta", "Alquería"]
    assert "Postobón SA" not in nombres and "Coca-Cola Co" not in nombres
    assert "British American Tobacco" not in nombres
    assert "Beverage Industry News" not in nombres and "ProfitMargin" not in nombres


def test_sin_sub_gics_conserva_grupo_excluyendo_ruido():
    # Invariante: sin sub-código, comportamiento de grupo; solo ruido (medios/métricas) fuera.
    nombres = filter_rank_competidores(_kb_3020(), sub_gics=None)
    assert "Beverage Industry News" not in nombres and "ProfitMargin" not in nombres
    # Verificados primero, luego por evidencia (chunks).
    assert nombres[0] in {"Colanta", "Alquería"}
    assert "Postobón SA" in nombres  # sin sub no se descarta la industria ajena


def test_sub_sin_pares_relevantes_cae_al_grupo():
    # sub food pero el KB solo tiene candidatos sin tag ni verificar → no se pierde todo.
    rows = [
        CompetidorRow("Nutresa", "nutresa", None, verificado=False, n_chunks=12, n_menciones=20),
        CompetidorRow(
            "Alimentos XYZ", "alimentos xyz", None, verificado=False, n_chunks=5, n_menciones=5
        ),
    ]
    nombres = filter_rank_competidores(rows, sub_gics="302020")
    assert nombres == ["Nutresa", "Alimentos XYZ"]


def test_alcance_global_filtra_locales():
    # DT-061b: componente de clase mundial → solo actores globales; locales y sin-clasificar fuera.
    rows = [
        CompetidorRow(
            "Nestlé",
            "nestlé",
            "302020",
            alcance="global",
            verificado=True,
            n_chunks=3,
            n_menciones=3,
        ),
        CompetidorRow(
            "Danone",
            "danone",
            "302020",
            alcance="global",
            verificado=True,
            n_chunks=2,
            n_menciones=2,
        ),
        CompetidorRow(
            "Colanta",
            "colanta",
            "302020",
            alcance="local",
            verificado=True,
            n_chunks=9,
            n_menciones=9,
        ),
        CompetidorRow(
            "Nutresa NER",
            "nutresa ner",
            None,
            alcance=None,
            verificado=False,
            n_chunks=20,
            n_menciones=20,
        ),
    ]
    nombres = filter_rank_competidores(rows, sub_gics="302020", alcance="global")
    assert nombres == ["Nestlé", "Danone"]  # locales y sin-clasificar excluidos


def test_alcance_global_sub_estricto_excluye_sub_ajena():
    # DT-062b: en el tier de clase mundial, un `verificado` de OTRA sub (food) NO debe colarse en
    # el ancla de tabaco. Sub-estricto sin puente verificado → tabaco con solo globales food = [].
    rows = [
        CompetidorRow(
            "Nestlé",
            "nestlé",
            "302020",
            alcance="global",
            verificado=True,
            n_chunks=3,
            n_menciones=3,
        ),
        CompetidorRow(
            "Danone",
            "danone",
            "302020",
            alcance="global",
            verificado=True,
            n_chunks=2,
            n_menciones=2,
        ),
    ]
    # Empresa de tabaco (302030): ninguno de los globales food coincide → ancla vacía.
    assert filter_rank_competidores(rows, sub_gics="302030", alcance="global") == []
    # Invariante food: una empresa food/302020 sigue viendo sus globales food.
    assert filter_rank_competidores(rows, sub_gics="302020", alcance="global") == [
        "Nestlé",
        "Danone",
    ]


def test_alcance_global_sub_estricto_no_fallback_a_grupo():
    # Sin fallback a grupo en el tier global: si no hay match de sub, queda vacío (no "conserva").
    rows = [
        CompetidorRow(
            "Nestlé",
            "nestlé",
            "302020",
            alcance="global",
            verificado=True,
            n_chunks=3,
            n_menciones=3,
        ),
    ]
    assert filter_rank_competidores(rows, sub_gics="302010", alcance="global") == []


def test_sin_alcance_no_filtra_por_alcance():
    # Invariante: si no se pide alcance, no se filtra por él (otros componentes intactos).
    rows = [
        CompetidorRow(
            "Colanta",
            "colanta",
            "302020",
            alcance="local",
            verificado=True,
            n_chunks=5,
            n_menciones=5,
        ),
    ]
    assert filter_rank_competidores(rows, sub_gics="302020") == ["Colanta"]


def test_respeta_limit():
    rows = [
        CompetidorRow(f"E{i}", f"e{i}", None, verificado=False, n_chunks=i, n_menciones=i)
        for i in range(20)
    ]
    assert len(filter_rank_competidores(rows, limit=8)) == 8
