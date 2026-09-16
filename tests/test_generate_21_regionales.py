"""Tests US2 — Generate21Regionales (Referentes Regionales).

Fast (sin DB ni red): stubs para chain_perfil, store, web_connector.
4 casos del quickstart.md Escenario 2.
"""

from __future__ import annotations

from ic.domain.use_cases.generate_21_regionales import Generate21Regionales
from ic.shared.types import Cap21Regionales, ChunkResult


def _emis_chunk(nombre: str = "Empresa Regional") -> ChunkResult:
    return ChunkResult(
        chunk_texto=f"Información sobre {nombre}",
        fuente_tipo="emis",
        fuente_url=None,
        score=0.85,
        metadatos={"sector_gics": "3020", "empresa": nombre},
    )


def _web_chunk() -> ChunkResult:
    return ChunkResult(
        chunk_texto="Web info", fuente_tipo="web", fuente_url="http://x.com", score=0.7
    )


class _FakeChain:
    def __init__(self, result: str = "### Referentes Regionales LatAm/Colombia\n\nTexto."):
        self._result = result

    def invoke(self, _payload):
        return self._result


class _FakeStore:
    def __init__(self, emis_chunks: list[ChunkResult] | None = None):
        self._emis_chunks = emis_chunks or []
        self.ingest_calls: list[dict] = []
        self.search_calls: list[dict] = []

    def ingest(self, texts, fuente_tipo, urls, empresa_id=None, metadatos_extra=None):
        self.ingest_calls.append({"fuente_tipo": fuente_tipo})
        return len(texts)

    def search(self, query, fuente_tipo_filter=None, **kwargs) -> list[ChunkResult]:
        self.search_calls.append({"query": query, "fuente_tipo_filter": fuente_tipo_filter})
        if fuente_tipo_filter == "emis":
            return self._emis_chunks
        return []


class _FakeWebConnector:
    def __init__(self, has_results: bool = True):
        self._has_results = has_results

    def search(self, query: str, max_results: int = 3):
        if not self._has_results:
            return []
        from ic.shared.types import WebResult

        return [WebResult(url="http://x.com", title="T", content="c", snippet="s")]


def _make_use_case(
    emis_chunks: list[ChunkResult],
    perfil_text: str = "### Referentes Regionales LatAm/Colombia\n\nTexto.",
    max_empresas: int = 3,
    web_has_results: bool = True,
) -> Generate21Regionales:
    return Generate21Regionales(
        chain_perfil=_FakeChain(perfil_text),
        store=_FakeStore(emis_chunks),
        web_connector=_FakeWebConnector(web_has_results),
        max_empresas=max_empresas,
    )


def test_retrieval_emis_exclusivo():
    emis = [_emis_chunk(f"Empresa{i}") for i in range(4)]
    uc = _make_use_case(emis_chunks=emis)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert isinstance(result, Cap21Regionales)
    assert result.retrieval_suficiente is True
    assert result.n_con_emis > 0
    # Store search fue llamado con fuente_tipo_filter=emis
    assert uc._store.search_calls[0]["fuente_tipo_filter"] == "emis"


def test_ausencia_si_sin_chunks_emis():
    uc = _make_use_case(emis_chunks=[])
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert result.retrieval_suficiente is False
    assert "Dato no disponible" in result.texto
    assert result.n_con_emis == 0


def test_complemento_web_no_reemplaza_emis():
    emis = [_emis_chunk(f"Empresa{i}") for i in range(3)]
    uc = _make_use_case(emis_chunks=emis, web_has_results=True)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert result.retrieval_suficiente is True
    # El retrieval principal siempre es EMIS
    emis_search = [c for c in uc._store.search_calls if c.get("fuente_tipo_filter") == "emis"]
    assert len(emis_search) >= 1


def test_max_3_empresas_regionales():
    # Con más de 3 chunks EMIS, el resultado no debe superar max_empresas
    emis = [_emis_chunk(f"EmpresaX{i}") for i in range(6)]
    uc = _make_use_case(emis_chunks=emis, max_empresas=3)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert result.retrieval_suficiente is True
    assert len(result.empresas_emis) <= 3


def test_excluye_empresa_focal_de_regionales():
    """Los nombres EMIS que coinciden con la empresa focal no deben aparecer en empresas_emis."""
    # Alpina aparece en los metadatos de un chunk EMIS
    emis = [
        _emis_chunk("Alpina"),  # empresa focal → debe filtrarse
        _emis_chunk("Nutresa"),
        _emis_chunk("Colanta"),
    ]
    uc = _make_use_case(emis_chunks=emis)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        empresa_id=None,
    )
    assert result.retrieval_suficiente is True
    assert "Alpina" not in result.empresas_emis
    assert "Nutresa" in result.empresas_emis
    assert "Colanta" in result.empresas_emis
