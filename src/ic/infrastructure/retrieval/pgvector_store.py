import uuid

from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval import chunker as chunker_mod
from ic.infrastructure.retrieval.embedder import Embedder
from ic.shared.config import Settings
from ic.shared.types import ChunkResult


class PGVectorStore:
    def __init__(self, embedder: Embedder, repo: EmbeddingRepository, settings: Settings) -> None:
        self._embedder = embedder
        self._repo = repo
        self._top_k = settings.rag_top_k
        self._threshold = settings.rag_similarity_threshold

    def ingest(
        self,
        texts: list[str],
        fuente_tipo: str,
        urls: list[str | None],
        empresa_id: uuid.UUID | None = None,
        metadatos_extra: list[dict] | None = None,
    ) -> int:
        chunks: list[str] = []
        chunk_urls: list[str | None] = []
        chunk_meta: list[dict | None] = []

        for i, text in enumerate(texts):
            split = chunker_mod.chunk_text(text)
            url = urls[i] if i < len(urls) else None
            meta = metadatos_extra[i] if metadatos_extra and i < len(metadatos_extra) else None
            for _ in split:
                chunks.append(_)
                chunk_urls.append(url)
                chunk_meta.append(meta)

        if not chunks:
            return 0

        embeddings = self._embedder.embed_many(chunks)

        orm_objects = [
            EmbeddingVectorial(
                fuente_tipo=fuente_tipo,
                fuente_url=chunk_urls[i],
                empresa_id=empresa_id,
                chunk_texto=chunks[i],
                chunk_index=i,
                embedding=embeddings[i],
                metadatos=chunk_meta[i],
            )
            for i in range(len(chunks))
        ]

        self._repo.insert_many(orm_objects)
        return len(orm_objects)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        empresa_id: uuid.UUID | None = None,
    ) -> list[ChunkResult]:
        k = top_k if top_k is not None else self._top_k
        t = threshold if threshold is not None else self._threshold

        query_vec = self._embedder.embed(query)
        rows = self._repo.search_similar(query_vec, k, t, empresa_id)

        return [
            ChunkResult(
                chunk_texto=obj.chunk_texto,
                fuente_tipo=obj.fuente_tipo,
                fuente_url=obj.fuente_url,
                score=score,
                metadatos=obj.metadatos,
            )
            for obj, score in rows
        ]
