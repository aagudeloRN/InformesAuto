"""DT-056/T2 — agregador puro del sustrato: consolidación, señal (publisher/ruido), ranking, alias.

Puro (sin BD ni modelos). Fixtures reproducen los patrones reales verificados en BD: publishers
omnipresentes (muchos sectores), fragmentos de títulos de informe, y competidores concentrados.
"""

from __future__ import annotations

from ic.domain.kb.aggregate import (
    SIGNAL_COMPETIDOR,
    SIGNAL_PUBLISHER,
    SIGNAL_RUIDO,
    MencionCruda,
    aggregate_menciones,
    rank_candidatos,
)


def _m(norm, texto, sector, chunk, doc=None):
    return MencionCruda(
        entidad_normalizada=norm,
        entidad_texto=texto,
        sector=sector,
        chunk_id=chunk,
        documento_id=doc,
    )


def test_consolida_menciones_y_cuenta_chunks_sectores():
    filas = [
        _m("alpina", "Alpina", "3020", "c1"),
        _m("alpina", "ALPINA S.A.", "3020", "c1"),  # mismo chunk → no suma chunk distinto
        _m("alpina", "Alpina", "3020", "c2"),
    ]
    (c,) = aggregate_menciones(filas)
    assert c.nombre_normalizado == "alpina"
    assert c.n_menciones == 3
    assert c.n_chunks == 2  # c1, c2
    assert c.n_sectores == 1
    assert c.sector_dominante == "3020"
    assert c.concentracion == 1.0
    assert c.signal == SIGNAL_COMPETIDOR


def test_display_es_forma_mas_frecuente_y_aliases_el_resto():
    filas = [
        _m("infiniti research", "Infiniti Research", "4020", "c1"),
        _m("infiniti research", "Infiniti Research", "4020", "c2"),
        _m("infiniti research", "Infiniti Research Limited", "4020", "c3"),
    ]
    (c,) = aggregate_menciones(filas)
    assert c.nombre == "Infiniti Research"  # más frecuente
    assert c.aliases == ["Infiniti Research Limited"]  # variante superficial conservada


def test_publisher_por_dispersion_multi_sector():
    # 'the business research company' (TBRC) en 8 sectores → publisher, no competidor.
    filas = [_m("the business research company", "TBRC", str(s), f"c{s}") for s in range(8)]
    (c,) = aggregate_menciones(filas)
    assert c.n_sectores == 8
    assert c.signal == SIGNAL_PUBLISHER


def test_publisher_umbral_configurable():
    # Nombre sin token de marca conocido: solo la dispersión decide (aísla el umbral).
    filas = [_m("acme holding", "Acme Holding", str(s), f"c{s}") for s in range(5)]
    (c,) = aggregate_menciones(filas, publisher_min_sectores=4)
    assert c.signal == SIGNAL_PUBLISHER
    # Con umbral alto, 5 sectores no alcanza → deja de ser publisher.
    (c2,) = aggregate_menciones(filas, publisher_min_sectores=9)
    assert c2.signal != SIGNAL_PUBLISHER


def test_ruido_fragmento_titulo_de_informe():
    # "colombia construction equipment market report": largo + token de título → ruido.
    filas = [
        _m("colombia construction equipment market report", "…", "2010", f"c{i}") for i in range(3)
    ]
    (c,) = aggregate_menciones(filas)
    assert c.signal == SIGNAL_RUIDO


def test_ruido_acronimo_corto():
    filas = [_m("lpg", "LPG", "1010", "c1"), _m("cop", "COP", "1010", "c2")]
    cs = {c.nombre_normalizado: c.signal for c in aggregate_menciones(filas)}
    assert cs["lpg"] == SIGNAL_RUIDO
    assert cs["cop"] == SIGNAL_RUIDO


def test_publisher_por_token_de_marca_aunque_pocos_sectores():
    # Casas de análisis concentradas en pocos sectores: la dispersión no basta, el token sí.
    filas = (
        [
            _m("euromonitor international", "Euromonitor International", "2550", f"e{i}")
            for i in range(7)
        ]
        + [
            _m("international energy agency", "International Energy Agency", "1010", f"a{i}")
            for i in range(5)
        ]
        + [_m("mapfre economics", "Mapfre Economics", "4030", "m1")]
    )
    señales = {c.nombre_normalizado: c.signal for c in aggregate_menciones(filas)}
    assert señales["euromonitor international"] == SIGNAL_PUBLISHER  # token 'euromonitor'
    assert señales["international energy agency"] == SIGNAL_PUBLISHER  # nombre completo de fuente
    assert señales["mapfre economics"] == SIGNAL_PUBLISHER  # token 'mapfre', 1 sector


def test_ruido_terminos_genericos_y_geografias():
    filas = [
        _m("latam", "LATAM", "5010", "c1"),
        _m("european union", "European Union", "1010", "c2"),
        _m("global fintech", "Global Fintech", "4020", "c3"),
        _m("credit ratings", "Credit Ratings", "3510", "c4"),
    ]
    señales = {c.nombre_normalizado: c.signal for c in aggregate_menciones(filas)}
    assert all(s == SIGNAL_RUIDO for s in señales.values())


def test_competidor_real_concentrado_no_es_ruido():
    # Nombre propio de empresa, 1 sector, sin tokens de título → competidor.
    filas = [_m("grupo nutresa", "Grupo Nutresa", "3020", f"c{i}") for i in range(4)]
    (c,) = aggregate_menciones(filas)
    assert c.signal == SIGNAL_COMPETIDOR


def test_ranking_competidores_primero_por_evidencia():
    filas = (
        [_m("grupo nutresa", "Grupo Nutresa", "3020", f"n{i}") for i in range(5)]
        + [_m("colanta", "Colanta", "3020", f"c{i}") for i in range(2)]
        + [_m("oecd", "OECD", str(s), f"o{s}") for s in range(10)]  # publisher
    )
    ranked = rank_candidatos(aggregate_menciones(filas))
    # Competidores antes que el publisher; entre competidores, mayor evidencia primero.
    assert [r.nombre_normalizado for r in ranked[:2]] == ["grupo nutresa", "colanta"]
    assert ranked[-1].nombre_normalizado == "oecd"


def test_ignora_normalizado_vacio():
    assert aggregate_menciones([_m("", "", "3020", "c1")]) == []
