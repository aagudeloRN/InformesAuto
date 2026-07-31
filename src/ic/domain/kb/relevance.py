"""Relevancia del anclaje de competidores (DT-061) — puro, sin BD ni modelo.

Dos responsabilidades, ambas deterministas y testeables con fixtures:

- ``es_ruido_competidor``: detecta el ruido que el NER dejó pasar y que se coló como "competidor"
  en el informe de Alpina — **medios** ("Food and Beverage Industry News") y **fragmentos de
  métrica** OCR-pegados ("ProfitMargin", "Profit perEmployee"). Complementa la stoplist de
  ``aggregate`` (publishers/geografías/títulos de informe), que no atrapaba estos casos.
- ``filter_rank_competidores``: dada la lista cruda del KB para un grupo, excluye ruido y —cuando
  la empresa analizada resolvió un **sub-código** (food/beverage/tobacco)— **restringe** a los
  pares de esa sub-actividad, dejando fuera la industria ajena (bebidas/tabaco) que compartía el
  industry group 3020. Orden: verificado → match de sub → señal.

  Dos regímenes de restricción por sub (DT-062b):
  - **Tier de clase mundial** (``alcance`` pedido, p. ej. ``global``): sub-**estricto**, sin puente
    ``verificado`` y sin fallback a grupo. Los globales se siembran ``verificado`` por sub; un
    ``verificado`` de OTRA sub (food) no debe colarse en el ancla de tabaco/bebidas. Mejor ancla
    vacía → el guard de coste dispara el descubrimiento de esa sub.
  - **Grupo/local** (sin ``alcance``): se conserva el puente ``verificado OR sub`` y el fallback a
    grupo (invariante DT-061: curados sin sub tag deben mostrarse; nunca se pierde todo el set).

RN-001: solo **excluye/ordena** lo presente; no fabrica nombres ni atributos.
"""

from __future__ import annotations

from dataclasses import dataclass

# Palabras propias de MEDIOS (no empresas del sector): un nombre con alguna de estas es un
# publisher/medio, no un competidor. Match por token exacto (no substring) para no atrapar
# empresas cuyo nombre las contenga como fragmento.
_MEDIA_TOKENS: frozenset[str] = frozenset({
    "news", "magazine", "journal", "times", "press", "gazette", "herald", "bulletin",
    "daily", "weekly", "tribune", "chronicle", "observer", "wire", "media", "newsletter",
    "insights", "insider",
})

# Palabras/fragmentos de MÉTRICAS financieras que el OCR pega como si fueran nombres de empresa
# ("ProfitMargin" → "profitmargin"; "Profit perEmployee" → "profit peremployee").
_METRIC_TOKENS: frozenset[str] = frozenset({
    "profit", "profitmargin", "margin", "peremployee", "ebitda", "ebit", "revenue",
    "turnover", "opex", "capex", "roa", "roe", "roi", "yoy",
})
# Formas pegadas (sin espacio) que no se parten en tokens.
_METRIC_GLUED: tuple[str, ...] = (
    "profitmargin", "peremployee", "grossmargin", "netmargin", "operatingmargin",
)


def es_ruido_competidor(nombre_normalizado: str) -> bool:
    """True si el nombre normalizado es un medio o un fragmento de métrica (no una empresa).

    ``nombre_normalizado`` se asume en minúsculas sin acentos (como lo produce el NER/aggregate).
    Puro y determinista (RN-001: solo clasifica, no inventa).
    """
    if not nombre_normalizado:
        return True
    tokens = set(nombre_normalizado.split())
    if tokens & _MEDIA_TOKENS or tokens & _METRIC_TOKENS:
        return True
    return any(frag in nombre_normalizado for frag in _METRIC_GLUED)


@dataclass(frozen=True)
class CompetidorRow:
    """Fila cruda del KB para rankear (la capa data la construye desde SQL; el dominio no ve BD)."""

    nombre: str
    nombre_normalizado: str
    sub_gics: str | None = None
    alcance: str | None = None
    verificado: bool = False
    n_chunks: int = 0
    n_menciones: int = 0


@dataclass(frozen=True)
class LocalRow:
    """Fila del directorio local (DT-050) para el anclaje de los tiers 2.1.2/2.1.3."""

    nombre: str
    ciudad: str | None = None
    actividad: str | None = None
    tamano: str | None = None
    segmento: str | None = None


def _linea_local(r: LocalRow) -> str:
    partes = [r.nombre]
    for extra in (r.ciudad, r.actividad, r.tamano):
        if extra:
            partes.append(extra)
    return "- " + " — ".join(partes)


def format_jugadores_locales(
    regionales: list[LocalRow], startups: list[LocalRow]
) -> str:
    """Bloque de contexto estructurado con jugadores locales del directorio (DT-050). Puro.

    Ground-truth para anclar 2.1.2 (regionales) y 2.1.3 (startups) sin depender solo de la web
    (DT-049). Devuelve "" si no hay nada (invariante: prompt idéntico cuando el flag está OFF o el
    directorio no tiene locales del sector). RN-001: solo lista lo recuperado del directorio.
    """
    bloques: list[str] = []
    if regionales:
        bloques.append(
            "Referentes regionales (Colombia) del directorio:\n"
            + "\n".join(_linea_local(r) for r in regionales)
        )
    if startups:
        bloques.append(
            "Startups regionales del directorio:\n"
            + "\n".join(_linea_local(r) for r in startups)
        )
    return "\n\n".join(bloques)


def filter_rank_competidores(
    rows: list[CompetidorRow],
    sub_gics: str | None = None,
    alcance: str | None = None,
    limit: int = 8,
) -> list[str]:
    """Excluye ruido, restringe por sub-actividad/alcance (si aplica) y ordena. Puro.

    - Siempre excluye medios/métricas (``es_ruido_competidor``).
    - Si ``alcance`` se pide (p. ej. ``global`` para la sección de clase mundial), **filtra** a ese
      alcance: solo actores marcados así entran (los locales y los sin clasificar se dejan para su
      propio componente, DT-050). Filtro duro (no fallback): la lista de clase mundial no debe
      diluirse con jugadores locales.
    - Si ``sub_gics`` se resolvió, **restringe** por sub-actividad → cae la industria ajena. El
      régimen depende de ``alcance`` (DT-062b):
      - Con ``alcance`` (tier de clase mundial): sub-**estricto** (``r.sub_gics == sub_gics``), sin
        puente ``verificado`` ni fallback a grupo. Puede quedar vacío (mejor que sub ajena: el
        guard dispara el descubrimiento de esa sub).
      - Sin ``alcance`` (grupo/local): puente ``verificado OR sub`` con fallback a grupo si no hay
        relevantes (invariante DT-061). Sin ``sub_gics`` → conserva el set, solo sin ruido.
    - Orden: ``verificado`` → match de ``sub_gics`` → evidencia (chunks, menciones).
    """
    limpios = [r for r in rows if not es_ruido_competidor(r.nombre_normalizado)]
    if alcance:
        limpios = [r for r in limpios if r.alcance == alcance]
    if sub_gics:
        if alcance:
            # Tier de clase mundial: sub-ESTRICTO (sin puente verificado, sin fallback a grupo).
            limpios = [r for r in limpios if r.sub_gics == sub_gics]
        else:
            relevantes = [r for r in limpios if r.verificado or r.sub_gics == sub_gics]
            if relevantes:
                limpios = relevantes
    ordenados = sorted(
        limpios,
        key=lambda r: (
            not r.verificado,
            not (sub_gics is not None and r.sub_gics == sub_gics),
            -(r.n_chunks or 0),
            -(r.n_menciones or 0),
        ),
    )
    return [r.nombre for r in ordenados[:limit]]
