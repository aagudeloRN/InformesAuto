"""Tests Fase 18 T18.2 — Citación APA de PDFs locales (DT-033).

Contratos:
- Chunks de PDF local → bloque de fuentes contiene autor/año, NUNCA nombre de archivo.
- Chunk de PDF sin autor → usa "Ruta N" como fallback.
- Referencia APA de PDF local no expone rutas locales (/home/...).
- format_chunks_with_meta no emite rutas locales para PDFs.
"""

import pytest

from ic.infrastructure.citation.apa_formatter import (
    CitationMetadata,
    build_references_section,
    format_chunks_with_meta,
    format_reference,
)
from ic.shared.types import ChunkResult


def _pdf_chunk(titulo, autor, año, ruta_local="/home/user/docs/Informe.pdf"):
    """Fixture: chunk de PDF local con metadatos APA."""
    return ChunkResult(
        chunk_texto="Texto de prueba del informe.",
        fuente_tipo="pdf",
        fuente_url=ruta_local,
        score=0.8,
        metadatos={
            "titulo": titulo,
            "fuente_nombre": autor,
            "año": str(año),
            "autor": autor,
            "fecha_acceso": None,
            "tipo_fuente": "informe_compilado",
        },
        chunk_id=None,
    )


def _web_chunk(url="https://example.com/articulo"):
    return ChunkResult(
        chunk_texto="Texto web.",
        fuente_tipo="web",
        fuente_url=url,
        score=0.75,
        metadatos={
            "titulo": "Artículo web",
            "fuente_nombre": "Example",
            "año": "2025",
            "autor": None,
        },
        chunk_id=None,
    )


# --- format_chunks_with_meta ---


def test_pdf_chunk_no_expone_ruta_local():
    """El bloque de fuentes de un PDF local NO debe contener la ruta absoluta."""
    chunk = _pdf_chunk("Informe Sectorial", "Ruta N", 2026)
    result = format_chunks_with_meta([chunk])
    assert "/home/" not in result
    assert ".pdf" not in result


def test_pdf_chunk_usa_autor_y_año():
    """El bloque de fuentes de un PDF local usa autor/año, no el nombre de archivo."""
    chunk = _pdf_chunk("Informe Sectorial", "McKinsey", 2025)
    result = format_chunks_with_meta([chunk])
    assert "McKinsey, 2025" in result


def test_pdf_chunk_sin_autor_usa_ruta_n():
    """Sin autor explícito, el fallback es el fuente_nombre (debería ser 'Ruta N', no filename)."""
    chunk = ChunkResult(
        chunk_texto="Texto.",
        fuente_tipo="pdf",
        fuente_url="/home/user/docs/SinAutor.pdf",
        score=0.7,
        metadatos={
            "titulo": "Documento sin autor",
            "fuente_nombre": "Ruta N",
            "año": "2026",
            "autor": None,
        },
        chunk_id=None,
    )
    result = format_chunks_with_meta([chunk])
    assert "Ruta N, 2026" in result
    assert "/home/" not in result
    assert "SinAutor.pdf" not in result


def test_web_chunk_incluye_url():
    """Las URLs públicas (http/https) sí se incluyen en el bloque de fuentes."""
    chunk = _web_chunk("https://example.com/nota")
    result = format_chunks_with_meta([chunk])
    assert "https://example.com/nota" in result


# --- _apa_report: referencias sin rutas locales ---


def test_apa_report_no_expone_ruta_local():
    """La referencia APA de un PDF local no incluye rutas /home/..."""
    meta = CitationMetadata(
        titulo="Informe sectorial: Materiales",
        fuente_nombre="Ruta N",
        año="2026",
        autor="Ruta N",
        url="/home/user/docs/PulsoMateriales.pdf",
        fecha_acceso=None,
        tipo_fuente="informe_compilado",
    )
    ref = format_reference(meta, fuente_tipo="pdf")
    assert "/home/" not in ref.apa_string
    assert ".pdf" not in ref.apa_string
    assert "Ruta N. (2026)." in ref.apa_string


def test_apa_report_url_publica_se_incluye():
    """Una URL pública (https) sí aparece en la referencia APA."""
    meta = CitationMetadata(
        titulo="Informe público",
        fuente_nombre="Organismo",
        año="2024",
        autor="Organismo",
        url="https://pub.example.org/informe.pdf",
        fecha_acceso=None,
        tipo_fuente=None,
    )
    ref = format_reference(meta, fuente_tipo="pdf")
    assert "https://pub.example.org" in ref.apa_string


def test_build_references_section_no_contiene_rutas():
    """build_references_section con chunks de PDF local no expone rutas absolutas."""
    chunks = [
        _pdf_chunk("Informe A", "Autor A", 2026, "/home/user/docs/A.pdf"),
        _pdf_chunk("Informe B", "Autor B", 2025, "/tmp/B.pdf"),
    ]
    refs = build_references_section(chunks)
    for r in refs:
        assert "/home/" not in r.apa_string
        assert "/tmp/" not in r.apa_string
        assert ".pdf" not in r.apa_string


def assert_no_filenames(texto: str) -> None:
    """Helper reutilizable para el E2E: falla si el texto contiene nombres de archivo PDF."""
    import re

    filenames = re.findall(r"\b\w[\w\s]*\.pdf\b", texto, re.IGNORECASE)
    assert not filenames, f"Nombres de archivo encontrados en el texto: {filenames}"


def test_assert_no_filenames_helper():
    assert_no_filenames("Ver (Ruta N, 2026) para más detalles.")
    with pytest.raises(AssertionError):
        assert_no_filenames("El InformeConvergencia.pdf muestra que...")


# --- T18.5 — renumber_subheadings (DT-032) ---


from ic.domain.markdown_parser import renumber_subheadings  # noqa: E402
from ic.domain.report_model import Heading, Paragraph  # noqa: E402


def test_renumber_corrige_prefijo_erroneo():
    """Heading con prefijo 5.1 en Cap 4 → reescribe a 4.1."""
    blocks = [Heading("5.1. Ecosistema Local", level=3)]
    resultado = renumber_subheadings(blocks, chapter_number=4)
    assert resultado[0].text == "4.1. Ecosistema Local"


def test_renumber_respeta_cap_correcto():
    """Si el prefijo ya es correcto, no toca el texto."""
    blocks = [Heading("4.2. Ecosistema Global", level=3)]
    resultado = renumber_subheadings(blocks, chapter_number=4)
    assert resultado[0].text == "4.2. Ecosistema Global"


def test_renumber_sin_prefijo_numerico_intacto():
    """Headings sin prefijo N.M quedan sin cambios."""
    blocks = [Heading("Ecosistema Local", level=3)]
    resultado = renumber_subheadings(blocks, chapter_number=4)
    assert resultado[0].text == "Ecosistema Local"


def test_renumber_no_toca_paragrafos():
    """Los bloques Paragraph no se modifican."""
    blocks = [Paragraph("5.1. Este es un párrafo, no heading.")]
    resultado = renumber_subheadings(blocks, chapter_number=4)
    assert resultado[0].text == "5.1. Este es un párrafo, no heading."


def test_renumber_con_punto_final():
    """Funciona con '5.1.' (punto final tras el número)."""
    blocks = [Heading("5.1. Local", level=3)]
    resultado = renumber_subheadings(blocks, chapter_number=4)
    assert resultado[0].text.startswith("4.1")


def test_renumber_mezcla_caps_y_headings():
    """Mezcla de bloques: solo los Heading numerados se tocan."""
    blocks = [
        Heading("Capítulo 4. Ecosistema Empresarial", level=2),
        Paragraph("Introducción."),
        Heading("5.1. Local", level=3),
        Heading("5.2. Global", level=3),
        Heading("Actores sin número", level=3),
    ]
    resultado = renumber_subheadings(blocks, chapter_number=4)
    textos = [b.text for b in resultado]
    assert textos[0] == "Capítulo 4. Ecosistema Empresarial"  # sin prefijo N.M → intacto
    assert textos[1] == "Introducción."
    assert textos[2] == "4.1. Local"
    assert textos[3] == "4.2. Global"
    assert textos[4] == "Actores sin número"
