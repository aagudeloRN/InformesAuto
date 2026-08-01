"""Extractor puro de la sección 2.1 (Jugadores Clave) de los informes manuales → markdown.

Convierte los bloques neutros de un ``.docx`` (``DocxParagraph`` / ``DocxTable``, entregados por el
wrapper ``infrastructure/sources/docx_reader``) en el **mismo markdown** que emite ``chain_03`` para
2.1, de modo que ``parse_fichas_competidores`` lo parsee sin cambios. Puro: sin I/O ni docx.

Clave estructural (verdad de terreno, los 5 informes): cada *tier* se marca con un párrafo de texto
(``Referentes Globales`` / ``Mayor Fortaleza - Referentes Regionales`` / ``Startups / FoodTech`` …),
**no** con un Heading de Word, y va inmediatamente seguido de su tabla ancha. El parser fija el tier
por ``Heading`` → aquí esos párrafos-marcador se emiten como ``### …``. Se detectan reutilizando
``_tier_de_heading`` (DRY): un párrafo cuyo tier resuelve a algo es un marcador. Los párrafos de
narrativa/citas que casualmente casen son inocuos: el marcador genuino que precede a cada tabla
restablece el tier correcto antes de ella.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ic.domain.kb.ficha_parser import _tier_de_heading
from ic.infrastructure.sources.docx_reader import DocxParagraph, DocxTable

# La sección arranca en "2.1 …" y termina en la siguiente subsección de nivel 2 (2.2–2.9) o cap 3.
_START_RE = re.compile(r"^2\.1(\D|$)")
_STOP_RE = re.compile(r"^(2\.[2-9]|3\.)")


def _celda(texto: str) -> str:
    """Sanea una celda para tabla markdown: `|` y saltos → espacio, sin romper el split por `|`."""
    return re.sub(r"\s+", " ", texto.replace("|", "/").replace("\n", " ")).strip()


def _tabla_markdown(rows: list[list[str]]) -> str:
    """Renderiza una matriz de texto como tabla markdown pipe (cabecera + separador + filas)."""
    filas = [r for r in rows if any(c.strip() for c in r)]
    if not filas:
        return ""
    ncol = len(filas[0])
    out = ["| " + " | ".join(_celda(c) for c in filas[0]) + " |"]
    out.append("| " + " | ".join(["---"] * ncol) + " |")
    for r in filas[1:]:
        out.append("| " + " | ".join(_celda(c) for c in r) + " |")
    return "\n".join(out)


def extract_seccion_markdown(blocks: Iterable[DocxParagraph | DocxTable]) -> str:
    """Extrae la sección 2.1 como markdown (headings de tier + tablas). Puro.

    Recorre los bloques en orden de documento; entra al ver el heading ``2.1 …`` y corta en la
    siguiente subsección. Emite ``### <texto>`` para los párrafos-marcador de tier y convierte cada
    tabla a markdown. Devuelve ``""`` si no encuentra la sección.
    """
    lineas: list[str] = []
    inside = False
    for blk in blocks:
        if isinstance(blk, DocxParagraph):
            t = blk.text.strip()
            if not t:
                continue
            if not inside:
                if _START_RE.match(t):
                    inside = True
                continue
            if _STOP_RE.match(t):
                break
            if _tier_de_heading(t) is not None:
                lineas.append(f"### {t}")
                lineas.append("")
        elif isinstance(blk, DocxTable):
            if not inside:
                continue
            tabla = _tabla_markdown(blk.rows)
            if tabla:
                lineas.append(tabla)
                lineas.append("")
    return "\n".join(lineas).strip()
