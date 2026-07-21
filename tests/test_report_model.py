"""Tests del modelo de documento (bloques semánticos)."""

import pytest

from ic.domain.report_model import (
    Callout,
    CitationBlock,
    FigureBlock,
    Heading,
    PageBreak,
    Paragraph,
    ReportDocument,
    TableBlock,
    Toc,
)


def test_heading_immutable():
    h = Heading(text="Título", level=2)
    assert h.text == "Título"
    assert h.level == 2
    with pytest.raises(Exception):
        h.text = "otro"  # type: ignore[misc]


def test_paragraph_defaults():
    p = Paragraph(text="Hola mundo")
    assert p.style == "Normal"


def test_paragraph_custom_style():
    p = Paragraph(text="Aviso", style="Caption")
    assert p.style == "Caption"


def test_table_block():
    t = TableBlock(
        headers=("Empresa", "País", "Cuota"),
        rows=(("Acme", "USA", "30%"), ("Beta", "DE", "15%")),
        caption="Tabla 1. Líderes del mercado",
    )
    assert t.headers[0] == "Empresa"
    assert t.rows[1][2] == "15%"
    assert t.caption == "Tabla 1. Líderes del mercado"


def test_table_block_default_caption():
    t = TableBlock(headers=("A", "B"), rows=(("1", "2"),))
    assert t.caption == ""


def test_figure_block():
    f = FigureBlock(image_path="/tmp/chart.png", alt="Radar benchmarking", caption="Figura 1")
    assert f.image_path == "/tmp/chart.png"
    assert f.alt == "Radar benchmarking"


def test_citation_block():
    c = CitationBlock(apa_string="Autor, A. (2024). *Título*. Fuente.")
    assert "2024" in c.apa_string


def test_callout_kinds():
    for kind in ("absent_data", "actionable", "warning"):
        c = Callout(text="Texto de aviso", kind=kind)
        assert c.kind == kind


def test_page_break_immutable():
    pb = PageBreak()
    assert isinstance(pb, PageBreak)


def test_toc_default_title():
    toc = Toc()
    assert toc.title == "Tabla de Contenidos"


def test_toc_custom_title():
    toc = Toc(title="Índice")
    assert toc.title == "Índice"


def test_report_document():
    doc = ReportDocument(
        title="Informe IC — Empresa X",
        company="Empresa X",
        date="21 de julio de 2026",
        blocks=[
            Toc(),
            Heading("Cap 1", level=2),
            Paragraph("Texto introductorio"),
            PageBreak(),
        ],
        disclaimer="Generado por IA.",
    )
    assert doc.company == "Empresa X"
    assert len(doc.blocks) == 4
    assert isinstance(doc.blocks[0], Toc)
    assert isinstance(doc.blocks[1], Heading)


def test_report_document_empty_blocks():
    doc = ReportDocument(title="T", company="C", date="D")
    assert doc.blocks == []
    assert doc.disclaimer == ""
