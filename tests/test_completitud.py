"""Fase 1 (caché keep-best) — score de completitud de capítulos. Puro (sin BD)."""

from __future__ import annotations

from ic.domain.kb.completitud import elegir_mejor, score_capitulo
from ic.shared.types import CapTendencias, DescripcionEmpresa

_CAP1_COMPLETO = """## Descripción general
Alpina es una multinacional láctea colombiana fundada en 1945, con ~7.000 empleados.

## Productos y servicios
Leches, yogures, quesos, arequipe y bebidas funcionales.

## Modelo de negocio
Producción e industrialización de lácteos; venta masiva y B2B.

## Cobertura geográfica
Colombia, Ecuador, Venezuela y EE. UU.
"""

_CAP1_DEGRADADO = """## Clasificación GICS
Alimentos, bebidas y tabaco (GICS 3020).
"""


def test_score_vacio_es_cero():
    assert score_capitulo(DescripcionEmpresa("Alpina", "1040", "")) == 0
    assert score_capitulo(DescripcionEmpresa("Alpina", "1040", "   \n  ")) == 0


def test_capitulo_completo_puntua_mas_que_degradado():
    completo = DescripcionEmpresa("Alpina", "1040", _CAP1_COMPLETO)
    degradado = DescripcionEmpresa("Alpina", "1040", _CAP1_DEGRADADO)
    assert score_capitulo(completo) > score_capitulo(degradado)


def test_frases_de_ausencia_no_inflan_el_score():
    con_datos = CapTendencias(
        texto="## Tendencias\nCrecimiento del 27% en RTD saludable.",
        n_chunks_usados=1, retrieval_suficiente=True,
    )
    sin_datos = CapTendencias(
        texto="## Tendencias\nDatos no disponibles en las fuentes consultadas.",
        n_chunks_usados=0, retrieval_suficiente=False,
    )
    assert score_capitulo(con_datos) > score_capitulo(sin_datos)


def test_bonus_por_productos_servicios():
    base = DescripcionEmpresa("X", None, "## Descripción\nTexto base de la empresa.")
    con_prod = DescripcionEmpresa(
        "X", None, "## Descripción\nTexto base de la empresa.",
        productos_servicios="Lácteos, yogures",
    )
    assert score_capitulo(con_prod) > score_capitulo(base)


# ----------------------------------------------------------------------- elegir_mejor (keep-best)


def test_elegir_sin_cache_usa_el_fresco():
    fresh = DescripcionEmpresa("Alpina", "1040", _CAP1_COMPLETO)
    para_informe, para_cache = elegir_mejor(fresh, None)
    assert para_informe is fresh and para_cache is fresh


def test_fresco_degradado_cae_al_cacheado_bueno():
    # El caso real: el modelo degradó el Cap 1 (queda casi vacío) y hay uno bueno cacheado.
    cached = DescripcionEmpresa("Alpina", "1040", _CAP1_COMPLETO)
    fresh = DescripcionEmpresa("Alpina", "1040", _CAP1_DEGRADADO)
    para_informe, para_cache = elegir_mejor(fresh, cached)
    assert para_informe is cached  # fallback anti-regresión
    assert para_cache is cached  # keep-best: el bueno no se pisa


def test_fresco_bueno_no_cae_al_cacheado():
    # Fresco al menos tan completo → se usa y se cachea el fresco (no preferir stale).
    cached = DescripcionEmpresa("Alpina", "1040", _CAP1_DEGRADADO)
    fresh = DescripcionEmpresa("Alpina", "1040", _CAP1_COMPLETO)
    para_informe, para_cache = elegir_mejor(fresh, cached)
    assert para_informe is fresh
    assert para_cache is fresh
