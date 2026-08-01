"""Extracción de productos/servicios de la descripción de empresa (DT-063). Puro, sin modelo.

La señal que guía el descubrimiento de competidores es lo que la empresa **hace** (sus productos y
servicios), no un sub-código GICS coarso y frágil. Cap 1 (`chain_01_descripcion`) ya emite una
sección "## Productos y servicios"; aquí se aísla su texto y se tokeniza en términos de contenido
para (a) steerear el prompt de globales y (b) re-rankear locales/startups del directorio por solape
con la actividad. Determinista (RN-001: solo extrae lo presente, no fabrica).
"""

from __future__ import annotations

import re
import unicodedata

# Encabezado exacto que emite chain_01. Se tolera nivel de "#", acentos y mayúsculas.
_HEADING_RE = re.compile(
    r"^#{1,4}\s*productos\s+y\s+servicios\s*$", re.IGNORECASE | re.MULTILINE
)
_NEXT_HEADING_RE = re.compile(r"^#{1,4}\s+\S", re.MULTILINE)
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Palabras vacías/genéricas que no discriminan un producto (es neutro). No fabrican señal.
_STOPWORDS: frozenset[str] = frozenset({
    "de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "en", "con", "para", "por",
    "que", "una", "uno", "unos", "unas", "un", "al", "a", "su", "sus", "se", "es", "son",
    "como", "mas", "muy", "entre", "sobre", "tambien", "ademas", "esta", "este", "estos",
    "estas", "ser", "tiene", "tienen", "ofrece", "ofrecen", "empresa", "compania", "productos",
    "producto", "servicios", "servicio", "principales", "diversos", "varios", "gama", "linea",
    "portafolio", "incluye", "incluyen", "mercado", "clientes", "cliente", "sector", "actividad",
    "actividades", "solucion", "soluciones", "dato", "disponible", "fuentes", "consultadas",
    "inferencia", "diferentes", "amplia", "amplio", "nacional", "internacional", "calidad",
})


def _normalize(texto: str) -> str:
    """Minúsculas sin acentos (fold NFKD). Idéntico criterio que gics_groups._normalize."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def extract_productos_servicios(texto: str | None) -> str:
    """Devuelve el texto de la sección "## Productos y servicios" de la descripción, o "".

    Toma desde el encabezado hasta el siguiente encabezado "## " (o el fin). "" si no hay sección
    (→ el descubrimiento cae a nivel de grupo GICS, nunca a un sub adivinado).
    """
    if not texto:
        return ""
    m = _HEADING_RE.search(texto)
    if not m:
        return ""
    resto = texto[m.end():]
    sig = _NEXT_HEADING_RE.search(resto)
    seccion = resto[: sig.start()] if sig else resto
    return seccion.strip()


def producto_terms(seccion: str | None, min_len: int = 4) -> set[str]:
    """Tokens de contenido de la sección de productos (normalizados, sin stopwords). Puro.

    Sirve para el solape producto↔actividad del re-rank de competidores. Descarta tokens cortos
    (< ``min_len``) y stopwords/genéricos. Devuelve conjunto (orden irrelevante).
    """
    if not seccion:
        return set()
    return {
        t for t in _TOKEN_RE.findall(_normalize(seccion))
        if len(t) >= min_len and t not in _STOPWORDS
    }


def producto_overlap(descriptor: str | None, productos_terms: set[str]) -> int:
    """Nº de términos de producto presentes en el ``descriptor`` de un candidato. Puro (DT-063).

    ``descriptor`` = lo que el candidato HACE (perfil de producto del global; actividad/vertical del
    local). 0 si no hay términos o descriptor → señal de "sin solape" (cae al desempate por
    evidencia).
    """
    if not productos_terms or not descriptor:
        return 0
    return len(productos_terms & producto_terms(descriptor))
