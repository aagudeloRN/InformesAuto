"""T22.1 (Q1) — build_caps_summary: contexto de hallazgos de capítulos previos."""

from ic.domain.coherence import build_caps_summary


def test_une_y_etiqueta_capitulos():
    out = build_caps_summary([
        ("Cap 2 — Benchmarking", "Alpina lidera el mercado lácteo."),
        ("Cap 3 — Tendencias", "Crece la demanda de plant-based."),
    ])
    assert "## Cap 2 — Benchmarking" in out
    assert "Alpina lidera" in out
    assert "## Cap 3 — Tendencias" in out
    assert "---" in out  # separador entre capítulos


def test_ignora_textos_vacios_o_en_blanco():
    out = build_caps_summary([
        ("Cap 2", "Contenido real."),
        ("Cap 3", ""),
        ("Cap 4", "   "),
    ])
    assert "Cap 2" in out
    assert "Cap 3" not in out
    assert "Cap 4" not in out


def test_trunca_a_max_chars():
    largo = "x" * 1000
    out = build_caps_summary([("Cap 2", largo)], max_chars_per_cap=100)
    # 100 chars de contenido + etiqueta + elipsis; no debe incluir los 1000.
    assert "x" * 100 in out
    assert "x" * 200 not in out
    assert out.endswith("…")


def test_lista_vacia_devuelve_cadena_vacia():
    assert build_caps_summary([]) == ""
    assert build_caps_summary([("Cap 2", "")]) == ""
