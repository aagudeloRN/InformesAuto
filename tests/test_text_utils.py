"""Tests de utilidades de texto compartidas (ic.shared.text_utils).

Foco DT-UI04c: strip_preamble — saneo determinista del preámbulo espurio (bloques de código/JSON)
que algunos modelos anteponen al contenido real del capítulo. Función pura, sin IO.
"""

from ic.shared.text_utils import strip_preamble

INTRO = "El análisis tendencial describe las tendencias del sector empresarial."


def _primera_linea(texto: str) -> str:
    return next(ln for ln in texto.splitlines() if ln.strip())


def test_strip_preamble_poda_bloque_codigo_antes_de_heading():
    crudo = '```json\n{"x": 1}\n```\n\n## 3.1. Tendencias\n\nCuerpo.'
    out = strip_preamble(crudo)
    assert _primera_linea(out).startswith("## 3.")
    assert "```" not in out


def test_strip_preamble_poda_json_suelto_antes_de_heading():
    crudo = '{"meta": "ruido"}\n\n# Capítulo 5\n\nCuerpo.'
    out = strip_preamble(crudo)
    assert _primera_linea(out).startswith("# Capítulo 5")


def test_strip_preamble_conserva_parrafo_intro():
    # Prosa legítima (párrafo introductorio) antes del primer heading NO se poda.
    crudo = f"{INTRO}\n\n## 3.1. Tendencias\n\nCuerpo."
    assert strip_preamble(crudo) == crudo


def test_strip_preamble_desenvuelve_documento_en_cerca():
    crudo = "```markdown\n## 3.1. Tendencias\n\nCuerpo.\n```"
    out = strip_preamble(crudo)
    assert _primera_linea(out).startswith("## 3.")
    assert "```" not in out


def test_strip_preamble_sin_ruido_no_altera():
    crudo = "## 3.1. Tendencias\n\nCuerpo respirable."
    assert strip_preamble(crudo) == crudo


def test_strip_preamble_texto_vacio():
    assert strip_preamble("") == ""
