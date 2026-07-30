"""DT-057/T2 (DT-053) — backfill de sectores_adicionales + aflorado multi-sector.

Fast (sin BD ni Ollama):
  1. `EmbeddingRepository.backfill_sectores` estampa el array multi-sector idempotentemente
     (Session falsa con estado; segunda corrida → 0 filas) y con la guarda de scope correcta.
  2. Un doc con `metadatos.sectores=[primario, secundario]` aflora al buscar el sector secundario
     (mock del repo, patrón `test_fase13_sectorial`).
  3. El SQL no estricto de `search_similar` filtra por `jsonb_exists` sobre `sectores` con el
     sector pedido (afford del aflorado multi-sector).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from ic.data.repositories.embedding_repo import EmbeddingRepository


class _FakeResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _StatefulSession:
    """Session falsa: mantiene el array `sectores` actual del doc y aplica el UPDATE con guarda."""

    def __init__(self, sectores_actual) -> None:
        self.sectores = sectores_actual  # None o lista
        self.sqls: list[str] = []

    def execute(self, sql, params=None):  # noqa: ANN001
        s = str(sql)
        self.sqls.append(s)
        if s.strip().upper().startswith("UPDATE"):
            nuevo = json.loads(params["sectores"])
            if self.sectores != nuevo:  # IS DISTINCT FROM
                self.sectores = nuevo
                return _FakeResult(1)
            return _FakeResult(0)
        return _FakeResult(0)

    def commit(self):
        pass


def test_backfill_sectores_idempotente():
    sess = _StatefulSession(None)
    repo = EmbeddingRepository(sess)

    n1 = repo.backfill_sectores("Informe Lácteos", ["3020", "2530"])
    n2 = repo.backfill_sectores("Informe Lácteos", ["3020", "2530"])  # mismo array → no-op

    assert n1 == 1
    assert n2 == 0
    assert sess.sectores == ["3020", "2530"]


def test_backfill_sectores_sql_scope_y_guarda():
    sess = _StatefulSession(None)
    EmbeddingRepository(sess).backfill_sectores("Doc X", ["3020", "2510"])
    sql = sess.sqls[-1]
    assert "metadatos->>'titulo' = :titulo" in sql          # acotado al documento
    assert "IS DISTINCT FROM CAST(:sectores AS jsonb)" in sql  # idempotencia
    assert "jsonb_build_object('sectores'" in sql


def test_doc_multi_sector_aflora_en_sector_secundario():
    """Patrón test_fase13_sectorial: el repo devuelve el chunk multi-sector para el 2º sector."""
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore

    settings = MagicMock()
    settings.rag_top_k = 3
    settings.rag_similarity_threshold = 0.7
    settings.rag_max_chunks_per_doc = 4
    settings.rag_sector_reserve = 0
    settings.rag_sector_reserve_threshold = 0.5
    settings.rag_global_reserve = 0
    settings.rag_empresa_reserve = 0
    settings.rag_mmr_lambda = 1.0
    settings.rag_min_distinct_docs = 0

    def _chunk(cid, sectores):
        obj = MagicMock()
        obj.id = cid
        obj.chunk_texto = f"c{cid}"
        obj.fuente_tipo = "pdf"
        obj.fuente_url = None
        # sector_gics primario 3020, pero multi-etiquetado para 2530 vía array `sectores`
        obj.metadatos = {"sector_gics": "3020", "sectores": sectores, "titulo": "Informe X"}
        return obj

    # Doc multi-sector 3020+2530 aflora al buscar el sector secundario 2530
    general = [(_chunk(10, ["3020", "2530"]), 0.72)]

    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768
    repo = MagicMock()
    repo.search_similar.return_value = general

    store = PGVectorStore(embedder, repo, settings)
    res = store.search("q", sector_gics="2530")

    assert "c10" in [r.chunk_texto for r in res]


def test_search_no_estricto_filtra_por_jsonb_exists_sectores():
    """El SQL no estricto usa jsonb_exists(sectores, :sector) → afford del aflorado multi-sector."""

    class _Capt:
        def __init__(self):
            self.sqls = []
            self.params = []

        def execute(self, sql, params=None):  # noqa: ANN001
            self.sqls.append(str(sql))
            self.params.append(params)
            return MagicMock(fetchall=lambda: [])

        def get(self, *_a, **_k):
            return None

    sess = _Capt()
    EmbeddingRepository(sess).search_similar(
        [0.1, 0.2, 0.3], top_k=3, threshold=0.5, sector_gics="2530", sector_estricto=False
    )
    sql = sess.sqls[-1]
    assert "jsonb_exists(e.metadatos->'sectores', :sector)" in sql
    assert sess.params[-1]["sector"] == "2530"
