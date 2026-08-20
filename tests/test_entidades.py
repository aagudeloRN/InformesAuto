"""T1b (DT-054, T22.4) — Identificación de entidades competidoras + búsqueda dirigida.

Cubre el parser puro `parse_entidades` (RN-001: solo depura, no fabrica) y el paso de búsqueda
dirigida por entidad en `GenerateBenchmarking` (mocks, sin Ollama/Tavily reales).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ic.domain.chains.chain_02b_entidades import MAX_ENTIDADES, parse_entidades
from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
from ic.shared.types import ChunkResult, WebResult


class TestParseEntidades:
    def test_array_plano(self):
        assert parse_entidades('["Alpina", "Colanta"]') == ["Alpina", "Colanta"]

    def test_fenced_json(self):
        raw = 'Aquí están:\n```json\n["Nestlé", "Alquería"]\n```\n'
        assert parse_entidades(raw) == ["Nestlé", "Alquería"]

    def test_dedupe_case_insensitive_conserva_primera(self):
        assert parse_entidades('["Alpina", "ALPINA", "alpina", "Colanta"]') == [
            "Alpina",
            "Colanta",
        ]

    def test_descarta_vacios_y_no_strings(self):
        assert parse_entidades('["Alpina", "", "  ", 42, null, "Colanta"]') == [
            "Alpina",
            "Colanta",
        ]

    def test_cap_a_max_entidades(self):
        muchas = [f"E{i}" for i in range(20)]
        raw = "[" + ", ".join(f'"{n}"' for n in muchas) + "]"
        assert len(parse_entidades(raw)) == MAX_ENTIDADES

    def test_sin_array_devuelve_vacio(self):
        # RN-001: no fabrica nada si no hay un array parseable en el texto.
        assert parse_entidades("El sector es competitivo pero no listo nombres.") == []

    def test_vacio_o_none(self):
        assert parse_entidades("") == []
        assert parse_entidades("[]") == []


def _chunk(texto: str, url: str = "https://e.com/1") -> ChunkResult:
    return ChunkResult(
        chunk_texto=texto, fuente_tipo="pdf", fuente_url=url, score=0.9,
        metadatos={"titulo": "Doc", "año": "2025", "autor": "Autor", "sector_gics": "3020"},
    )


def _web(url: str = "https://e.com/perfil") -> WebResult:
    return WebResult(
        url=url, title="Perfil", content="contenido del perfil de la empresa",
        snippet="perfil", metadatos={"titulo": "Perfil", "año": "2025", "autor": None},
    )


def _store_con_chunks(n: int) -> MagicMock:
    store = MagicMock()
    store.search.return_value = [_chunk(f"competidores {i}") for i in range(n)]
    store.ingest.return_value = n
    return store


class TestBusquedaDirigida:
    def test_con_entidades_lanza_una_busqueda_por_entidad(self):
        store = _store_con_chunks(6)
        web = MagicMock()
        web.search.return_value = [_web()]
        entidades_chain = MagicMock()
        entidades_chain.invoke.return_value = '["Colanta", "Alquería"]'
        chain = MagicMock()
        chain.invoke.return_value = "## 2.1. Jugadores Clave\ntexto"

        GenerateBenchmarking(
            chain=chain, store=store, web_connector=web, entidades_chain=entidades_chain,
        ).execute(
            nombre_empresa="Alpina", descripcion_empresa="láctea",
            sector_gics="Alimentos", sector_gics_code="3020",
        )

        # Las 3 queries de sector iniciales + 1 dirigida por cada entidad identificada.
        dirigidas = [
            c for c in web.search.call_args_list
            if "perfil empresa portafolio" in c.args[0]
        ]
        assert len(dirigidas) == 2
        assert any("Colanta" in c.args[0] for c in dirigidas)
        assert any("Alquería" in c.args[0] for c in dirigidas)
        # Re-retrieval tras enriquecer: search se llamó dos veces (inicial + final).
        assert store.search.call_count == 2

    def test_sin_entidades_chain_no_hay_busqueda_dirigida(self):
        store = _store_con_chunks(6)
        web = MagicMock()
        web.search.return_value = [_web()]
        chain = MagicMock()
        chain.invoke.return_value = "texto"

        GenerateBenchmarking(
            chain=chain, store=store, web_connector=web,  # entidades_chain=None
        ).execute(
            nombre_empresa="Alpina", descripcion_empresa="láctea",
            sector_gics="Alimentos", sector_gics_code="3020",
        )

        dirigidas = [
            c for c in web.search.call_args_list
            if "perfil empresa portafolio" in c.args[0]
        ]
        assert dirigidas == []
        assert store.search.call_count == 1  # sin re-retrieval

    def test_entidades_vacias_no_reretrieval(self):
        store = _store_con_chunks(6)
        web = MagicMock()
        web.search.return_value = [_web()]
        entidades_chain = MagicMock()
        entidades_chain.invoke.return_value = "[]"  # el modelo no ancló nombres
        chain = MagicMock()
        chain.invoke.return_value = "texto"

        GenerateBenchmarking(
            chain=chain, store=store, web_connector=web, entidades_chain=entidades_chain,
        ).execute(
            nombre_empresa="Alpina", descripcion_empresa="láctea",
            sector_gics="Alimentos", sector_gics_code="3020",
        )

        assert store.search.call_count == 1  # sin entidades → sin re-retrieval


class TestAnclajeKB:
    """DT-056/T3 — la lista canónica del KB ancla la búsqueda dirigida (cierra causas A/E)."""

    def _run(self, kb_competidores, llm_json='["Colanta"]'):
        store = _store_con_chunks(6)
        web = MagicMock()
        web.search.return_value = [_web()]
        entidades_chain = MagicMock()
        entidades_chain.invoke.return_value = llm_json
        chain = MagicMock()
        chain.invoke.return_value = "texto"
        GenerateBenchmarking(
            chain=chain, store=store, web_connector=web, entidades_chain=entidades_chain,
            kb_competidores=kb_competidores,
        ).execute(
            nombre_empresa="Alpina", descripcion_empresa="láctea",
            sector_gics="Alimentos", sector_gics_code="3020",
        )
        return [
            c.args[0] for c in web.search.call_args_list
            if "perfil empresa portafolio" in c.args[0]
        ]

    def test_kb_competidores_lideran_la_busqueda_dirigida(self):
        dirigidas = self._run(["Nestlé", "Danone"])
        # KB primero, luego lo que el LLM ancló en evidencia (sin duplicar).
        assert any("Nestlé" in q for q in dirigidas)
        assert any("Danone" in q for q in dirigidas)
        assert any("Colanta" in q for q in dirigidas)
        assert len(dirigidas) == 3

    def test_kb_none_es_comportamiento_b1_identico(self):
        # None → solo lo que el LLM ancla; ninguna entidad del KB filtrada.
        dirigidas = self._run(None)
        assert len(dirigidas) == 1
        assert any("Colanta" in q for q in dirigidas)

    def test_kb_dedup_casefold_y_cap(self):
        # KB con duplicado del LLM (case-insensitive) + cota MAX_ENTIDADES.
        kb = [f"E{i}" for i in range(10)]  # excede la cota
        dirigidas = self._run(kb, llm_json='["e0", "Colanta"]')  # "e0" duplica "E0" del KB
        assert len(dirigidas) == MAX_ENTIDADES  # cota respetada
        # No aparece "Colanta" porque el KB ya llenó la cota (lidera); sin duplicar "e0"/"E0".
        assert sum("E0 " in q or q.startswith("E0 ") for q in dirigidas) == 1


class TestLocalRowVentasOrdering:
    """T031/T038: ventas_2025_cop ordena primero; n_menciones es desempate (via _list_locales)."""

    def test_ventas_cop_ordena_primero(self):
        """list_locales_by_sector pone primero la entidad con ventas sobre la grande sin ventas."""
        from ic.data.repositories._entidad_queries import list_locales_by_sector
        # r: nombre, ciudad, vertical, ing_valor, segmento, verificado, tam, desc, prod, ventas, menciones
        row_con_ventas  = ("PequenaConVentas", None, None, None, None, False, 100, None, None, 1_000_000.0, 0)
        row_sin_ventas  = ("GrandeSinVentas",  None, None, None, None, False, 99_999_999, None, None, None, 0)

        class _FakeDB:
            def execute(self, *a, **kw):
                return self
            def fetchall(self):
                return [row_sin_ventas, row_con_ventas]

        result = list_locales_by_sector(_FakeDB(), ["3020"], limit=10)
        assert result[0].nombre == "PequenaConVentas"

    def test_ventas_cop_none_fallback_a_menciones(self):
        """Cuando ventas=None en todas, n_menciones decide el orden en list_locales_by_sector."""
        from ic.data.repositories._entidad_queries import list_locales_by_sector
        row_mas_menciones   = ("SinVentasMasMenciones",   None, None, None, None, False, 0, None, None, None, 10)
        row_menos_menciones = ("SinVentasMenosMenciones", None, None, None, None, False, 0, None, None, None, 2)

        class _FakeDB:
            def execute(self, *a, **kw):
                return self
            def fetchall(self):
                return [row_menos_menciones, row_mas_menciones]

        result = list_locales_by_sector(_FakeDB(), ["3020"], limit=10)
        assert result[0].nombre == "SinVentasMasMenciones"
