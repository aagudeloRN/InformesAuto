"""Tests US1 — Generate21Globales (Referentes Globales).

Fast (sin DB ni red): stubs para chain_candidatos, chain_perfil, store, web_connector.
5 casos del quickstart.md Escenario 1.
"""

from __future__ import annotations

import json

from ic.domain.use_cases.generate_21_globales import Generate21Globales
from ic.shared.types import Cap21Globales, ChunkResult


def _chunk(texto: str = "contexto", fuente: str = "web") -> ChunkResult:
    return ChunkResult(chunk_texto=texto, fuente_tipo=fuente, fuente_url="http://x.com", score=0.9)


class _FakeChain:
    def __init__(self, result):
        self._result = result

    def invoke(self, _payload):
        return self._result


class _FakeStore:
    def __init__(self, chunks: list[ChunkResult] | None = None):
        self._chunks = chunks or []
        self.ingest_calls: list[dict] = []
        self.search_calls: list[dict] = []

    def ingest(self, texts, fuente_tipo, urls, empresa_id=None, metadatos_extra=None):
        self.ingest_calls.append({"texts": texts, "fuente_tipo": fuente_tipo})
        return len(texts)

    def search(self, query, **kwargs) -> list[ChunkResult]:
        self.search_calls.append({"query": query, **kwargs})
        return self._chunks


class _FakeWebConnector:
    def __init__(self, results_per_query: int = 1):
        self._results_per_query = results_per_query
        self.search_calls: list[str] = []

    def search(self, query: str, max_results: int = 3):
        self.search_calls.append(query)
        from ic.shared.types import WebResult

        return [
            WebResult(url=f"http://ex.com/{i}", title="T", content="contenido", snippet="s")
            for i in range(self._results_per_query)
        ]


def _make_use_case(
    candidatos: list[str],
    chunks: list[ChunkResult],
    perfil_text: str = "### Referentes Globales\n\nTexto generado.",
    web_results: int = 1,
    max_empresas: int = 5,
) -> Generate21Globales:
    chain_cand = _FakeChain(json.dumps(candidatos))
    chain_perf = _FakeChain(perfil_text)
    store = _FakeStore(chunks)
    web = _FakeWebConnector(results_per_query=web_results)
    return Generate21Globales(
        chain_candidatos=chain_cand,
        chain_perfil=chain_perf,
        store=store,
        web_connector=web,
        max_empresas=max_empresas,
    )


def test_candidatos_propuestos_y_filtrados():
    chunks = [_chunk() for _ in range(3)]
    uc = _make_use_case(candidatos=["Nestlé", "Danone", "Fonterra"], chunks=chunks)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea colombiana",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert isinstance(result, Cap21Globales)
    assert result.retrieval_suficiente is True
    assert len(result.candidatos) == 3
    assert "### Referentes Globales" in result.texto


def test_candidatos_sin_web_se_omiten():
    uc = _make_use_case(
        candidatos=["Nestlé"],
        chunks=[],  # sin chunks → ausencia
        web_results=0,
    )
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert result.retrieval_suficiente is False
    assert result.n_candidatos_con_web == 0
    assert "Dato no disponible" in result.texto


def test_excluye_empresa_focal():
    chunks = [_chunk() for _ in range(3)]
    uc = _make_use_case(candidatos=["Alpina", "Nestlé", "Danone"], chunks=chunks)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea colombiana",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert "Alpina" not in result.candidatos


def test_ausencia_si_cero_candidatos():
    uc = _make_use_case(candidatos=[], chunks=[])
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert result.retrieval_suficiente is False
    assert result.candidatos == []
    assert "Dato no disponible" in result.texto


def test_max_5_empresas_respetado():
    chunks = [_chunk() for _ in range(5)]
    candidatos_raw = ["A", "B", "C", "D", "E", "F", "G"]
    uc = _make_use_case(candidatos=candidatos_raw, chunks=chunks, max_empresas=5)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert len(result.candidatos) <= 5
