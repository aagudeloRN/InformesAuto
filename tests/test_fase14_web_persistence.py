"""Tests Fase 14 — persistencia web "solo lo citado" (T14.5, DT-020).

Los tests de la lógica SQL (promoción/purga/barrido) requieren PostgreSQL → marcados `slow`.
Los tests de stamping de session_id y selección de citados son fast (mocked).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from ic.data.database import SessionLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.repositories.embedding_repo import EmbeddingRepository

# --- Fast: stamping de session_id en ingest ---


def test_ingest_estampa_session_id_solo_en_web():
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore

    settings = MagicMock()
    settings.rag_top_k = 10
    settings.rag_similarity_threshold = 0.7
    settings.rag_max_chunks_per_doc = 4
    settings.rag_sector_reserve = 3
    settings.rag_sector_reserve_threshold = 0.5
    settings.rag_mmr_lambda = 0.7

    embedder = MagicMock()
    embedder.embed_many.side_effect = lambda ts: [[0.1] * 768 for _ in ts]
    repo = MagicMock()

    store = PGVectorStore(embedder, repo, settings)
    store.session_id = "sess-abc"

    store.ingest(texts=["contenido web"], fuente_tipo="web", urls=["http://x"])
    insertados = repo.insert_many.call_args.args[0]
    assert all(o.metadatos["session_id"] == "sess-abc" for o in insertados)


def test_ingest_no_estampa_session_en_pdf():
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore

    settings = MagicMock()
    settings.rag_top_k = 10
    settings.rag_similarity_threshold = 0.7
    settings.rag_max_chunks_per_doc = 4
    settings.rag_sector_reserve = 3
    settings.rag_sector_reserve_threshold = 0.5
    settings.rag_mmr_lambda = 0.7

    embedder = MagicMock()
    embedder.embed_many.side_effect = lambda ts: [[0.1] * 768 for _ in ts]
    repo = MagicMock()

    store = PGVectorStore(embedder, repo, settings)
    store.session_id = "sess-abc"

    store.ingest(texts=["informe"], fuente_tipo="pdf", urls=[None])
    insertados = repo.insert_many.call_args.args[0]
    # Los chunks pdf no llevan session_id (no participan de la política web).
    assert all(not (o.metadatos or {}).get("session_id") for o in insertados)


# --- Fast: cableado del orquestador (selección de citados + llamadas al repo) ---


def _chunk_result(fuente_tipo, chunk_id):
    from ic.shared.types import ChunkResult
    return ChunkResult(
        chunk_texto="x", fuente_tipo=fuente_tipo, fuente_url=None,
        score=0.8, metadatos=None, chunk_id=chunk_id,
    )


def test_promote_cited_web_selecciona_solo_web_con_id():
    from ic.domain.use_cases.generate_informe import GenerateInforme, _PipelineContext

    ctx = _PipelineContext(params=MagicMock(), settings=MagicMock(), step_fn=None,
                           total_start=0.0, session_id="sess-1")
    chunks = [
        _chunk_result("web", "id-web-1"),
        _chunk_result("web", "id-web-2"),
        _chunk_result("pdf", "id-pdf-1"),   # no es web → se ignora
        _chunk_result("web", None),          # web sin id → se ignora
    ]
    repo = MagicMock()
    repo.promote_cited_web.return_value = (0, 2)
    with (
        patch("ic.data.database.SessionLocal") as msess,
        patch("ic.data.repositories.embedding_repo.EmbeddingRepository", return_value=repo),
    ):
        msess.return_value.__enter__.return_value = MagicMock()
        GenerateInforme(MagicMock())._promote_cited_web(ctx, chunks)

    sid, cited = repo.promote_cited_web.call_args.args
    assert sid == "sess-1"
    assert cited == ["id-web-1", "id-web-2"]


def test_sweep_stale_web_llama_al_repo_con_session():
    from ic.domain.use_cases.generate_informe import GenerateInforme, _PipelineContext

    ctx = _PipelineContext(params=MagicMock(), settings=MagicMock(), step_fn=None,
                           total_start=0.0, session_id="sess-9")
    repo = MagicMock()
    repo.sweep_stale_web_sessions.return_value = 3
    with (
        patch("ic.data.database.SessionLocal") as msess,
        patch("ic.data.repositories.embedding_repo.EmbeddingRepository", return_value=repo),
    ):
        msess.return_value.__enter__.return_value = MagicMock()
        GenerateInforme(MagicMock())._sweep_stale_web(ctx)

    assert repo.sweep_stale_web_sessions.call_args.args[0] == "sess-9"


# --- Slow: ciclo de vida real contra PostgreSQL ---


def _mk_web_chunk(db, session_id=None, promoted=False, texto="web x"):
    meta: dict = {"titulo": "t", "fuente_nombre": "x"}
    if session_id:
        meta["session_id"] = session_id
    if promoted:
        meta["promoted"] = "true"
    obj = EmbeddingVectorial(
        fuente_tipo="web", fuente_url="http://x", chunk_texto=texto,
        chunk_index=0, embedding=[0.01] * 768, metadatos=meta,
    )
    db.add(obj)
    db.commit()
    return obj.id


@pytest.mark.slow
def test_promote_cited_web_borra_no_citados_y_promueve_citados():
    sid = f"test-{uuid.uuid4().hex}"
    with SessionLocal() as db:
        repo = EmbeddingRepository(db)
        cited = _mk_web_chunk(db, session_id=sid, texto="citado")
        _dropped = _mk_web_chunk(db, session_id=sid, texto="descartado")

        borrados, promovidos = repo.promote_cited_web(sid, [str(cited)])
        assert borrados == 1 and promovidos == 1

        promoted_obj = db.get(EmbeddingVectorial, cited)
        assert promoted_obj is not None
        assert "session_id" not in (promoted_obj.metadatos or {})
        assert (promoted_obj.metadatos or {}).get("promoted") == "true"

        # limpieza
        db.delete(promoted_obj)
        db.commit()


@pytest.mark.slow
def test_sweep_stale_web_sessions_borra_otras_sesiones():
    keep = f"keep-{uuid.uuid4().hex}"
    stale = f"stale-{uuid.uuid4().hex}"
    with SessionLocal() as db:
        repo = EmbeddingRepository(db)
        keep_id = _mk_web_chunk(db, session_id=keep)
        stale_id = _mk_web_chunk(db, session_id=stale)

        n = repo.sweep_stale_web_sessions(keep)
        assert n >= 1
        assert db.get(EmbeddingVectorial, stale_id) is None
        assert db.get(EmbeddingVectorial, keep_id) is not None

        db.delete(db.get(EmbeddingVectorial, keep_id))
        db.commit()


@pytest.mark.slow
def test_purge_unused_web_backlog_solo_borra_legacy():
    sid = f"inses-{uuid.uuid4().hex}"
    with SessionLocal() as db:
        repo = EmbeddingRepository(db)
        legacy_id = _mk_web_chunk(db, texto="legacy sin marcas")
        promoted_id = _mk_web_chunk(db, promoted=True, texto="promovido")
        insession_id = _mk_web_chunk(db, session_id=sid, texto="en sesión")

        repo.purge_unused_web_backlog()

        assert db.get(EmbeddingVectorial, legacy_id) is None      # legacy borrado
        assert db.get(EmbeddingVectorial, promoted_id) is not None  # promovido intacto
        assert db.get(EmbeddingVectorial, insession_id) is not None  # en sesión intacto

        for cid in (promoted_id, insession_id):
            db.delete(db.get(EmbeddingVectorial, cid))
        db.commit()
