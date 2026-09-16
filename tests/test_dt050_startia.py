"""Tests DT-050/T2 — crosswalk StartIA + parser (fast, sin BD)."""

from ic.infrastructure.ner.entity_recognizer import normalize_entity
from ic.shared.constants.startia_gics import vertical_to_gics
from ic.shared.ingest.startia import parse_startia


def test_crosswalk_verticales_clave():
    assert vertical_to_gics("FinTech") == "4020"
    assert vertical_to_gics("agtech") == "3020"  # case-insensitive
    assert vertical_to_gics("Software") == "4510"
    assert vertical_to_gics("Desconocida") is None
    assert vertical_to_gics(None) is None


def _row(**kw):
    base = {
        "NOMBRE_STARTUP": "VILU LATAM",
        "RAZON_SOCIAL": "VILU LATAM S.A.S.",
        "NIT": "901861914",
        "CIUDAD": "MEDELLIN",
        "VERTICALES": "FINTECH; HRTECH",
        "ETAPA": "ACELERACION",
        "ULTIMA_RONDA": None,
        "SITIO_WEB": "WWW.LEAPCO.COM.CO",
        "ANO_FUNDACION": "2024",
        "NUMERO_EMPLEADOS": "1",
        "DESCRIPCION": "Plataforma tecnológica",
    }
    base.update(kw)
    return base


def test_parse_multivertical_dos_membresias():
    p = parse_startia(_row(), normalize=normalize_entity)
    assert p is not None
    assert p.segmento == "startup"
    assert p.nit == "901861914"
    # FINTECH → 4020, HRTECH → 2020 (Servicios comerciales y profesionales).
    sectores = {m.sector_gics for m in p.memberships}
    assert "4020" in sectores
    assert len(p.memberships) == 2
    claves = {a.clave for a in p.atributos}
    assert {"etapa", "sitio_web", "ano_fundacion"}.issubset(claves)


def test_parse_vertical_desconocida_no_rompe():
    p = parse_startia(_row(**{"VERTICALES": "Desconocida"}), normalize=normalize_entity)
    assert p is not None
    assert p.memberships == []


def test_parse_fallback_a_razon_social_y_fila_invalida():
    p = parse_startia(_row(**{"NOMBRE_STARTUP": None}), normalize=normalize_entity)
    assert p.nombre == "VILU LATAM S.A.S."
    assert (
        parse_startia(
            _row(**{"NOMBRE_STARTUP": None, "RAZON_SOCIAL": None}), normalize=normalize_entity
        )
        is None
    )
