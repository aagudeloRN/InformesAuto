"""Coherencia — T22.1 (build_caps_summary) y T22.6 (enforce_cap5_areas)."""

from ic.domain.coherence import build_caps_summary, enforce_cap5_areas


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


# ── T22.6 (DT-047): enforce_cap5_areas ─────────────────────────────────────

_CAP5 = (
    "La convergencia empresarial analiza cómo las estrategias.\n\n"
    "## 5.1 Área Estratégica: Sostenibilidad Ambiental\nContenido 5.1.\n\n"
    "## 5.2 Área Estratégica: Transformación Digital\nContenido 5.2.\n\n"
    "## 5.3 Área Estratégica: Desarrollo Social-Humano\nContenido 5.3.\n\n"
    "## 5.4 Área Estratégica: Desarrollo Económico\nContenido 5.4.\n\n"
)


def test_elimina_areas_extra():
    texto = _CAP5 + (
        "## 5.5 Área Estratégica: Innovación\nContenido inventado 5.5.\n\n"
        "## 5.6 Área Estratégica: Gobernanza\nContenido inventado 5.6.\n"
    )
    saneado, eliminados = enforce_cap5_areas(texto)
    assert len(eliminados) == 2
    assert "Contenido inventado 5.5" not in saneado
    assert "Contenido inventado 5.6" not in saneado
    # Conserva intro + las 4 áreas canónicas.
    assert "La convergencia empresarial" in saneado
    for n in range(1, 5):
        assert f"## 5.{n}" in saneado


def test_sin_areas_extra_no_cambia():
    saneado, eliminados = enforce_cap5_areas(_CAP5)
    assert eliminados == []
    assert saneado == _CAP5


def test_sin_encabezados_no_toca_nada():
    texto = "Un capítulo sin encabezados de área numerados."
    saneado, eliminados = enforce_cap5_areas(texto)
    assert eliminados == []
    assert saneado == texto


def test_devuelve_labels_eliminados():
    texto = _CAP5 + "## 5.7 Área Estratégica: Extra\nContenido.\n"
    _saneado, eliminados = enforce_cap5_areas(texto)
    assert any("5.7" in e for e in eliminados)
