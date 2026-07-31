"""Tests DT-050 — mapeo CIIU por división + parser EmpresasColombia (fast, sin BD)."""

from ic.infrastructure.ner.entity_recognizer import normalize_entity
from ic.shared.constants.ciiu_gics import (
    ciiu_division_to_gics,
    extract_all_ciiu_from_text,
    extract_ciiu_from_text,
)
from ic.shared.ingest.empresas_colombia import parse_empresa_colombia

# --- extracción del CIIU embebido ---


def test_extract_ciiu_primero():
    assert extract_ciiu_from_text("Elaboración De Productos Lácteos (C1040)") == "1040"
    assert extract_ciiu_from_text("Sin código aquí") is None
    assert extract_ciiu_from_text(None) is None


def test_extract_all_ciiu_multiactividad_sin_duplicados():
    txt = "Actividades De Administración (M7010); Consultoría (M7020); Otra (M7010)"
    assert extract_all_ciiu_from_text(txt) == ["7010", "7020"]
    assert extract_all_ciiu_from_text("") == []


# --- división CIIU → grupo GICS (único) ---


def test_division_alimentos_bebidas_tabaco_es_3020():
    assert ciiu_division_to_gics("1040") == "3020"   # lácteos
    assert ciiu_division_to_gics("1101") == "3020"   # bebidas alcohólicas
    assert ciiu_division_to_gics("1200") == "3020"   # tabaco
    assert ciiu_division_to_gics("0141") == "3020"   # ganado bovino (agro)


def test_division_casos_representativos():
    assert ciiu_division_to_gics("2910") == "2510"   # vehículos → automóviles
    assert ciiu_division_to_gics("6201") == "4510"   # programación → software
    assert ciiu_division_to_gics("6810") == "6020"   # inmobiliaria
    assert ciiu_division_to_gics("6419") == "4010"   # banca
    assert ciiu_division_to_gics("2100") == "3520"   # farmacéutica


def test_override_comercio_basicos_es_3010():
    # Comercio de básicos (alimentos/farmacia) → consumo básico (3010), no discrecional (2550).
    assert ciiu_division_to_gics("4711") == "3010"   # minorista no especializado
    assert ciiu_division_to_gics("4773") == "3010"   # farmacéuticos
    # El resto del comercio cae en el default de división (discrecional).
    assert ciiu_division_to_gics("4751") == "2550"


def test_division_sin_codigo_o_sin_correspondencia():
    assert ciiu_division_to_gics(None) is None
    assert ciiu_division_to_gics("9") is None
    assert ciiu_division_to_gics("9900") is None     # Sección U → sin correspondencia


# --- parser EmpresasColombia ---


def _row(**kw):
    base = {
        "Compañía": "Grupo Nutresa S.A.",
        "Sector (Local)": "Elaboración De Productos Lácteos (C1040)",
        "Actividades principales (Local)": "Elaboración De Productos Lácteos (C1040)",
        "Ciudad": "Medellín",
        "Estado/Provincia/Región": "Antioquia",
        "CO-NIT": "890900050",
        "Total Ingreso Operativo": "20.578.987,8",
        "Número de empleados": "47.033 (2025)",
        "Forma Legal": "S.A.",
        "Principales Ejecutivos": "Angela María Tafur",
        "Descripción de la compañía / productos": "Alimentos procesados",
    }
    base.update(kw)
    return base


def test_parse_nutresa_lacteos_food():
    p = parse_empresa_colombia(_row(), normalize=normalize_entity)
    assert p is not None
    assert p.nit == "890900050"
    assert p.nombre_normalizado == "grupo nutresa"
    assert p.ciudad == "Medellín"
    assert len(p.memberships) == 1
    assert p.memberships[0].sector_gics == "3020"
    assert p.memberships[0].sub_gics == "302020"  # lácteos → alimentos
    claves = {a.clave for a in p.atributos}
    assert {"ingreso_operativo", "n_empleados"}.issubset(claves)


def test_parse_multiactividad_varias_membresias():
    p = parse_empresa_colombia(
        _row(**{
            "Sector (Local)": "Cría De Ganado (A0141); Elaboración De Lácteos (C1040)",
            "Actividades principales (Local)": "",
        }),
        normalize=normalize_entity,
    )
    assert p is not None
    # Ambos CIIU mapean a 3020 → una sola membresía deduplicada por grupo.
    assert [m.sector_gics for m in p.memberships] == ["3020"]


def test_parse_nit_solo_digitos_y_fila_invalida():
    p = parse_empresa_colombia(_row(**{"CO-NIT": " 890.900-050 "}), normalize=normalize_entity)
    assert p.nit == "890900050"
    assert parse_empresa_colombia(_row(**{"Compañía": None}), normalize=normalize_entity) is None
