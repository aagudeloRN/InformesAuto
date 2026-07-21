"""Renderer docx: portada, TOC, paginación, estilos, cursivas APA, tablas, figuras, callouts.

Recibe un ReportDocument (domain) y produce un .docx con python-docx.
Solo este módulo importa python-docx; domain/ permanece limpio.
"""

import os
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from ic.domain.report_model import (
    Callout,
    CitationBlock,
    DocumentBlock,
    FigureBlock,
    Heading,
    PageBreak,
    Paragraph,
    ReportDocument,
    TableBlock,
    Toc,
)

_INLINE_RE = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")


class DocxRenderer:
    def __init__(self, template_path: str | None = None) -> None:
        self._template_path = template_path

    def render(self, doc: ReportDocument, output_path: str) -> str:
        if self._template_path and os.path.exists(self._template_path):
            word_doc = Document(self._template_path)
        else:
            word_doc = Document()

        _add_footer(word_doc)
        _add_cover_page(word_doc, doc.title, doc.company, doc.date)

        for block in doc.blocks:
            _dispatch(word_doc, block)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        word_doc.save(output_path)
        return output_path


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def _add_cover_page(doc: Document, title: str, company: str, date: str) -> None:
    p_title = doc.add_paragraph()
    p_title.style = "Title"
    run = p_title.add_run(title)
    run.bold = True

    p_company = doc.add_paragraph()
    p_company.style = "Heading 1"
    p_company.add_run(company)

    p_date = doc.add_paragraph()
    p_date.style = "Subtitle"
    p_date.add_run(date)

    doc.add_page_break()


# ---------------------------------------------------------------------------
# Footer with page number
# ---------------------------------------------------------------------------

def _add_footer(doc: Document) -> None:
    section = doc.sections[0]
    footer = section.footer
    para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    para.alignment = 1  # CENTER
    run = para.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    run._r.append(fld)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    run2 = para.add_run()
    run2._r.append(instr)

    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run3 = para.add_run()
    run3._r.append(fld2)


# ---------------------------------------------------------------------------
# TOC field
# ---------------------------------------------------------------------------

def _add_toc_field(doc: Document, title: str) -> None:
    doc.add_heading(title, level=1)
    para = doc.add_paragraph()
    run = para.add_run()

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    run._r.append(fld_begin)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r' TOC \o "1-3" \h \z \u '
    run2 = para.add_run()
    run2._r.append(instr)

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run3 = para.add_run()
    run3._r.append(fld_end)

    doc.add_page_break()


# ---------------------------------------------------------------------------
# Block dispatcher
# ---------------------------------------------------------------------------

def _dispatch(doc: Document, block: DocumentBlock) -> None:
    match block:
        case Heading():
            doc.add_heading(block.text, level=block.level)
        case Paragraph():
            para = doc.add_paragraph(style=block.style if block.style != "Normal" else None)
            _add_inline_text(para, block.text)
        case TableBlock():
            _render_table(doc, block)
        case FigureBlock():
            _render_figure(doc, block)
        case CitationBlock():
            _render_citation(doc, block)
        case Callout():
            _render_callout(doc, block)
        case PageBreak():
            doc.add_page_break()
        case Toc():
            _add_toc_field(doc, block.title)


# ---------------------------------------------------------------------------
# Inline text with **bold** and *italic* markers
# ---------------------------------------------------------------------------

def _add_inline_text(para, text: str) -> None:
    parts = _INLINE_RE.split(text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = para.add_run(part[1:-1])
            run.italic = True
        else:
            if part:
                para.add_run(part)


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

def _render_table(doc: Document, block: TableBlock) -> None:
    n_cols = len(block.headers)
    table = doc.add_table(rows=1, cols=n_cols)
    table.style = "Table Grid"

    header_row = table.rows[0]
    for i, header in enumerate(block.headers):
        cell = header_row.cells[i]
        cell.text = header
        cell_para = cell.paragraphs[0]
        run = cell_para.runs[0] if cell_para.runs else cell_para.add_run(header)
        run.bold = True

    for row_data in block.rows:
        row = table.add_row()
        for i, value in enumerate(row_data[:n_cols]):
            row.cells[i].text = value

    if block.caption:
        cap = doc.add_paragraph(block.caption)
        cap.style = "Caption"


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def _render_figure(doc: Document, block: FigureBlock) -> None:
    if not os.path.exists(block.image_path):
        doc.add_paragraph(f"[Figura no disponible: {block.alt}]")
        return
    try:
        doc.add_picture(block.image_path, width=Inches(5))
    except Exception:
        doc.add_paragraph(f"[Error al insertar figura: {block.alt}]")
        return

    if block.caption or block.alt:
        label = block.caption or block.alt
        cap = doc.add_paragraph(label)
        cap.style = "Caption"


# ---------------------------------------------------------------------------
# Citation (APA — sangría francesa + cursivas)
# ---------------------------------------------------------------------------

def _render_citation(doc: Document, block: CitationBlock) -> None:
    para = doc.add_paragraph()
    fmt = para.paragraph_format
    fmt.left_indent = Pt(36)
    fmt.first_line_indent = Pt(-36)
    _add_inline_text(para, block.apa_string)


# ---------------------------------------------------------------------------
# Callout (borde lateral izquierdo azul)
# ---------------------------------------------------------------------------

_CALLOUT_COLORS = {
    "absent_data": "1F4E79",   # azul oscuro
    "actionable": "375623",    # verde oscuro
    "warning": "843C0C",       # naranja oscuro
}


def _render_callout(doc: Document, block: Callout) -> None:
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Pt(18)
    _add_inline_text(para, block.text)

    color_hex = _CALLOUT_COLORS.get(block.kind, "1F4E79")
    _add_left_border(para, color_hex)


def _add_left_border(para, color_hex: str) -> None:
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "24")   # 3pt
    left.set(qn("w:space"), "4")
    left.set(qn("w:color"), color_hex)
    pBdr.append(left)
    pPr.append(pBdr)
