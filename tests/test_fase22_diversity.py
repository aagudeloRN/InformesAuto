"""T22.A1 (DT-049) — Garantía de diversidad de documentos en el retrieval.

Tests mockeados (sin Ollama ni PostgreSQL): un repo y un embedder falsos controlan el pool de
candidatos para verificar que `PGVectorStore.search()` diversifica los documentos devueltos.
"""

from __future__ import annotations

from types import SimpleNamespace

from ic.infrastructure.retrieval.pgvector_store import PGVectorStore


class _FakeObj:
    """Sustituto de EmbeddingVectorial con solo los campos que search() consume."""

    def __init__(
        self, id_, documento_id=None, fuente_url=None, texto="chunk", tipo="pdf", meta=None
    ) -> None:
        self.id = id_
        self.documento_id = documento_id
        self.fuente_url = fuente_url
        self.chunk_texto = texto
        self.fuente_tipo = tipo
        self.metadatos = meta or {}


class _FakeEmbedder:
    def embed(self, _query: str) -> list[float]:
        return [0.0] * 8


class _FakeRepo:
    """Devuelve un pool fijo para la búsqueda base y nada para las reservas estrictas."""

    def __init__(self, pool: list[tuple]) -> None:
        self._pool = pool

    def search_similar(
        self,
        _vec,
        top_k,
        _threshold,
        _empresa_id=None,
        sector_gics=None,
        solo_activos=True,
        max_chunks_per_doc=None,
        sector_estricto=False,
        global_estricto=False,
        empresa_estricto=False,
        mmr_lambda=1.0,
        fuente_tipo_filter=None,
    ) -> list[tuple]:
        if sector_estricto or global_estricto or empresa_estricto:
            return []
        return self._pool[:top_k]


def _settings(**overrides) -> SimpleNamespace:
    base = dict(
        rag_top_k=6,
        rag_similarity_threshold=0.5,
        rag_max_chunks_per_doc=2,
        rag_sector_reserve=0,
        rag_sector_reserve_threshold=0.5,
        rag_global_reserve=0,
        rag_empresa_reserve=0,
        rag_mmr_lambda=0.7,
        rag_min_distinct_docs=5,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _store(pool: list[tuple], **settings_overrides) -> PGVectorStore:
    return PGVectorStore(_FakeEmbedder(), _FakeRepo(pool), _settings(**settings_overrides))


def _distinct_docs(results) -> set:
    return {r.metadatos.get("doc") for r in results}


def test_search_backfills_to_min_distinct_docs():
    """Base concentrada en 3 docs → search() rellena hasta 5 docs distintos del pool."""
    # Pool ordenado por score desc, ya "capado" a 2 chunks/doc como haría el SQL.
    pool = [
        (_FakeObj("a1", "docA", meta={"doc": "A"}), 0.95),
        (_FakeObj("a2", "docA", meta={"doc": "A"}), 0.94),
        (_FakeObj("b1", "docB", meta={"doc": "B"}), 0.90),
        (_FakeObj("b2", "docB", meta={"doc": "B"}), 0.89),
        (_FakeObj("c1", "docC", meta={"doc": "C"}), 0.85),
        (_FakeObj("c2", "docC", meta={"doc": "C"}), 0.84),  # base [:6] → solo A,B,C
        (_FakeObj("d1", "docD", meta={"doc": "D"}), 0.80),
        (_FakeObj("e1", "docE", meta={"doc": "E"}), 0.78),
        (_FakeObj("f1", "docF", meta={"doc": "F"}), 0.76),
    ]
    results = _store(pool).search("competidores del sector")

    assert len(results) == 6  # no baja de top_k
    assert len(_distinct_docs(results)) >= 5  # garantía de diversidad
    # Los docs nuevos entraron sustituyendo chunks excedentes de docs sobre-representados.
    assert {"D", "E"}.issubset(_distinct_docs(results))


def test_search_monodoc_corpus_does_not_break():
    """Corpus de un solo documento: devuelve lo que hay, sin error ni relleno imposible."""
    pool = [(_FakeObj(f"a{i}", "docA", meta={"doc": "A"}), 0.9 - i * 0.01) for i in range(4)]
    results = _store(pool).search("consulta")
    assert _distinct_docs(results) == {"A"}
    assert len(results) == 4


def test_search_never_introduces_below_threshold():
    """El relleno solo usa candidatos del pool (ya filtrado por umbral)."""
    pool = [
        (_FakeObj("a1", "docA", meta={"doc": "A"}), 0.95),
        (_FakeObj("a2", "docA", meta={"doc": "A"}), 0.94),
        (_FakeObj("b1", "docB", meta={"doc": "B"}), 0.90),
        (_FakeObj("d1", "docD", meta={"doc": "D"}), 0.80),
    ]
    results = _store(pool).search("consulta")
    ids_validos = {"a1", "a2", "b1", "d1"}
    assert all(r.chunk_id in ids_validos for r in results)


def test_web_chunks_count_as_distinct_by_url():
    """Chunks web (sin documento_id) cuentan como fuentes distintas por su URL."""
    pool = [
        (_FakeObj("w1", None, "http://x.com/1", tipo="web", meta={"doc": "w1"}), 0.9),
        (_FakeObj("w2", None, "http://x.com/2", tipo="web", meta={"doc": "w2"}), 0.88),
        (_FakeObj("w3", None, "http://x.com/3", tipo="web", meta={"doc": "w3"}), 0.86),
    ]
    store = PGVectorStore(_FakeEmbedder(), _FakeRepo(pool), _settings(rag_top_k=3))
    results = store.search("consulta")
    # 3 URLs distintas → 3 fuentes; el piso de diversidad no las colapsa ni las descarta.
    assert len({r.fuente_url for r in results}) == 3


def test_enforce_doc_diversity_preserves_length_and_reserves():
    """El método puro: sustituye desde el final (protege reservas al frente), conserva len y k."""
    store = _store([])  # pool no usado en la llamada directa
    rows = [
        (_FakeObj("r1", "RESERVA"), 0.99),  # reserva antepuesta — no debe salir
        (_FakeObj("a1", "docA"), 0.95),
        (_FakeObj("a2", "docA"), 0.94),
        (_FakeObj("a3", "docA"), 0.93),
    ]
    pool = rows + [
        (_FakeObj("b1", "docB"), 0.80),
        (_FakeObj("c1", "docC"), 0.78),
        (_FakeObj("d1", "docD"), 0.76),
    ]
    out = store._enforce_doc_diversity(rows, pool, k=4, min_docs=4)
    keys = [o.documento_id for o, _ in out]
    assert len(out) == 4
    assert "RESERVA" in keys  # la reserva sobrevive (está al frente)
    assert len(set(keys)) >= 4  # se alcanzó el piso de diversidad
