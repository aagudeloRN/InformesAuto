"""Tests Fase 21 — Calidad de Contenido (Sprint A + A').

Cubre: search_depth parametrizable (T21.1), constraint sectorial casos locales (T21.2),
des-sesgado de prompts (T21.5), Metodología + Aviso IA (T21.7), rediseño Cap 4 (T21.8)
y Cap 2.3 Mercado (T21.6). Todos fast (sin BD ni LLM real; mocks).
"""

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# T21.1 (DT-035) — search_depth parametrizable
# ---------------------------------------------------------------------------


def _settings_tavily():
    s = MagicMock()
    s.tavily_api_key = "test-key"
    return s


def test_search_tavily_propaga_search_depth_al_payload():
    from ic.infrastructure.sources.web_connector import WebConnector

    conn = WebConnector(_settings_tavily())
    with patch("ic.infrastructure.sources.web_connector.httpx.post") as mpost:
        mpost.return_value.json.return_value = {"results": []}
        mpost.return_value.raise_for_status.return_value = None
        conn.search("q competidores", search_depth="advanced")

    payload = mpost.call_args.kwargs["json"]
    assert payload["search_depth"] == "advanced"


def test_search_default_es_basic():
    from ic.infrastructure.sources.web_connector import WebConnector

    conn = WebConnector(_settings_tavily())
    with patch("ic.infrastructure.sources.web_connector.httpx.post") as mpost:
        mpost.return_value.json.return_value = {"results": []}
        mpost.return_value.raise_for_status.return_value = None
        conn.search("q generica")

    assert mpost.call_args.kwargs["json"]["search_depth"] == "basic"


def test_cached_web_propaga_search_depth_y_separa_clave():
    from ic.infrastructure.sources.cached_connector import CachedWebConnector

    inner = MagicMock()
    inner.search.return_value = []
    repo = MagicMock()
    repo.get_fresh.return_value = None
    settings = MagicMock()
    settings.retrieval_cache_ttl_hours = 24

    with patch(
        "ic.infrastructure.sources.cached_connector.RetrievalCacheRepository",
        return_value=repo,
    ):
        cached = CachedWebConnector(inner, MagicMock(), settings)
        cached.search("perfil competidor", search_depth="advanced")

    # Propaga search_depth al connector subyacente.
    assert inner.search.call_args.kwargs["search_depth"] == "advanced"
    # La clave de caché se diferencia cuando no es basic.
    cache_query = repo.get_fresh.call_args.args[1]
    assert "depth=advanced" in cache_query


def test_generate_benchmarking_usa_advanced_en_queries_competidores():
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking

    web = MagicMock()
    web.search.return_value = []
    store = MagicMock()
    store.search.return_value = []  # retrieval insuficiente → corta temprano
    gb = GenerateBenchmarking(chain=MagicMock(), store=store, web_connector=web)

    gb.execute(
        nombre_empresa="ACME",
        descripcion_empresa="desc",
        sector_gics="Transporte (GICS 2030)",
    )

    assert web.search.call_count >= 1
    assert all(
        c.kwargs.get("search_depth") == "advanced" for c in web.search.call_args_list
    )


# ---------------------------------------------------------------------------
# T21.2 (DT-036) — constraint sectorial en casos locales Cap 3
# ---------------------------------------------------------------------------


def test_chain_04_casos_locales_tiene_constraint_sectorial():
    from ic.domain.chains.chain_04_tendencias import USER_PROMPT_04

    assert "RESTRICCIÓN SECTORIAL OBLIGATORIA" in USER_PROMPT_04
    assert "{sector_gics}" in USER_PROMPT_04
    assert "NO uses casos de otros sectores" in USER_PROMPT_04


def test_generate_tendencias_lanza_query_casos_locales_sectorial():
    from ic.domain.use_cases.generate_tendencias import GenerateTendencias

    web = MagicMock()
    web.search.return_value = []
    openalex = MagicMock()
    openalex.search.return_value = []
    store = MagicMock()
    store.search.return_value = []  # corta tras las queries web
    gt = GenerateTendencias(
        chain=MagicMock(), store=store, web_connector=web, openalex_connector=openalex
    )

    gt.execute(
        nombre_empresa="ACME",
        descripcion_empresa="desc",
        sector_gics="Bancos (GICS 4010)",
    )

    queries = [c.args[0] for c in web.search.call_args_list]
    assert any("caso de éxito" in q and "Medellín" in q for q in queries)


# ---------------------------------------------------------------------------
# T21.5 (DT-043) — des-sesgar prompts por {sector_gics}
# ---------------------------------------------------------------------------

_SESGO = ["FoodTech", "agroindustrial", "bienes de consumo"]


def test_chain_03_sin_sesgo_sectorial_y_parametrizado():
    from ic.domain.chains.chain_03_benchmarking import SYSTEM_PROMPT_03, USER_PROMPT_03

    combinado = SYSTEM_PROMPT_03 + USER_PROMPT_03
    for termino in _SESGO:
        assert termino not in combinado
    assert "{sector_gics}" in SYSTEM_PROMPT_03
    assert "{sector_gics}" in USER_PROMPT_03


def test_chain_04_sin_sesgo_sectorial():
    from ic.domain.chains.chain_04_tendencias import SYSTEM_PROMPT_04

    for termino in _SESGO:
        assert termino not in SYSTEM_PROMPT_04
    assert "{sector_gics}" in SYSTEM_PROMPT_04


def _chunk(i):
    from ic.shared.types import ChunkResult

    return ChunkResult(
        chunk_texto=f"perfil competidor {i}", fuente_tipo="web",
        fuente_url="http://x", score=0.8, metadatos={"autor": "X", "año": "2025"},
        chunk_id=f"id-{i}",
    )


def test_generate_benchmarking_pasa_sector_gics_al_invoke():
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking

    web = MagicMock()
    web.search.return_value = []
    store = MagicMock()
    store.search.return_value = [_chunk(i) for i in range(6)]  # retrieval suficiente
    chain = MagicMock()
    chain.invoke.return_value = "## 2.1 texto sin radar"
    gb = GenerateBenchmarking(chain=chain, store=store, web_connector=web)

    gb.execute(
        nombre_empresa="ACME",
        descripcion_empresa="desc",
        sector_gics="Transporte (GICS 2030)",
    )

    payload = chain.invoke.call_args.args[0]
    assert payload["sector_gics"] == "Transporte (GICS 2030)"


# ---------------------------------------------------------------------------
# T21.7 (DT-045) — Metodología + Aviso de uso de IA en el ensamblado
# ---------------------------------------------------------------------------


def _informe_minimo():
    from ic.shared.types import (
        CapBenchmarking,
        ClasificacionGICS,
        DescripcionEmpresa,
        InformePiloto,
    )

    empresa = DescripcionEmpresa(nombre_empresa="ACME S.A.", actividad_ciiu=None, texto="**ACME**")
    gics = ClasificacionGICS(grupo_gics="Bancos (GICS 4010)", justificacion="j", texto_raw="r")
    cap = CapBenchmarking(
        texto="## 2.1. Jugadores\nTexto.", n_chunks_usados=1, retrieval_suficiente=True,
    )
    return InformePiloto(empresa=empresa, gics=gics, cap_benchmarking=cap)


def test_assembler_incluye_metodologia_y_aviso_ia():
    from ic.domain.assembler import PilotAssembler
    from ic.domain.report_model import Heading

    report = PilotAssembler().build(_informe_minimo())
    headings = [b.text for b in report.blocks if isinstance(b, Heading)]
    assert "Metodología" in headings
    assert "Aviso sobre el uso de inteligencia artificial" in headings


# ---------------------------------------------------------------------------
# T21.8 (DT-046) — rediseño Cap 4 a 4.1–4.5 (movimientos corporativos)
# ---------------------------------------------------------------------------


def test_chain_05_estructura_movimientos_4_1_a_4_5():
    from ic.domain.chains.chain_05_ecosistema import SYSTEM_PROMPT_05, USER_PROMPT_05

    for subcap in [
        "## 4.1. Inversiones",
        "## 4.2. Integraciones Verticales",
        "## 4.3. Fusiones y Adquisiciones",
        "## 4.4. Joint Ventures",
        "## 4.5. Alianzas de Compra",
    ]:
        assert subcap in USER_PROMPT_05
    # Campos por evento (patrón Noel).
    assert "Capacidad estratégica adquirida" in USER_PROMPT_05
    assert "Vulnerabilidad mitigada" in USER_PROMPT_05
    assert "{sector_gics}" in SYSTEM_PROMPT_05
    # Ya no mapea actores estáticos (estructura vieja).
    assert "Actores Disruptores" not in USER_PROMPT_05
