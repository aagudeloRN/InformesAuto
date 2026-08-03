"""Score de completitud de un capítulo (Fase 1 — caché keep-best de contenido).

Proxy barato y puro para decidir si un capítulo recién generado es **al menos tan completo** como el
que ya está en el caché (keep-best): un capítulo degradado —p. ej. el Cap 1 que salió casi vacío por
variabilidad del modelo free— puntúa por debajo del bueno → no lo reemplaza y se usa como fallback.

No es una nota de calidad fina (para eso está la rúbrica del self-review, DT-059); solo mide el
**volumen de contenido real**: secciones (headings markdown) + longitud de texto útil, descontando
líneas dominadas por frases de ausencia ("Datos no disponibles…"). Sin I/O ni dependencias externas.
Solo se comparan capítulos del MISMO tipo entre sí, así que basta con que el score sea monótono en
"cantidad de contenido útil".
"""

from __future__ import annotations

import re

# Línea sin contenido real (el LLM señala ausencia). Se descuenta del score.
_AUSENTE_LINEA = re.compile(
    r"no\s+disponible|no\s+especificad|sin\s+informaci|datos?\s+no\s+", re.IGNORECASE
)


# Usar el cacheado SOLO si el fresco está claramente degradado (no rescatar por diferencias menores
# ni preferir contenido stale; solo proteger contra rotura, p. ej. Cap 1 vacío por el modelo).
FALLBACK_RATIO = 0.6


def elegir_mejor(fresh, cached, ratio: float = FALLBACK_RATIO):
    """Decisión pura del keep-best/fallback. Devuelve ``(para_informe, para_cache)``.

    - ``para_informe``: el que debe usar el informe actual = el cacheado SOLO si el fresco está
      claramente degradado (``score_new < ratio * score_cached``); si no, el fresco.
    - ``para_cache``: el de mayor completitud (un capítulo degradado nunca pisa uno bueno).
    Sin ``cached`` → ``(fresh, fresh)``.
    """
    if cached is None:
        return fresh, fresh
    s_new, s_old = score_capitulo(fresh), score_capitulo(cached)
    para_informe = cached if (s_old > 0 and s_new < ratio * s_old) else fresh
    para_cache = cached if s_old > s_new else fresh
    return para_informe, para_cache


def score_capitulo(obj) -> int:
    """Score de completitud (≥0) de un capítulo por su contenido. Puro.

    ``0`` si no hay ``texto`` o está vacío. Combina nº de headings (secciones) y longitud del texto
    útil (líneas que no son frases de ausencia). Bonus si Cap 1 trae ``productos_servicios``.
    """
    texto = (getattr(obj, "texto", "") or "").strip()
    if not texto:
        return 0
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    utiles = [ln for ln in lineas if not _AUSENTE_LINEA.search(ln)]
    headings = sum(1 for ln in utiles if ln.startswith("#"))
    chars = sum(len(ln) for ln in utiles)
    bonus = 5 if (getattr(obj, "productos_servicios", "") or "").strip() else 0
    return headings * 20 + chars // 50 + bonus
