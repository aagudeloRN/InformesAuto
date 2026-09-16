"""DT-061/T3 — Curación (purga de ruido, no-degrada verificado) + siembra de pares reales.

Fast (sin BD ni modelo): el contrato SQL de la purga se verifica con sesión falsa; la semilla se
valida por forma y por consistencia con la clave de dedup del NER (`normalize_entity`).
"""

from __future__ import annotations

from ic.data.models.entidad import ESTADO_CANDIDATO, ESTADO_VERIFICADO
from ic.data.repositories.entidad_repo import EntidadRepository
from ic.infrastructure.ner.entity_recognizer import normalize_entity
from ic.shared.constants.gics_groups import (
    SUB_GICS_302010_BEVERAGES,
    SUB_GICS_302020_FOOD,
    SUB_GICS_302030_TOBACCO,
)
from ic.shared.data.pares_sectoriales import PARES_VERIFICADOS, pares_de_sector
from tests.test_kb_entidades import _FakeSession

_SUBS_VALIDOS = {SUB_GICS_302010_BEVERAGES, SUB_GICS_302020_FOOD, SUB_GICS_302030_TOBACCO}


# --- Purga de ruido (contrato SQL, no-degrada verificado) ---


def test_descartar_ruido_marca_solo_ruido_y_no_degrada_verificado():
    # Filas candidatas (id, nombre_normalizado); solo las de ruido deben marcarse.
    sess = _FakeSession(
        select_rows=[
            (1, "colanta"),
            (2, "beverage industry news"),  # medio → ruido
            (3, "profitmargin"),  # métrica → ruido
            (4, "nestlé"),
        ]
    )
    marcados = EntidadRepository(sess).descartar_ruido_competidores()
    assert marcados == ["beverage industry news", "profitmargin"]
    # El SELECT excluye ya-descartados y verificados (idempotencia + no-degradación).
    sel = sess.sqls[0]
    assert "NOT IN (:descartado, :verificado)" in sel
    # El UPDATE lleva el guard anti-degradación de verificado.
    updates = [q for q in sess.sqls if q.startswith("UPDATE")]
    assert len(updates) == 2 and all("estado <> :verificado" in u for u in updates)


def test_descartar_ruido_dry_run_no_escribe():
    sess = _FakeSession(select_rows=[(1, "food and beverage industry news")])
    marcados = EntidadRepository(sess).descartar_ruido_competidores(dry_run=True)
    assert marcados == ["food and beverage industry news"]
    assert not any(q.startswith("UPDATE") for q in sess.sqls)  # sin escritura
    assert sess.commits == 0


# --- Semilla de pares verificados ---


def test_semilla_3020_tiene_pares_lacteos_reales():
    pares = pares_de_sector("3020")
    nombres = {p["nombre"] for p in pares}
    assert {"Colanta", "Alquería", "Nestlé", "Danone"} <= nombres
    assert "Alpina" not in nombres  # la empresa analizada se omite a propósito


def test_semilla_alcance_global_vs_local():
    # DT-061b: los globales son clase mundial; las lácteas locales colombianas van a 'local'.
    pares = {p["nombre"]: p["alcance"] for p in pares_de_sector("3020")}
    assert pares["Nestlé"] == "global" and pares["Danone"] == "global"
    assert pares["Yili"] == "global" and pares["Grupo Nutresa"] == "global"
    assert pares["Colanta"] == "local" and pares["Alquería"] == "local"


def test_semilla_shape_y_sub_gics_valido():
    for sector, pares in PARES_VERIFICADOS.items():
        assert sector.isdigit() and len(sector) == 4
        vistos: set[str] = set()
        for p in pares:
            assert p["nombre"] and p["nombre_normalizado"]
            assert p["sub_gics"] in _SUBS_VALIDOS
            assert p["alcance"] in {"global", "local"}
            assert p["nombre_normalizado"] not in vistos  # sin duplicados
            vistos.add(p["nombre_normalizado"])


def test_semilla_normalizado_consistente_con_ner():
    # El nombre_normalizado precalculado DEBE coincidir con la clave de dedup del NER,
    # o la siembra no consolidaría con los candidatos existentes (duplicaría).
    for pares in PARES_VERIFICADOS.values():
        for p in pares:
            assert normalize_entity(p["nombre"]) == p["nombre_normalizado"], p["nombre"]


def test_seed_rows_son_verificados():
    from scripts.curar_kb_competidores import _seed_rows

    filas = _seed_rows("3020")
    assert filas and all(f.estado == ESTADO_VERIFICADO for f in filas)
    assert all(f.sector_gics == "3020" and f.sub_gics and f.alcance for f in filas)
    assert ESTADO_CANDIDATO != ESTADO_VERIFICADO  # sanity
