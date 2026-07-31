"""DT-062 T1 — parser puro de la cadena de descubrimiento de globales.

Espejo de ``TestParseEntidades``: RN-001 (solo depura, no fabrica), dedup casefold, cota
``MAX_GLOBALES``. Sin BD ni modelo real.
"""

from __future__ import annotations

from ic.domain.chains.chain_02c_pares_globales import MAX_GLOBALES, parse_pares_globales


class TestParsePares:
    def test_array_plano(self):
        assert parse_pares_globales('["Nestlé", "Danone"]') == ["Nestlé", "Danone"]

    def test_fenced_json(self):
        raw = 'Aquí están los globales:\n```json\n["Yili", "Fonterra"]\n```\n'
        assert parse_pares_globales(raw) == ["Yili", "Fonterra"]

    def test_dedupe_case_insensitive_conserva_primera(self):
        assert parse_pares_globales('["Nestlé", "NESTLÉ", "nestlé", "Danone"]') == [
            "Nestlé",
            "Danone",
        ]

    def test_descarta_vacios_y_no_strings(self):
        assert parse_pares_globales('["Nestlé", "", "  ", 42, null, "Danone"]') == [
            "Nestlé",
            "Danone",
        ]

    def test_cap_a_max_globales(self):
        muchas = [f"G{i}" for i in range(30)]
        raw = "[" + ", ".join(f'"{n}"' for n in muchas) + "]"
        assert len(parse_pares_globales(raw)) == MAX_GLOBALES

    def test_sin_array_devuelve_vacio(self):
        # RN-001: no fabrica nada si no hay un array parseable en el texto.
        assert parse_pares_globales("El sector tiene líderes globales pero no listo nombres.") == []

    def test_vacio_o_none(self):
        assert parse_pares_globales("") == []
        assert parse_pares_globales("[]") == []
