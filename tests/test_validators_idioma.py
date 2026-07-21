"""Tests de validación de idioma CJK en los use cases N1–N3 (T10.1)."""

from unittest.mock import MagicMock

from ic.shared.types import (
    CapAccionables,
    CapBenchmarking,
    CapConvergencia,
    CapEcosistema,
    CapTendencias,
    ChunkResult,
    ResumenEjecutivo,
)

_CJK_TEXT = "这是中文文本，包含多个汉字字符用于测试。系统应该拒绝这段文字。"
_ES_TEXT = "Este es un texto en español latino neutro que el sistema debe aceptar."

def _make_chunks(n: int = 6) -> list[ChunkResult]:
    return [
        ChunkResult(chunk_texto=f"Texto único del chunk número {i}.", fuente_tipo="web",
                    fuente_url=f"https://fuente{i}.com", score=0.9)
        for i in range(n)
    ]


_DUMMY_CHUNKS = _make_chunks(6)


def _make_chain(texto: str) -> MagicMock:
    chain = MagicMock()
    chain.invoke.return_value = texto
    return chain


def _make_store(chunks=None) -> MagicMock:
    store = MagicMock()
    store.search.return_value = chunks if chunks is not None else _DUMMY_CHUNKS
    store.ingest.return_value = None
    return store


def _make_web() -> MagicMock:
    web = MagicMock()
    web.search.return_value = []
    return web


# ── GenerateBenchmarking ──────────────────────────────────────────────────


class TestBenchmarkingCJK:
    def _uc(self, texto: str) -> CapBenchmarking:
        from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
        return GenerateBenchmarking(
            chain=_make_chain(texto),
            store=_make_store(),
            web_connector=_make_web(),
        ).execute("Empresa Test", "Descripción.", "Sector Alimentos")

    def test_cjk_devuelve_ausencia(self):
        cap = self._uc(_CJK_TEXT)
        assert cap.retrieval_suficiente is False
        assert "incorrecto" in cap.texto or "Cap 2" in cap.texto

    def test_espanol_devuelve_cap_normal(self):
        cap = self._uc(_ES_TEXT)
        assert cap.retrieval_suficiente is True
        assert cap.texto == _ES_TEXT


# ── GenerateTendencias ────────────────────────────────────────────────────


class TestTendenciasCJK:
    def _uc(self, texto: str) -> CapTendencias:
        from ic.domain.use_cases.generate_tendencias import GenerateTendencias
        openalex = MagicMock()
        openalex.search.return_value = []
        return GenerateTendencias(
            chain=_make_chain(texto),
            store=_make_store(),
            web_connector=_make_web(),
            openalex_connector=openalex,
        ).execute("Empresa Test", "Descripción.", "Sector Alimentos")

    def test_cjk_devuelve_ausencia(self):
        cap = self._uc(_CJK_TEXT)
        assert cap.retrieval_suficiente is False
        assert "Cap 3" in cap.texto or "incorrecto" in cap.texto

    def test_espanol_devuelve_cap_normal(self):
        cap = self._uc(_ES_TEXT)
        assert cap.retrieval_suficiente is True
        assert cap.texto == _ES_TEXT


# ── GenerateEcosistema ────────────────────────────────────────────────────


class TestEcosistemaCJK:
    def _uc(self, texto: str) -> CapEcosistema:
        from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
        return GenerateEcosistema(
            chain=_make_chain(texto),
            store=_make_store(),
            web_connector=_make_web(),
        ).execute("Empresa Test", "Descripción.", "Sector Alimentos")

    def test_cjk_devuelve_ausencia(self):
        cap = self._uc(_CJK_TEXT)
        assert cap.retrieval_suficiente is False
        assert "Cap 4" in cap.texto or "incorrecto" in cap.texto

    def test_espanol_devuelve_cap_normal(self):
        cap = self._uc(_ES_TEXT)
        assert cap.retrieval_suficiente is True
        assert cap.texto == _ES_TEXT


# ── GenerateConvergencia ──────────────────────────────────────────────────


class TestConvergenciaCJK:
    def _uc_monolitica(self, texto: str) -> CapConvergencia:
        from ic.domain.use_cases.generate_convergencia import GenerateConvergencia
        return GenerateConvergencia(
            chain=_make_chain(texto),
            store=_make_store(),
            web_connector=_make_web(),
            chain_eje=None,
        ).execute("Empresa Test", "Descripción.", "Sector Alimentos")

    def _uc_dividida(self, texto_final: str) -> CapConvergencia:
        from ic.domain.use_cases.generate_convergencia import GenerateConvergencia
        chain_synth = _make_chain(texto_final)
        chain_eje = _make_chain("Análisis del eje.")
        return GenerateConvergencia(
            chain=chain_synth,
            store=_make_store(),
            web_connector=_make_web(),
            chain_eje=chain_eje,
        ).execute("Empresa Test", "Descripción.", "Sector Alimentos")

    def test_monolitica_cjk_devuelve_ausencia(self):
        cap = self._uc_monolitica(_CJK_TEXT)
        assert cap.retrieval_suficiente is False

    def test_monolitica_espanol_ok(self):
        cap = self._uc_monolitica(_ES_TEXT)
        assert cap.retrieval_suficiente is True

    def test_dividida_cjk_en_sintesis_devuelve_ausencia(self):
        cap = self._uc_dividida(_CJK_TEXT)
        assert cap.retrieval_suficiente is False

    def test_dividida_espanol_ok(self):
        cap = self._uc_dividida(_ES_TEXT)
        assert cap.retrieval_suficiente is True


# ── GenerateAccionables ───────────────────────────────────────────────────


class TestAccionablesCJK:
    def _uc(self, texto: str) -> CapAccionables:
        from ic.domain.use_cases.generate_accionables import GenerateAccionables
        return GenerateAccionables(
            chain=_make_chain(texto),
            store=_make_store(_DUMMY_CHUNKS),
        ).execute("Empresa Test", "Descripción.", "Sector Alimentos")

    def test_cjk_devuelve_ausencia(self):
        cap = self._uc(_CJK_TEXT)
        assert cap.retrieval_suficiente is False
        assert "Cap 6" in cap.texto or "incorrecto" in cap.texto

    def test_espanol_devuelve_cap_normal(self):
        cap = self._uc(_ES_TEXT)
        assert cap.retrieval_suficiente is True


# ── GenerateResumenEjecutivo ──────────────────────────────────────────────


class TestResumenEjecutivoCJK:
    def _uc(self, texto: str) -> ResumenEjecutivo:
        from ic.domain.use_cases.generate_resumen_ejecutivo import GenerateResumenEjecutivo
        return GenerateResumenEjecutivo(
            chain=_make_chain(texto),
        ).execute(
            nombre_empresa="Empresa Test",
            descripcion_empresa="Descripción.",
            sector_gics="Sector Alimentos",
            cap_textos={"Cap 1": "Contenido cap 1."},
        )

    def test_cjk_devuelve_ausencia(self):
        resumen = self._uc(_CJK_TEXT)
        assert resumen.retrieval_suficiente is False
        assert "Resumen" in resumen.texto or "incorrecto" in resumen.texto

    def test_espanol_devuelve_resumen_normal(self):
        resumen = self._uc(_ES_TEXT)
        assert resumen.retrieval_suficiente is True
        assert resumen.texto == _ES_TEXT
