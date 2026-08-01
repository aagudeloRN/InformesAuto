"""Siembra del KB desde los informes manuales (DT-064) — piezas puras.

Fast: ``extract_seccion_markdown`` (docx-blocks → markdown de 2.1) y ``merge_fichas_parciales`` (une
las dos tablas por tier) son puras (sin BD ni python-docx: los bloques se construyen a mano). Cubren
la especificidad de la verdad de terreno: marcadores de tier como párrafo (no Heading), recorte
2.1..2.2, saneo de `|`, y la fusión de las fichas parciales de un mismo competidor.
"""

from __future__ import annotations

from ic.domain.kb.ficha_parser import (
    TIER_GLOBAL,
    TIER_REGIONAL,
    FichaCompetidor,
    merge_fichas_parciales,
    parse_fichas_competidores,
)
from ic.domain.kb.informe_seccion import extract_seccion_markdown
from ic.infrastructure.sources.docx_reader import DocxParagraph, DocxTable

# ------------------------------------------------------------------------- extract_seccion_markdown


def _bloques_informe():
    """Reproduce la estructura real de 2.1: tier como párrafo + tabla ancha, x2 por tier."""
    return [
        DocxParagraph("1.5 Algo previo", "Heading 2"),
        DocxTable([["Ignorar", "esta"], ["tabla", "previa"]]),  # antes de 2.1 → se descarta
        DocxParagraph("2.1. Jugadores Clave - Líderes del Mercado", "Heading 2"),
        DocxParagraph("El ecosistema actual cuenta con actores principales.", "Body Text"),
        DocxParagraph("Referentes Globales", "Body Text"),
        DocxTable([
            ["Empresa", "País de Origen", "Portafolio / Productos"],
            ["Nestlé S.A.", "Suiza", "Galletas | snacks"],  # el `|` debe sanearse
        ]),
        DocxParagraph("Mayor Fortaleza - Referentes Globales", "Body Text"),
        DocxTable([
            ["Empresa", "Propuesta de Valor", "Mayor Fortaleza"],
            ["Nestlé S.A.", "Nutrición y calidad", "Red de distribución global"],
        ]),
        DocxParagraph("Referentes Regionales (Latam/Colombia)", "Body Text"),
        DocxTable([
            ["Empresa", "País de Origen", "Portafolio / Productos"],
            ["Colombina S.A.", "Colombia", "Confitería"],
        ]),
        DocxParagraph("2.2. División de competidores", "Heading 2"),
        DocxTable([["Ya", "no"], ["cuenta", "esta"]]),  # tras 2.2 → se descarta
    ]


def test_extract_recorta_seccion_y_marca_tiers():
    md = extract_seccion_markdown(_bloques_informe())
    # Solo contenido de 2.1: nada de las tablas previas/posteriores.
    assert "previa" not in md and "Ya" not in md
    # Los párrafos-marcador de tier se emiten como headings.
    assert "### Referentes Globales" in md
    assert "### Mayor Fortaleza - Referentes Globales" in md
    assert "### Referentes Regionales (Latam/Colombia)" in md
    # La narrativa (no marcador) no se emite.
    assert "ecosistema actual" not in md
    # Tablas en markdown pipe, con el `|` de celda saneado.
    assert "| Nestlé S.A. |" in md
    assert "Galletas / snacks" in md


def test_extract_alimenta_al_parser_con_tiers_correctos():
    fichas = parse_fichas_competidores(extract_seccion_markdown(_bloques_informe()))
    por_nombre = {(f.nombre, f.tier) for f in fichas}
    # Nestlé aparece en las dos tablas globales (parciales) y Colombina en la regional.
    assert ("Nestlé S.A.", TIER_GLOBAL) in por_nombre
    assert ("Colombina S.A.", TIER_REGIONAL) in por_nombre


def test_extract_sin_seccion_devuelve_vacio():
    bloques = [DocxParagraph("3. Otro capítulo", "Heading 1"), DocxTable([["a", "b"]])]
    assert extract_seccion_markdown(bloques) == ""


# --------------------------------------------------------------------------- merge_fichas_parciales


def _norm(s: str) -> str:
    return s.strip().lower()


def test_merge_une_campos_de_fichas_parciales():
    parciales = [
        FichaCompetidor("Nestlé S.A.", TIER_GLOBAL, {"pais_origen": "Suiza", "portafolio": "Snac"}),
        FichaCompetidor("Nestlé S.A.", TIER_GLOBAL, {"mayor_fortaleza": "Distribución"}),
    ]
    fusionadas = merge_fichas_parciales(parciales, _norm)
    assert len(fusionadas) == 1
    f = fusionadas[0]
    assert f.campos == {
        "pais_origen": "Suiza",
        "portafolio": "Snac",
        "mayor_fortaleza": "Distribución",
    }
    assert f.tier == TIER_GLOBAL


def test_merge_no_pisa_valor_existente_y_preserva_orden():
    parciales = [
        FichaCompetidor("Alpha", TIER_GLOBAL, {"portafolio": "primero"}),
        FichaCompetidor("Beta", TIER_REGIONAL, {"portafolio": "b"}),
        FichaCompetidor("ALPHA", TIER_GLOBAL, {"portafolio": "segundo", "pais_origen": "US"}),
    ]
    fusionadas = merge_fichas_parciales(parciales, _norm)
    assert [f.nombre for f in fusionadas] == ["Alpha", "Beta"]  # orden de aparición, dedup homónimo
    alpha = fusionadas[0]
    assert alpha.campos["portafolio"] == "primero"  # la primera tabla gana
    assert alpha.campos["pais_origen"] == "US"  # el campo nuevo se añade


def test_merge_ignora_nombre_vacio():
    parciales = [FichaCompetidor("", TIER_GLOBAL, {"portafolio": "x"})]
    assert merge_fichas_parciales(parciales, _norm) == []
