"""Agregador puro del sustrato `entidad_menciones` → entidades candidatas (DT-056/T2).

Consolida las menciones crudas del NER (ruidosas: publishers omnipresentes + fragmentos de títulos
de informe + competidores reales) en entidades candidatas con una **señal** que las clasifica:

- ``competidor``: entidad sector-específica de alta evidencia → entra al KB como candidato.
- ``publisher``: aparece en muchos sectores (IEA/BMI/Fitch/OECD/World Bank/TBRC/DANE) → NO es
  competidor, es fuente/editor omnipresente. No entra al KB.
- ``ruido``: fragmento de título/metadato de informe o acrónimo → no es empresa. No entra al KB.

Puro y testeable sin BD ni modelos. RN-001: **solo consolida lo presente** en el sustrato; no
fabrica nombres, atributos ni fusiones sin evidencia. La dedup es por `entidad_normalizada` (el
NER ya normalizó); las formas superficiales distintas se conservan como `aliases`. La
reconciliación por NIT/ciudad con la base DT-050 es un gancho futuro (el sustrato es ORG-only).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from ic.domain.kb.relevance import es_ruido_competidor

# Umbral de dispersión: aparecer en ≥ este nº de sectores es señal de publisher/fuente, no de
# competidor. Verificado en BD: TBRC(19)/OECD(16)/IMF(17)/DANE(20)/Deloitte(16) vs competidores
# reales concentrados en 1 sector. Configurable desde el script si hiciera falta afinar.
PUBLISHER_MIN_SECTORES = 8

# Señales.
SIGNAL_COMPETIDOR = "competidor"
SIGNAL_PUBLISHER = "publisher"
SIGNAL_RUIDO = "ruido"

# Tokens propios de TÍTULOS/METADATOS de informe (no de nombres de empresa). Un normalizado que
# contiene alguno y es "largo" (varias palabras) es casi seguro un fragmento de título de reporte
# ("colombia construction equipment market report", "latin america transportation sector report").
_REPORT_TOKENS: frozenset[str] = frozenset({
    "report", "market", "outlook", "database", "comparisons", "comparison", "forecast",
    "statistics", "overview", "analysis", "review", "series", "table", "data table",
    "industry profile", "country", "quarterly", "annual",
})
# Palabras funcionales que no cuentan para la longitud "de nombre propio".
_MIN_PALABRAS_TITULO = 4

# Acrónimos/metadatos cortos que colan como ORG pero no son empresas (unidades, siglas genéricas).
_ACRONIMO_RE = re.compile(r"^[a-z]{2,4}$")

# Curación de FUENTES/EDITORES (no competidores): casas de análisis, proveedores de datos y
# organismos multilaterales que el corpus EMIS cita como fuente. La dispersión cross-sector no los
# atrapa cuando se concentran en pocos sectores (IEA↔energía, Euromonitor↔consumo). Se identifican
# por un TOKEN de marca distintivo (raro en nombres de competidor real). Consistente con el prompt
# de chain_02b, que ya instruye "no incluyas fuentes (Euromonitor, DANE)". Curación, no invención.
_PUBLISHER_TOKENS: frozenset[str] = frozenset({
    "fitch", "euromonitor", "marketline", "globaldata", "mordor", "statista", "cepal",
    "oecd", "imf", "unctad", "deloitte", "pwc", "kpmg", "mckinsey", "gartner", "nielsen",
    "bloomberg", "reuters", "moody", "standard", "poors", "spglobal", "mapfre", "infiniti",
    "tbrc", "bmi", "cfa", "eiu", "ihs", "frost", "sullivan", "grandview", "technavio",
    "comtrade", "dane", "worldbank", "bancolombia", "supersociedades", "supersalud",
    "fedesarrollo", "anif", "asobancaria",
})

# Fuentes multi-palabra sin token de marca distintivo (organismos/multilaterales): se descartan por
# nombre normalizado completo.
_PUBLISHER_NAMES: frozenset[str] = frozenset({
    "international energy agency", "international monetary fund", "world bank",
    "the business research company", "united nations", "world trade organization",
    "inter american development bank", "world economic forum", "european commission",
    "us energy information administration", "energy information administration",
    "un comtrade database", "world energy outlook", "world energy investment",
})

# Términos genéricos que NO son entidades: geografías/regiones, bloques y sustantivos de sector que
# spaCy etiqueta ORG. Se descartan por nombre normalizado completo (conservador para no borrar
# empresas cuyo nombre contenga uno de estos como parte).
_GENERIC_NOISE: frozenset[str] = frozenset({
    "latam", "latin america", "european union", "non oecd", "oecd", "energia", "energy",
    "fintech", "global fintech", "credit ratings", "mer", "i l", "cti", "sic", "llms",
    "convergencia", "usd", "cop", "eur", "gdp", "pib", "cagr", "middle east", "asia pacific",
    "north america", "south america", "sub saharan africa", "eurozone", "brics",
})


@dataclass
class EntidadCandidata:
    """Entidad consolidada desde el sustrato, con su señal y procedencia agregada."""

    nombre_normalizado: str
    nombre: str  # forma superficial más frecuente (display)
    aliases: list[str] = field(default_factory=list)
    n_menciones: int = 0
    n_chunks: int = 0
    n_sectores: int = 0
    sector_dominante: str | None = None
    concentracion: float = 0.0  # fracción de chunks en el sector dominante (0..1)
    signal: str = SIGNAL_COMPETIDOR


@dataclass(frozen=True)
class MencionCruda:
    """Fila del sustrato a agregar (subset de `entidad_menciones`)."""

    entidad_normalizada: str
    entidad_texto: str
    sector: str | None
    chunk_id: str
    documento_id: str | None = None


def _clasificar_signal(
    nombre_normalizado: str, n_sectores: int, umbral: int = PUBLISHER_MIN_SECTORES
) -> str:
    """Señal de una entidad ya agregada. Puro y determinista (RN-001: no inventa)."""
    palabras = nombre_normalizado.split()
    # Fuente/editor conocido (token de marca distintivo o nombre completo) → publisher.
    if nombre_normalizado in _PUBLISHER_NAMES or any(p in _PUBLISHER_TOKENS for p in palabras):
        return SIGNAL_PUBLISHER
    # Omnipresente cross-sector → publisher.
    if n_sectores >= umbral:
        return SIGNAL_PUBLISHER
    # Medio o fragmento de métrica OCR (DT-061): "… Industry News", "ProfitMargin" → ruido.
    if es_ruido_competidor(nombre_normalizado):
        return SIGNAL_RUIDO
    # Término genérico / geografía (nombre completo) o acrónimo corto → ruido.
    if nombre_normalizado in _GENERIC_NOISE or _ACRONIMO_RE.match(nombre_normalizado):
        return SIGNAL_RUIDO
    # Fragmento de título/metadato de informe (largo + token de reporte) → ruido.
    if len(palabras) >= _MIN_PALABRAS_TITULO and any(
        tok in nombre_normalizado for tok in _REPORT_TOKENS
    ):
        return SIGNAL_RUIDO
    return SIGNAL_COMPETIDOR


def aggregate_menciones(
    filas: list[MencionCruda],
    publisher_min_sectores: int = PUBLISHER_MIN_SECTORES,
) -> list[EntidadCandidata]:
    """Consolida menciones crudas en entidades candidatas con señal. Puro.

    Agrupa por `entidad_normalizada`; cuenta menciones, chunks distintos y sectores distintos;
    elige el sector dominante (más chunks) y la forma superficial más frecuente como display.
    `publisher_min_sectores` permite afinar el umbral sin tocar el código.
    """
    # Acumuladores por entidad normalizada.
    chunks: dict[str, set[str]] = {}
    menciones: Counter[str] = Counter()
    formas: dict[str, Counter[str]] = {}
    # Chunks DISTINTOS por sector (no menciones): la concentración se mide en chunks.
    chunks_por_sector: dict[str, dict[str, set[str]]] = {}

    for f in filas:
        k = f.entidad_normalizada
        if not k:
            continue
        menciones[k] += 1
        chunks.setdefault(k, set()).add(f.chunk_id)
        formas.setdefault(k, Counter())[f.entidad_texto] += 1
        if f.sector:
            chunks_por_sector.setdefault(k, {}).setdefault(f.sector, set()).add(f.chunk_id)

    out: list[EntidadCandidata] = []
    for k in menciones:
        n_chunks = len(chunks.get(k, ()))
        cps = chunks_por_sector.get(k, {})
        n_sectores = len(cps)
        # Sector dominante = el de más chunks distintos.
        sector_dominante, chunks_dom = (None, 0)
        for sec, cset in cps.items():
            if len(cset) > chunks_dom:
                sector_dominante, chunks_dom = sec, len(cset)
        concentracion = (chunks_dom / n_chunks) if n_chunks else 0.0
        # Forma display = superficie más frecuente; aliases = el resto de superficies vistas.
        forma_counter = formas.get(k, Counter())
        display = forma_counter.most_common(1)[0][0] if forma_counter else k
        aliases = sorted(s for s in forma_counter if s != display)

        signal = _clasificar_signal(
            k, n_sectores if n_sectores else 1, publisher_min_sectores
        )

        out.append(EntidadCandidata(
            nombre_normalizado=k,
            nombre=display,
            aliases=aliases,
            n_menciones=menciones[k],
            n_chunks=n_chunks,
            n_sectores=n_sectores,
            sector_dominante=sector_dominante,
            concentracion=round(concentracion, 4),
            signal=signal,
        ))
    return out


def rank_candidatos(candidatas: list[EntidadCandidata]) -> list[EntidadCandidata]:
    """Ordena competidores primero, luego por evidencia (chunks) y concentración sectorial.

    No filtra: solo ordena. El merge decide qué señales persiste (competidor) y cuáles descarta.
    """
    return sorted(
        candidatas,
        key=lambda c: (c.signal != SIGNAL_COMPETIDOR, -c.n_chunks, -c.concentracion),
    )
