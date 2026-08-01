"""Wrapper de lectura de .docx (python-docx) — Dependency Agnosticism (CLAUDE.md TIER 1, regla 5).

El resto de la app (siembra del KB desde los informes manuales, DT-064) depende de este wrapper, no
de ``python-docx``. Recorre el cuerpo del documento en **orden de aparición** (párrafos y tablas
intercalados: ``iter_block_items``), que es lo que necesita el extractor de la sección 2.1 para
saber qué tabla pertenece a qué tier. Sin lógica de negocio: entrega bloques neutros
(``DocxParagraph`` / ``DocxTable``); el parseo vive en los módulos puros (``shared/ingest``).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocxParagraph:
    """Un párrafo del documento: su texto y el nombre del estilo (p. ej. ``Heading 2``)."""

    text: str
    style: str


@dataclass
class DocxTable:
    """Una tabla del documento como matriz de texto (``\\n`` intra-celda → espacio)."""

    rows: list[list[str]]


def iter_docx_blocks(path: str | Path) -> Iterator[DocxParagraph | DocxTable]:
    """Itera los bloques del cuerpo (párrafos y tablas) en orden de documento.

    Las celdas se devuelven como texto plano; las celdas fusionadas de python-docx repiten el mismo
    ``<w:tc>`` en varias posiciones lógicas de la fila → se conservan tal cual (una col por celda
    lógica), que es lo que espera la conversión a tabla markdown.
    """
    from docx import Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            par = Paragraph(child, doc)
            style = par.style.name if par.style is not None else ""
            yield DocxParagraph(text=par.text.strip(), style=style)
        elif isinstance(child, CT_Tbl):
            tabla = Table(child, doc)
            rows: list[list[str]] = []
            for row in tabla.rows:
                rows.append([cell.text.replace("\n", " ").strip() for cell in row.cells])
            yield DocxTable(rows=rows)
