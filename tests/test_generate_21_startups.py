"""Tests US3 — Generate21Startups (Startups y Disruptores).

Fast (sin DB ni red): stubs para chain_perfil, store, web_connector, entidad_repo.
5 casos del quickstart.md Escenario 3.
"""

from __future__ import annotations

from ic.domain.use_cases.generate_21_startups import Generate21Startups
from ic.domain.kb.relevance import LocalRow
from ic.shared.types import Cap21Startups, ChunkResult


def _web_chunk(nombre: str = "Startup Internacional") -> ChunkResult:
    return ChunkResult(
        chunk_texto=f"Info sobre {nombre}",
        fuente_tipo="web",
        fuente_url="http://x.com",
        score=0.8,
    )


class _FakeChain:
    def __init__(self, result: str = "### Startups y Disruptores del sector\n\nTexto."):
        self._result = result

    def invoke(self, payload):
        self._last_payload = payload
        return self._result


class _FakeStore:
    def __init__(self, chunks: list[ChunkResult] | None = None):
        self._chunks = chunks or []
        self.ingest_calls: list[dict] = []

    def ingest(self, texts, fuente_tipo, urls, empresa_id=None, metadatos_extra=None):
        self.ingest_calls.append({"fuente_tipo": fuente_tipo, "n": len(texts)})
        return len(texts)

    def search(self, query, **kwargs) -> list[ChunkResult]:
        return self._chunks


class _FakeWebConnector:
    def __init__(self, has_results: bool = True):
        self._has_results = has_results

    def search(self, query: str, max_results: int = 3):
        if not self._has_results:
            return []
        from ic.shared.types import WebResult
        return [WebResult(url="http://intl.com", title="Startup Int", content="content", snippet="s")]


class _FakeEntidadRepo:
    def __init__(self, locales: list[LocalRow] | None = None):
        self._locales = locales or []

    def list_locales_by_sector(self, *args, **kwargs) -> list[LocalRow]:
        return list(self._locales)


def _make_use_case(
    locales: list[LocalRow],
    web_chunks: list[ChunkResult] | None = None,
    web_has_results: bool = True,
    max_locales: int = 3,
    max_internacionales: int = 2,
) -> Generate21Startups:
    chain_perf = _FakeChain()
    store = _FakeStore(web_chunks or [_web_chunk()])
    web = _FakeWebConnector(web_has_results)
    repo = _FakeEntidadRepo(locales)
    return Generate21Startups(
        chain_perfil=chain_perf,
        store=store,
        web_connector=web,
        entidad_repo=repo,
        max_locales=max_locales,
        max_internacionales=max_internacionales,
    )


def test_startups_locales_desde_kb():
    locales = [
        LocalRow(nombre="StartupCo", ciudad="Bogotá", actividad="fintech", segmento="startup"),
        LocalRow(nombre="TechAndes", ciudad="Medellín", actividad="agritech", segmento="startup"),
    ]
    uc = _make_use_case(locales=locales)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        sectores_ancla=["3020"],
        empresa_id=None,
    )
    assert isinstance(result, Cap21Startups)
    assert result.retrieval_suficiente is True
    assert "StartupCo" in result.locales
    assert "TechAndes" in result.locales
    assert "### Startups y Disruptores" in result.texto


def test_internacionales_desde_web():
    uc = _make_use_case(locales=[], web_has_results=True, web_chunks=[_web_chunk("StartupInt")])
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        sectores_ancla=["3020"],
        empresa_id=None,
    )
    assert result.retrieval_suficiente is True
    assert len(result.internacionales) > 0


def test_ausencia_si_sin_locales_ni_web():
    uc = _make_use_case(locales=[], web_has_results=False, web_chunks=[])
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        sectores_ancla=["3020"],
        empresa_id=None,
    )
    assert result.retrieval_suficiente is False
    assert "Dato no disponible" in result.texto


def test_deduplicacion_local_vs_internacional():
    # Si un nombre local aparece en internacionales, solo aparece como local
    locales = [LocalRow(nombre="StartupCo", ciudad="Bogotá", segmento="startup")]
    # StartupCo también está en chunks web → debe deduplicarse
    chunks_web = [ChunkResult(
        chunk_texto="StartupCo es una startup colombiana de fintech",
        fuente_tipo="web",
        fuente_url="http://x.com",
        score=0.9,
    )]
    uc = _make_use_case(locales=locales, web_chunks=chunks_web, web_has_results=True)
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        sectores_ancla=["3020"],
        empresa_id=None,
    )
    assert result.retrieval_suficiente is True
    assert "StartupCo" in result.locales
    # No debería aparecer en internacionales
    assert "StartupCo" not in result.internacionales


def test_locales_aparecen_primero_en_prosa():
    locales = [LocalRow(nombre="LocalStartup", ciudad="Bogotá", segmento="startup")]
    chain = _FakeChain()
    uc = Generate21Startups(
        chain_perfil=chain,
        store=_FakeStore([_web_chunk()]),
        web_connector=_FakeWebConnector(True),
        entidad_repo=_FakeEntidadRepo(locales),
    )
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea",
        sector_gics="3020",
        sector_gics_code="3020",
        sectores_ancla=["3020"],
        empresa_id=None,
    )
    # El payload al chain debe tener locales antes que internacionales
    payload = chain._last_payload
    assert "LocalStartup" in payload.get("locales_context", "")
