"""DT-066/B2 — Hole-filler estructurado: parseo del JSON + orquestación acotada (puro).

Fast: sin BD ni LLM real (cadena fake). Verifica RN-001 (null/ausencia no entran, no pisa el KB),
las cotas de presupuesto y que solo devuelve como "rellenados" los valores nuevos (para persistir).
"""

from __future__ import annotations

from ic.domain.chains.chain_03b_ficha_fields import parse_ficha_fields
from ic.domain.kb.ficha_parser import FICHA_KEYS, TIER_GLOBAL, TIER_REGIONAL
from ic.domain.kb.seccion21_holes import compute_holes, fill_holes

# --------------------------------------------------------------------------- parse_ficha_fields


def test_parse_conserva_solo_claves_pedidas_y_utiles():
    raw = """```json
    {"resumen_estrategico": "Líder mundial en snacks.", "portafolio": null,
     "presencia_geografica": "Dato no disponible.", "otra_cosa": "x"}
    ```"""
    out = parse_ficha_fields(raw, {"resumen_estrategico", "portafolio", "presencia_geografica"})
    assert out == {"resumen_estrategico": "Líder mundial en snacks."}
    # portafolio=null y presencia="Dato no disponible" NO entran (RN-001); "otra_cosa" no se pidió.


def test_parse_sin_json_devuelve_vacio():
    assert parse_ficha_fields("no hay json aquí", {"portafolio"}) == {}
    assert parse_ficha_fields("", {"portafolio"}) == {}


def test_parse_tolera_objeto_sin_fence():
    raw = 'Aquí va: {"pais_origen": "EE. UU."} fin'
    assert parse_ficha_fields(raw, {"pais_origen"}) == {"pais_origen": "EE. UU."}


# --------------------------------------------------------------------------- compute_holes


def test_compute_holes_lista_campos_vacios():
    holes = compute_holes({"pais_origen": "Suiza", "portafolio": "  "})
    assert "pais_origen" not in holes  # tiene valor
    assert "portafolio" in holes  # solo espacios → hueco
    assert "resumen_estrategico" in holes


# --------------------------------------------------------------------------- fill_holes


class _FakeChain:
    """Cadena que devuelve un JSON fijo por nombre y cuenta invocaciones."""

    def __init__(self, por_nombre: dict[str, str]):
        self._por_nombre = por_nombre
        self.calls: list[str] = []

    def invoke(self, payload):
        self.calls.append(payload["nombre"])
        return self._por_nombre.get(payload["nombre"], "{}")


_TIERS = {TIER_GLOBAL: ["Nestlé", "Danone"], TIER_REGIONAL: ["Colombina"]}


def test_fill_holes_rellena_solo_lo_nuevo_sin_pisar_kb():
    fichas = {"Nestlé": {"pais_origen": "Suiza"}}  # tiene país; le faltan los demás
    chain = _FakeChain(
        {
            "Nestlé": '{"pais_origen": "OTRO PAÍS", "portafolio": "Galletas y café."}',
        }
    )
    enr, rell = fill_holes(_TIERS, fichas, chain, "3020", "evidencia", max_competidores=5)
    # No pisa el país del KB…
    assert enr["Nestlé"]["pais_origen"] == "Suiza"
    # …pero sí añade el hueco portafolio, y solo eso va en "rellenados" (para persistir citado).
    assert enr["Nestlé"]["portafolio"] == "Galletas y café."
    assert rell == {"Nestlé": {"portafolio": "Galletas y café."}}
    # No muta la ficha original.
    assert "portafolio" not in fichas["Nestlé"]


def test_fill_holes_respeta_cota_de_competidores():
    chain = _FakeChain({})
    _, _ = fill_holes(_TIERS, {}, chain, "3020", "evidencia", max_competidores=2)
    # 3 anclados con huecos, pero la cota corta en 2 llamadas (globales primero).
    assert chain.calls == ["Nestlé", "Danone"]


def test_fill_holes_sin_cadena_o_sin_evidencia_es_noop():
    fichas = {"Nestlé": {}}
    enr, rell = fill_holes(_TIERS, fichas, None, "3020", "evidencia", max_competidores=5)
    assert enr == {"Nestlé": {}} and rell == {}
    chain = _FakeChain({"Nestlé": '{"portafolio": "x"}'})
    enr2, rell2 = fill_holes(_TIERS, fichas, chain, "3020", "   ", max_competidores=5)
    assert rell2 == {} and chain.calls == []  # evidencia vacía → no invoca


def test_fill_holes_salta_competidores_sin_huecos():
    fichas = {"Nestlé": {k: "x" for k in FICHA_KEYS}}  # ficha completa → sin huecos
    chain = _FakeChain({"Danone": '{"portafolio": "Yogures."}'})
    enr, rell = fill_holes(_TIERS, fichas, chain, "3020", "evidencia", max_competidores=5)
    assert "Nestlé" not in chain.calls  # ya estaba completa
    assert rell == {"Danone": {"portafolio": "Yogures."}}
