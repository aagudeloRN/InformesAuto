"""T16.1-E: tests de extracción del bloque radar_json del texto del LLM."""

from __future__ import annotations

import json

from ic.domain.use_cases.generate_benchmarking import _extract_radar

_VALID_JSON = {
    "dimensions": ["Innovación", "Inversión", "Presencia global", "Sostenibilidad", "Digital"],
    "competidores": {
        "Nestlé": [4.5, 4.0, 5.0, 3.5, 4.0],
        "Unilever": [3.5, 4.5, 4.5, 3.0, 3.5],
    },
}

_TEXT_WITH_RADAR = (
    "## 2.1. Jugadores Clave\n\nTexto del análisis.\n\n"
    "```radar_json\n"
    + json.dumps(_VALID_JSON, ensure_ascii=False)
    + "\n```"
)


def test_extract_radar_valid():
    """Texto con bloque JSON válido → radar_data correcto y texto limpio."""
    texto_limpio, data = _extract_radar(_TEXT_WITH_RADAR)

    assert data is not None
    assert data["dimensions"] == _VALID_JSON["dimensions"]
    assert "Nestlé" in data["competidores"]
    assert len(data["competidores"]["Nestlé"]) == 5
    assert "```radar_json" not in texto_limpio
    assert "Jugadores Clave" in texto_limpio


def test_extract_radar_invalid_json():
    """Bloque malformado → radar_data=None, texto sin el bloque."""
    texto = "Capítulo 2.\n\n```radar_json\n{malo json aquí\n```"
    texto_limpio, data = _extract_radar(texto)

    assert data is None
    assert "```radar_json" not in texto_limpio
    assert "Capítulo 2." in texto_limpio


def test_extract_radar_absent():
    """Sin bloque radar_json → devuelve texto intacto y None."""
    texto = "## 2.1. Jugadores Clave\n\nTexto sin bloque radar."
    texto_limpio, data = _extract_radar(texto)

    assert data is None
    assert texto_limpio == texto


def test_extract_radar_strips_trailing_whitespace():
    """El texto limpio no tiene espacios/saltos sobrantes al final."""
    texto_limpio, _ = _extract_radar(_TEXT_WITH_RADAR)
    assert texto_limpio == texto_limpio.rstrip()


def test_extract_radar_missing_competidores_key():
    """JSON parseable pero sin clave 'competidores' → data existe, pipeline hará fallback."""
    json_sin_comp = json.dumps({"dimensions": ["A", "B"]})
    texto = f"Texto.\n\n```radar_json\n{json_sin_comp}\n```"
    _, data = _extract_radar(texto)
    assert data is not None
    assert "competidores" not in data
