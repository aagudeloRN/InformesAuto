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


# --- rank_by_product_overlap (DT-063/T3) ---


def _pr(nombre, descriptor, *, alcance=None, verificado=False, tiebreak=0):
    from ic.domain.kb.relevance import ProductoRankRow

    return ProductoRankRow(
        nombre=nombre, nombre_normalizado=nombre.lower(), descriptor=descriptor,
        alcance=alcance, verificado=verificado, tiebreak=tiebreak,
    )


def test_rank_ordena_por_solape_luego_evidencia():
    from ic.domain.kb.relevance import rank_by_product_overlap

    rows = [
        _pr("Danone", "yogurt y lácteos", tiebreak=1),
        _pr("PepsiCo", "gaseosas y snacks", tiebreak=99),   # sin solape lácteo
        _pr("Lactalis", "quesos y leche", tiebreak=1),
    ]
    out = rank_by_product_overlap(rows, {"lacteos", "yogurt", "leche", "quesos"}, limit=8)
    assert set(out[:2]) == {"Danone", "Lactalis"}  # solape lácteo primero
    assert out[-1] == "PepsiCo"                     # más evidencia pero sin solape → al final


def test_rank_require_overlap_descarta_sin_solape():
    from ic.domain.kb.relevance import rank_by_product_overlap

    rows = [
        _pr("Danone", "yogurt lácteos", alcance="global"),
        _pr("Philip Morris", "tabaco cigarrillos", alcance="global"),
    ]
    out = rank_by_product_overlap(
        rows, {"lacteos", "yogurt"}, alcance="global", require_overlap=True
    )
    assert out == ["Danone"]  # tabaco sin solape lácteo → fuera (mejor vacío que ajeno)


def test_rank_sin_productos_cae_a_evidencia_sin_filtrar():
    from ic.domain.kb.relevance import rank_by_product_overlap

    rows = [_pr("A", "x", tiebreak=5), _pr("B", "y", tiebreak=9)]
    out = rank_by_product_overlap(rows, set(), require_overlap=True, limit=8)
    assert out == ["B", "A"]  # fallback: sin términos no se filtra, orden por tiebreak


def test_rank_excluye_ruido_y_filtra_alcance():
    from ic.domain.kb.relevance import rank_by_product_overlap

    rows = [
        _pr("Food Industry News", "lácteos noticias", alcance="global"),  # ruido (news)
        _pr("Nestlé", "lácteos", alcance="global"),
        _pr("Colanta", "lácteos", alcance="local"),
    ]
    out = rank_by_product_overlap(rows, {"lacteos"}, alcance="global", require_overlap=True)
    assert out == ["Nestlé"]
