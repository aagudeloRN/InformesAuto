"""Tests unitarios para AutoEnrich y EnrichmentConnector (Spec 008 / US2)."""

from unittest.mock import MagicMock, patch

import pytest

from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.domain.use_cases.auto_enrich import AutoEnrich, EventoEnriquecimiento
from ic.infrastructure.sources.enrichment_connector import FragmentoEnriquecido


@pytest.fixture
def fragmentos_mock():
    return [
        FragmentoEnriquecido(
            texto="Párrafo sobre energía renovable en Colombia.",
            titulo="Informe Energético 2023",
            autores="García, J.",
            año="2023",
            url="https://openalex.org/W12345",
            fuente="openalex",
            sector_gics="5510",
            idioma="es",
        )
    ]


def test_try_enrich_success(fragmentos_mock):
    settings = MagicMock()

    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal") as mock_session_cls,
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as mock_store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as mock_conn_cls,
        patch("ic.domain.use_cases.auto_enrich.EmbeddingRepository") as mock_repo_cls,
    ):
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db

        mock_store = MagicMock()
        mock_chunk_result = MagicMock()
        mock_chunk_result.score = 0.2
        mock_store.search.return_value = [mock_chunk_result]  # < threshold 0.5
        mock_store_cls.return_value = mock_store

        mock_conn = MagicMock()
        mock_conn.fetch_fragments.return_value = fragmentos_mock
        mock_conn_cls.return_value = mock_conn

        mock_repo = MagicMock()
        mock_repo.exists_by_sha256.return_value = False
        mock_repo_cls.return_value = mock_repo

        embedder = MagicMock()
        embedder.embed.return_value = [0.1] * 768

        auto_enrich = AutoEnrich(settings=settings, embedder=embedder)
        res = auto_enrich.try_enrich(
            sector_gics="5510", query_text="energía renovable", threshold=0.5
        )

        assert res.enriquecido is True
        assert res.resultado == "enriquecido"
        assert res.fuentes == ["openalex"]
        mock_conn.fetch_fragments.assert_called_once()
        mock_repo.insert_many.assert_called_once()


def test_try_enrich_skips_when_evidence_sufficient():
    settings = MagicMock()

    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal") as mock_session_cls,
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as mock_store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as mock_conn_cls,
    ):
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db

        mock_store = MagicMock()
        mock_chunk_result = MagicMock()
        mock_chunk_result.score = 0.85
        mock_store.search.return_value = [mock_chunk_result]  # >= threshold 0.5
        mock_store_cls.return_value = mock_store

        mock_conn = MagicMock()
        mock_conn_cls.return_value = mock_conn

        embedder = MagicMock()
        auto_enrich = AutoEnrich(settings=settings, embedder=embedder)
        res = auto_enrich.try_enrich(
            sector_gics="5510", query_text="energía renovable", threshold=0.5
        )

        assert res.enriquecido is False
        assert res.resultado == "suficiente"
        mock_conn.fetch_fragments.assert_not_called()


def test_try_enrich_graceful_degradation_on_exception():
    settings = MagicMock()

    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal") as mock_session_cls,
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as mock_store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as mock_conn_cls,
    ):
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db

        mock_store = MagicMock()
        mock_chunk_result = MagicMock()
        mock_chunk_result.score = 0.1
        mock_store.search.return_value = [mock_chunk_result]
        mock_store_cls.return_value = mock_store

        mock_conn = MagicMock()
        mock_conn.fetch_fragments.side_effect = RuntimeError("OpenAlex API Timeout")
        mock_conn_cls.return_value = mock_conn

        embedder = MagicMock()
        auto_enrich = AutoEnrich(settings=settings, embedder=embedder)
        res = auto_enrich.try_enrich(
            sector_gics="5510", query_text="energía renovable", threshold=0.5
        )

        assert res.enriquecido is False
        assert res.resultado == "fallido"
        assert "OpenAlex API Timeout" in res.error


def test_maybe_auto_enrich_guard_enriched_sectors():
    ctx = MagicMock()
    ctx._enriched_sectors = set()
    ctx.settings = MagicMock()
    ctx.embedder = MagicMock()
    ctx.eventos_enriquecimiento = []

    with patch("ic.domain.use_cases.auto_enrich.AutoEnrich") as mock_auto_enrich_cls:
        mock_instance = MagicMock()
        mock_instance.try_enrich.return_value = EventoEnriquecimiento(
            sector="5510", score_previo=0.1, resultado="enriquecido", n_fragmentos=1
        )
        mock_auto_enrich_cls.return_value = mock_instance

        from ic.domain.use_cases._n1_chapter_builders import _maybe_auto_enrich

        res1 = _maybe_auto_enrich(ctx, "5510", "energía renovable")
        assert res1 is True
        assert "5510" in ctx._enriched_sectors
        assert mock_instance.try_enrich.call_count == 1

        res2 = _maybe_auto_enrich(ctx, "5510", "energía renovable")
        assert res2 is False
        assert mock_instance.try_enrich.call_count == 1
        assert len(ctx.eventos_enriquecimiento) == 1


def _run_try_enrich(fragmentos, *, existe=False, fetch_error=None, scores=(0.1,)):
    """Ejecuta try_enrich con todo simulado; devuelve (evento, mock_repo)."""
    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal"),
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as mock_store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as mock_conn_cls,
        patch("ic.domain.use_cases.auto_enrich.EmbeddingRepository") as mock_repo_cls,
    ):
        mock_store_cls.return_value.search.return_value = [MagicMock(score=s) for s in scores]
        mock_conn = mock_conn_cls.return_value
        if fetch_error:
            mock_conn.fetch_fragments.side_effect = fetch_error
        else:
            mock_conn.fetch_fragments.return_value = fragmentos
        mock_repo = mock_repo_cls.return_value
        mock_repo.exists_by_sha256.return_value = existe
        embedder = MagicMock()
        embedder.embed.return_value = [0.1] * 768
        evento = AutoEnrich(settings=MagicMock(), embedder=embedder).try_enrich("5510", "q")
        return evento, mock_repo


def test_evento_enriquecido(fragmentos_mock):
    evento, _ = _run_try_enrich(fragmentos_mock)
    assert (evento.resultado, evento.n_fragmentos, evento.score_previo) == ("enriquecido", 1, 0.1)
    assert evento.to_dict()["sector"] == "5510"


def test_evento_sin_evidencia():
    evento, repo = _run_try_enrich([])
    assert evento.resultado == "sin_evidencia"
    repo.insert_many.assert_not_called()


def test_evento_fallido():
    evento, _ = _run_try_enrich([], fetch_error=RuntimeError("caído"))
    assert evento.resultado == "fallido"
    assert evento.error == "caído"


def test_evento_llega_a_metricas():
    from ic.domain.use_cases._informe_context import _PipelineContext

    assert _PipelineContext.__dataclass_fields__["eventos_enriquecimiento"].default_factory is list
    evento = EventoEnriquecimiento(sector="5510", score_previo=0.1, resultado="fallido", error="x")
    assert {"enriquecimiento": [evento.to_dict()]}["enriquecimiento"][0]["resultado"] == "fallido"


def test_chunks_llevan_chunk_sha256(fragmentos_mock):
    import hashlib

    _, repo = _run_try_enrich(fragmentos_mock)
    chunks = repo.insert_many.call_args.args[0]
    esperado = hashlib.sha256(fragmentos_mock[0].texto.encode()).hexdigest()
    assert chunks[0].metadatos["chunk_sha256"] == esperado


def test_duplicados_en_el_lote_se_insertan_una_vez(fragmentos_mock):
    _, repo = _run_try_enrich(fragmentos_mock * 3)
    assert len(repo.insert_many.call_args.args[0]) == 1


def test_todos_existentes_no_inserta(fragmentos_mock):
    evento, repo = _run_try_enrich(fragmentos_mock, existe=True)
    assert evento.resultado == "ya_existentes"
    assert evento.enriquecido is False
    repo.insert_many.assert_not_called()


def test_exists_by_sha256_consulta_por_hash():
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = (1,)
    assert EmbeddingRepository(session).exists_by_sha256("abc") is True
    assert session.execute.call_args.args[1] == {"sha": "abc"}
    session.execute.return_value.fetchone.return_value = None
    assert EmbeddingRepository(session).exists_by_sha256("abc") is False


# --------------------------------------------------------------------------- RN-001 (FR-014/015)


def _frag(fuente):
    return FragmentoEnriquecido(
        texto=f"Texto de {fuente}",
        titulo="T",
        autores="A",
        año="2024",
        url="https://x.org/1",
        fuente=fuente,
        sector_gics="5510",
        idioma="es",
    )


def test_openalex_entra_verificado_y_web_candidato():
    _, repo = _run_try_enrich([_frag("openalex"), _frag("web_enrichment")])
    estados = {c.metadatos["fuente"]: c.metadatos["estado_verificacion"] for c in _insertados(repo)}
    assert estados == {"openalex": "verificado", "web_enrichment": "candidato"}


def _insertados(repo):
    return repo.insert_many.call_args.args[0]


def _sql_de_search_similar(**kwargs):
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = []
    EmbeddingRepository(session).search_similar([0.1], top_k=3, threshold=0.5, **kwargs)
    return str(session.execute.call_args.args[0])


def test_search_similar_excluye_candidatos_por_defecto():
    assert "estado_verificacion" in _sql_de_search_similar()


def test_search_similar_puede_incluir_candidatos():
    assert "estado_verificacion" not in _sql_de_search_similar(incluir_candidatos=True)


def test_fragmento_enriquecido_es_recuperable_con_el_mismo_umbral(fragmentos_mock):
    """SC-005: el chunk enriquecido sale por PGVectorStore.search como cualquier otro chunk."""
    from types import SimpleNamespace

    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore

    _, repo_ins = _run_try_enrich(fragmentos_mock)
    chunk = _insertados(repo_ins)[0]
    chunk.id = None

    settings = SimpleNamespace(rag_top_k=5, rag_similarity_threshold=0.6, rag_min_distinct_docs=0)
    repo = MagicMock()
    repo.search_similar.return_value = [(chunk, 0.8)]
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768

    res = PGVectorStore(embedder, repo, settings).search("energía", sector_gics="5510")

    assert res[0].metadatos["titulo"] == "Informe Energético 2023"
    assert repo.search_similar.call_args_list[0].args[2] == 0.6
    assert "incluir_candidatos" not in repo.search_similar.call_args_list[0].kwargs
