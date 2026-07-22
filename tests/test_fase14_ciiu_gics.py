"""Tests Fase 14 — mapeo CIIU → Sección → GICS candidatos (fast, DT-023)."""

from ic.shared.constants.ciiu_gics import (
    ciiu_to_gics_candidates,
    ciiu_to_seccion,
)

# --- ciiu_to_seccion ---


def test_seccion_comfama_8430_es_O():
    assert ciiu_to_seccion("8430") == "O"


def test_seccion_por_division():
    assert ciiu_to_seccion("2011") == "C"   # manufactura (Andercol, químicos)
    assert ciiu_to_seccion("6810") == "L"   # inmobiliaria
    assert ciiu_to_seccion("6110") == "J"   # telecomunicaciones
    assert ciiu_to_seccion("4711") == "G"   # comercio minorista
    assert ciiu_to_seccion("8511") == "P"   # educación
    assert ciiu_to_seccion("3511") == "D"   # electricidad


def test_seccion_acepta_int_y_prefijos():
    assert ciiu_to_seccion(8430) == "O"
    assert ciiu_to_seccion("CIIU 8430") == "O"


def test_seccion_invalida():
    assert ciiu_to_seccion(None) is None
    assert ciiu_to_seccion("") is None
    assert ciiu_to_seccion("8") is None       # menos de 2 dígitos
    assert ciiu_to_seccion("0000") is None    # división 00 fuera de rango


# --- ciiu_to_gics_candidates (≥5 CIIU reales) ---


def test_candidates_comfama_8430_incluye_servicios_com_prof():
    # Comfama: caja de compensación → Sección O → "Servicios comerciales y profesionales" (2020)
    cands = ciiu_to_gics_candidates("8430")
    assert "2020" in cands


def test_candidates_banca_6810_inmobiliaria():
    # División 68 → Sección L → REITs (6010) + Gestión y desarrollo inmobiliario (6020)
    cands = ciiu_to_gics_candidates("6810")
    assert "6010" in cands and "6020" in cands


def test_candidates_seccion_financiera_K():
    # División 64 (intermediación financiera) → Sección K → Bancos/Serv. financieros/Seguros
    cands = ciiu_to_gics_candidates("6419")
    assert {"4010", "4020", "4030"}.issubset(set(cands))


def test_candidates_manufactura_incluye_materiales():
    # Andercol 2011 (químicos) → Sección C (manufactura) → multivaluado, incluye Materiales
    cands = ciiu_to_gics_candidates("2011")
    assert "1510" in cands
    assert len(cands) > 1  # la manufactura mapea a varios grupos


def test_candidates_telecom_6110():
    # División 61 → Sección J → Medios(5020) / Telecom(5010) / Software(4510)
    cands = ciiu_to_gics_candidates("6110")
    assert "5010" in cands


def test_candidates_retail_4711():
    # División 47 → Sección G → retail discrecional (2550) + básicos (3010)
    cands = ciiu_to_gics_candidates("4711")
    assert "2550" in cands and "3010" in cands


# --- casos borde ---


def test_candidates_sin_ciiu_es_vacio():
    assert ciiu_to_gics_candidates(None) == []
    assert ciiu_to_gics_candidates("") == []


def test_candidates_seccion_U_sin_correspondencia():
    # División 99 → Sección U → "Sin correspondencia" → sin candidatos
    assert ciiu_to_gics_candidates("9900") == []


def test_candidates_sin_duplicados():
    cands = ciiu_to_gics_candidates("2011")
    assert len(cands) == len(set(cands))
