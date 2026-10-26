"""RN-001 sobre fragmentos enriquecidos: estado en BD, curación humana y promoción (Spec 008)."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ic.data.repositories.embedding_estado_repo import EmbeddingEstadoRepository
from ic.domain.use_cases import curate_candidatos
from ic.domain.use_cases.auto_enrich import AutoEnrich
from ic.infrastructure.sources.enrichment_connector import FragmentoEnriquecido


def _session(rowcount=1, rows=()):
    s = MagicMock()
    s.execute.return_value.rowcount = rowcount
    s.execute.return_value.fetchall.return_value = list(rows)
    return s


# ---------------------------------------------------------------- T033: repositorio


def test_set_estado_actualiza_solo_desde_candidato():
    s = _session()
    cid = uuid.uuid4()
    assert EmbeddingEstadoRepository(s).set_estado_verificacion(cid, "verificado") is True
    sql = str(s.execute.call_args.args[0])
    assert "= 'candidato'" in sql and "jsonb_set" in sql
    assert s.execute.call_args.args[1] == {"estado": "verificado", "id": str(cid)}
    s.commit.assert_called_once()


def test_set_estado_sin_filas_devuelve_false():
    assert (
        EmbeddingEstadoRepository(_session(rowcount=0)).set_estado_verificacion(
            uuid.uuid4(), "descartado"
        )
        is False
    )


def test_set_estado_rechaza_estado_invalido():
    with pytest.raises(ValueError):
        EmbeddingEstadoRepository(_session()).set_estado_verificacion(uuid.uuid4(), "candidato")


def test_list_candidatos_mapea_filas():
    fila = SimpleNamespace(
        id=uuid.uuid4(), chunk_texto="t", fuente_url="u", titulo="T", autor="A",
        anio="2024", sector="5510", fuente="web_enrichment",
    )  # fmt: skip
    res = EmbeddingEstadoRepository(_session(rows=[fila])).list_candidatos(10)
    assert res == [
        {"id": str(fila.id), "texto": "t", "url": "u", "titulo": "T", "autor": "A",
         "año": "2024", "sector": "5510", "fuente": "web_enrichment"}
    ]  # fmt: skip


def test_retrieval_excluye_tambien_los_descartados():
    from ic.data.repositories.embedding_repo import EmbeddingRepository

    s = _session()
    EmbeddingRepository(s).search_similar([0.1], top_k=3, threshold=0.5)
    assert "'descartado'" in str(s.execute.call_args.args[0])


# ---------------------------------------------------------------- T035: curación humana


@pytest.mark.parametrize(("aprobar", "estado"), [(True, "verificado"), (False, "descartado")])
def test_resolver_candidato(aprobar, estado):
    cid = uuid.uuid4()
    with (
        patch.object(curate_candidatos, "SessionLocal"),
        patch.object(curate_candidatos, "EmbeddingEstadoRepository") as repo_cls,
    ):
        repo_cls.return_value.set_estado_verificacion.return_value = True
        assert curate_candidatos.resolver_candidato(str(cid), aprobar) is True
        repo_cls.return_value.set_estado_verificacion.assert_called_once_with(cid, estado)


def test_curacion_degrada_sin_romper():
    with patch.object(curate_candidatos, "SessionLocal", side_effect=RuntimeError("bd")):
        assert curate_candidatos.listar_candidatos() == []
        assert curate_candidatos.resolver_candidato(str(uuid.uuid4()), True) is False


# ---------------------------------------------------------------- T034: promoción automática


def _frag(fuente):
    return FragmentoEnriquecido(
        texto=f"Texto {fuente}", titulo="T", autores="A", año="2024",
        url="https://x.org", fuente=fuente, sector_gics="5510", idioma="es",
    )  # fmt: skip


def _enriquecer(fragmentos, respaldo):
    with (
        patch("ic.domain.use_cases.auto_enrich.SessionLocal"),
        patch("ic.domain.use_cases.auto_enrich.PGVectorStore") as store_cls,
        patch("ic.domain.use_cases.auto_enrich.EnrichmentConnector") as conn_cls,
        patch("ic.domain.use_cases.auto_enrich.EmbeddingRepository") as repo_cls,
        patch("ic.domain.use_cases.auto_enrich.EmbeddingEstadoRepository") as estado_cls,
    ):
        store_cls.return_value.search.return_value = [MagicMock(score=0.1)]
        conn_cls.return_value.fetch_fragments.return_value = fragmentos
        repo_cls.return_value.exists_by_sha256.return_value = False
        repo_cls.return_value.search_similar.return_value = respaldo
        estado_cls.return_value.set_estado_verificacion.return_value = True
        embedder = MagicMock()
        embedder.embed.return_value = [0.1] * 768
        settings = SimpleNamespace(rag_similarity_threshold=0.6)
        evento = AutoEnrich(settings=settings, embedder=embedder).try_enrich("5510", "q")
        return evento, repo_cls.return_value, estado_cls.return_value


def test_candidato_con_respaldo_se_promueve():
    evento, repo, estados = _enriquecer([_frag("web_enrichment")], respaldo=[(MagicMock(), 0.8)])
    assert evento.n_promovidos == 1
    args, kwargs = repo.search_similar.call_args
    assert args[1:3] == (1, 0.6) and kwargs == {"sector_gics": "5510", "sector_estricto": True}
    assert estados.set_estado_verificacion.call_args.args[1] == "verificado"


def test_candidato_sin_respaldo_queda_pendiente():
    evento, _, estados = _enriquecer([_frag("web_enrichment")], respaldo=[])
    assert evento.n_promovidos == 0
    estados.set_estado_verificacion.assert_not_called()


def test_openalex_no_pasa_por_promocion():
    evento, repo, _ = _enriquecer([_frag("openalex")], respaldo=[(MagicMock(), 0.9)])
    assert evento.enriquecido and evento.n_promovidos == 0
    repo.search_similar.assert_not_called()
