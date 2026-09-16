"""Wrapper de NER de entidades (TIER 1 regla 5: acceso a spaCy solo por aquí) — DT-057/T3.

Extrae menciones de organizaciones (competidores) del texto de un chunk. El motor es pluggable por
config (``ner_engine``); hoy implementa spaCy (librería, CPU, sin VRAM). El corpus EMIS es bilingüe
(~79% inglés / ~24% español), así que se elige el modelo por idioma del chunk (detección barata,
sin dependencia extra): ``en_core_web_md`` para inglés, ``es_core_news_md`` para español. Los
nombres de modelo viven en config, nunca hardcodeados en app-code (ADR-002, espíritu).

RN-001 (anti-fabricación): el NER solo reporta entidades **presentes** en el texto; cada mención
entra como **candidato** (ver ``EntidadMencion``). La verificación/merge del KB es DT-056.

El parseo/normalización/dedup/filtrado es puro y testeable sin cargar modelos; la carga de spaCy
es lazy y por idioma.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ic.shared.config import Settings

# Solo organizaciones: PER (personas), LOC (lugares) y MISC (ruido/boilerplate en este corpus) se
# descartan — el KB de entidades ancla empresas/competidores, no personas ni lugares.
RELEVANT_LABELS: frozenset[str] = frozenset({"ORG"})

# Sufijos societarios a recortar del nombre normalizado (dedup robusto).
_LEGAL_SUFFIXES = re.compile(
    r"\b(s\.?a\.?s\.?|s\.?a\.?|s\.?a\.?s|ltda\.?|s\.?l\.?|inc\.?|corp\.?|co\.?|"
    r"llc|plc|gmbh|ag|n\.?v\.?|c\.?a\.?|e\.?u\.?)\b",
    re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")

# Boilerplate frecuente en informes EMIS/Euromonitor/MarketLine que spaCy etiqueta como ORG pero
# NO es una empresa (copyright, licencias, nombres de la casa editora como fuente, artículos).
BOILERPLATE: frozenset[str] = frozenset(
    {
        "the",
        "however",
        "source",
        "sources",
        "figure",
        "total",
        "powered",
        "licensed",
        "all rights reserved",
        "unauthorized distribution prohibited",
        "isi markets",
        "marketline",
        "emis",
        "not to be photocopied page",
        "cc by",
        "copyright",
        "profile is a",
        "industry profiles marketline this",
        "by organizations in the",
        # Acr?nimos gen?ricos / metadatos de informe que NO son empresas (no se?al).
        "utc",
        "cagr",
        "lng",
        "cps",
        "ems",
        "emdes",
        "page",
        "industry profiles",
    }
)

# Artefactos de extracción: racha de ≥3 letras sueltas espaciadas (OCR: "p a g e", "m a r") y
# años (2025) → no son nombres de empresa.
_OCR_SPACED = re.compile(r"\b\w(?:\s+\w\b){2,}")
_HAS_YEAR = re.compile(r"\b(19|20)\d{2}\b")

# Marcadores de idioma muy frecuentes para la detección barata (sin dependencia externa).
_EN_MARKERS = re.compile(
    r"\b(the|and|of|for|with|market|report|company|is|are|to)\b", re.IGNORECASE
)
_ES_MARKERS = re.compile(
    r"\b(de|la|el|los|las|del|y|en|para|con|mercado|empresa|informe|es|son)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class EntityMention:
    """Una mención candidata detectada en un chunk (forma superficial + normalizada + etiqueta)."""

    texto: str
    normalizada: str
    tipo: str


def detect_language(texto: str) -> str:
    """Idioma dominante del chunk: 'en' o 'es' (heurística por marcadores; default 'en').

    Puro y determinista. El corpus es mayormente inglés → ante empate se prefiere 'en'.
    """
    en = len(_EN_MARKERS.findall(texto))
    es = len(_ES_MARKERS.findall(texto))
    return "es" if es > en else "en"


def normalize_entity(nombre: str) -> str:
    """Clave de dedup: minúsculas, sin sufijos societarios ni puntuación, espacios colapsados.

    Puro y determinista. 'Alpina S.A.S.' y 'ALPINA sas' → 'alpina'.
    """
    s = nombre.lower().strip()
    s = _LEGAL_SUFFIXES.sub(" ", s)
    s = _NON_ALNUM.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def parse_mentions(
    spans: list[tuple[str, str]],
    relevant_labels: frozenset[str] = RELEVANT_LABELS,
    stoplist: frozenset[str] = BOILERPLATE,
    min_len: int = 3,
) -> list[EntityMention]:
    """Convierte spans NER ``(texto, etiqueta)`` en menciones candidatas dedup.

    Puro y testeable sin spaCy. RN-001: no fabrica — los spans provienen del texto del chunk.
    Filtra por etiqueta relevante (ORG), descarta boilerplate y normalizados vacíos/cortos, y
    deduplica por nombre normalizado (conserva la primera forma superficial vista).
    """
    vistos: dict[str, EntityMention] = {}
    for texto, etiqueta in spans:
        if etiqueta not in relevant_labels:
            continue
        norm = normalize_entity(texto)
        if len(norm) < min_len or norm in stoplist or norm in vistos:
            continue
        # Descarta artefactos de extracción: años y OCR con letras espaciadas (no son empresas).
        if _HAS_YEAR.search(norm) or _OCR_SPACED.search(norm):
            continue
        vistos[norm] = EntityMention(texto=texto.strip(), normalizada=norm, tipo=etiqueta)
    return list(vistos.values())


class EntityRecognizer:
    """Reconocedor de entidades bilingüe con motor pluggable por config. Carga de modelos lazy."""

    def __init__(self, settings: Settings, nlp_en=None, nlp_es=None) -> None:  # noqa: ANN001
        self._settings = settings
        self._engine = getattr(settings, "ner_engine", "spacy")
        self._nlp = {"en": nlp_en, "es": nlp_es}  # inyectables en tests; lazy si None

    def _ensure_nlp(self, lang: str):
        if self._nlp.get(lang) is not None:
            return self._nlp[lang]
        if self._engine != "spacy":
            raise ValueError(f"Motor NER no soportado: {self._engine!r}")
        import spacy

        modelo = (
            self._settings.ner_spacy_model_es if lang == "es" else self._settings.ner_spacy_model_en
        )
        # Solo el componente NER: sin tagger/parser/lemmatizer → más rápido sobre miles de chunks.
        self._nlp[lang] = spacy.load(
            modelo, disable=["tagger", "parser", "lemmatizer", "attribute_ruler"]
        )
        return self._nlp[lang]

    def extract(self, texto: str) -> list[EntityMention]:
        """Devuelve las menciones candidatas del texto (vacío si el texto es vacío)."""
        if not texto or not texto.strip():
            return []
        lang = detect_language(texto)
        nlp = self._ensure_nlp(lang)
        doc = nlp(texto)
        spans = [(ent.text, ent.label_) for ent in doc.ents]
        return parse_mentions(spans)
