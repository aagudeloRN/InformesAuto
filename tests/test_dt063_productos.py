"""Tests DT-063/T1 — extracción de productos/servicios de la descripción (fast, sin BD)."""

from ic.shared.text_productos import extract_productos_servicios, producto_terms

_DESC = """## Descripción general
Alpina es una empresa colombiana del sector de alimentos, bebidas y tabaco.

## Productos y servicios
Alpina produce y comercializa productos lácteos: leche, yogurt, quesos, arequipe y
bebidas lácteas. También ofrece alimentos funcionales y postres.

## Segmentos de clientes
Hogares y canal institucional.
"""


def test_extrae_solo_la_seccion_de_productos():
    sec = extract_productos_servicios(_DESC)
    assert "yogurt" in sec.lower()
    assert "quesos" in sec.lower()
    # No debe arrastrar otras secciones.
    assert "Segmentos" not in sec
    assert "Descripción general" not in sec


def test_seccion_ausente_devuelve_vacio():
    assert extract_productos_servicios("## Descripción general\nTexto sin productos.") == ""
    assert extract_productos_servicios("") == ""
    assert extract_productos_servicios(None) == ""


def test_heading_tolera_acentos_mayusculas_y_niveles():
    txt = "# PRODUCTOS Y SERVICIOS\nCemento y concreto.\n# Otra\nx"
    assert "cemento" in extract_productos_servicios(txt).lower()


def test_producto_terms_food_no_incluye_tabaco_ni_stopwords():
    terms = producto_terms(extract_productos_servicios(_DESC))
    assert {"lacteos", "yogurt", "quesos", "arequipe"}.issubset(terms)
    # 'tabaco' está en la sección "Descripción general" (etiqueta del sector), NO en productos.
    assert "tabaco" not in terms
    # Stopwords/genéricos fuera.
    assert "productos" not in terms and "empresa" not in terms


def test_producto_terms_vacio():
    assert producto_terms("") == set()
    assert producto_terms(None) == set()
