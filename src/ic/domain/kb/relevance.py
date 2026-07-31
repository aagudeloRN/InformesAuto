"""Relevancia del anclaje de competidores (DT-061) — puro, sin BD ni modelo.

Dos responsabilidades, ambas deterministas y testeables con fixtures:

- ``es_ruido_competidor``: detecta el ruido que el NER dejó pasar y que se coló como "competidor"
  en el informe de Alpina — **medios** ("Food and Beverage Industry News") y **fragmentos de
  métrica** OCR-pegados ("ProfitMargin", "Profit perEmployee"). Complementa la stoplist de
  ``aggregate`` (publishers/geografías/títulos de informe), que no atrapaba estos casos.
- ``filter_rank_competidores``: dada la lista cruda del KB para un grupo, excluye ruido y —cuando
  la empresa analizada resolvió un **sub-código** (food/beverage/tobacco)— **restringe** a los
  pares de esa sub-actividad o ``verificado`` (curados), dejando fuera la industria ajena
  (bebidas/tabaco) que compartía el industry group 3020. Orden: verificado → match de sub → señal.

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
    verificado: bool = False
    n_chunks: int = 0
    n_menciones: int = 0


def filter_rank_competidores(
    rows: list[CompetidorRow], sub_gics: str | None = None, limit: int = 8
) -> list[str]:
    """Excluye ruido, restringe por sub-actividad (si aplica) y ordena por relevancia. Puro.

    - Siempre excluye medios/métricas (``es_ruido_competidor``).
    - Si ``sub_gics`` se resolvió y existen pares relevantes (``verificado`` o del mismo
      ``sub_gics``), **restringe** a ellos → cae la industria ajena (candidatos NER del grupo con
      ``sub_gics`` desconocido). Sin ``sub_gics`` o sin relevantes → conserva el set del grupo
      (invariante), solo con el ruido excluido.
    - Orden: ``verificado`` primero → match de ``sub_gics`` → evidencia (chunks, menciones).
    """
    limpios = [r for r in rows if not es_ruido_competidor(r.nombre_normalizado)]
    if sub_gics:
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
