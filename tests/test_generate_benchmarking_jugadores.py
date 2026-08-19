"""T032 — Tests unitarios para la integración Generate21Jugadores en GenerateBenchmarking.

Sin DB ni red: stubs para chain, store, web_connector y jugadores_use_case.
Verifica el contrato de delegación y fallback per Constitution V / T024.
"""

from __future__ import annotations

from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
from ic.shared.types import Cap21Jugadores, CapBenchmarking, ChunkResult


class _FakeChain:
    def invoke(self, payload):
        return "## Cap 2\n\nTexto generado."


class _FakeStore:
    def __init__(self):
        self.ingest_calls = 0

    def ingest(self, texts, fuente_tipo, urls, empresa_id=None, metadatos_extra=None):
        self.ingest_calls += 1
        return len(texts)

    def search(self, query, **kwargs) -> list[ChunkResult]:
        return [
            ChunkResult(
                chunk_texto=f"contenido relevante chunk {i}",
                fuente_tipo="web",
                fuente_url="http://x.com",
                score=0.9,
            )
            for i in range(6)  # _MIN_CHUNKS = 5 → necesitamos ≥5
        ]


class _FakeWebConnector:
    def search(self, query, max_results=5, search_depth="basic"):
        from ic.shared.types import WebResult
        return [WebResult(url="http://x.com", title="T", content="c", snippet="s")]


class _FakeJugadoresUseCase:
    def __init__(self, result: Cap21Jugadores | None = None, raise_exc: Exception | None = None):
        self._result = result
        self._raise = raise_exc
        self.called = False
        self.last_kwargs: dict = {}

    def execute(self, **kwargs) -> Cap21Jugadores:
        self.called = True
        self.last_kwargs = kwargs
        if self._raise is not None:
            raise self._raise
        return self._result


def _cap21_suficiente() -> Cap21Jugadores:
    return Cap21Jugadores(
        texto="## 2.1. Jugadores Clave\n\n### Referentes Globales\n\nNestlé.",
        globales=None,
        regionales=None,
        startups=None,
        retrieval_suficiente=True,
    )


def _make_benchmarking(jugadores_use_case=None) -> GenerateBenchmarking:
    return GenerateBenchmarking(
        chain=_FakeChain(),
        store=_FakeStore(),
        web_connector=_FakeWebConnector(),
        jugadores_use_case=jugadores_use_case,
    )


def test_jugadores_use_case_delegado_cuando_inyectado():
    """GenerateBenchmarking.execute llama jugadores_use_case.execute y usa su texto."""
    jugadores = _FakeJugadoresUseCase(result=_cap21_suficiente())
    uc = _make_benchmarking(jugadores_use_case=jugadores)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
    )
    assert isinstance(result, CapBenchmarking)
    assert jugadores.called
    assert "## 2.1. Jugadores Clave" in result.texto


def test_fallback_a_kb_assembler_si_jugadores_falla():
    """Ante excepción de jugadores_use_case, GenerateBenchmarking continúa sin 2.1 modular."""
    jugadores = _FakeJugadoresUseCase(raise_exc=RuntimeError("LLM timeout"))
    uc = _make_benchmarking(jugadores_use_case=jugadores)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
    )
    assert isinstance(result, CapBenchmarking)
    assert jugadores.called
    assert result.texto  # sigue produciendo texto aunque falle el sub-módulo
