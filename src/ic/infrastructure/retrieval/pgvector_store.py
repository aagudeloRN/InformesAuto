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
        self._max_chunks_per_doc = getattr(settings, "rag_max_chunks_per_doc", 4)
        self._sector_reserve = getattr(settings, "rag_sector_reserve", 3)
        self._sector_reserve_threshold = getattr(settings, "rag_sector_reserve_threshold", 0.5)
        self._global_reserve = getattr(settings, "rag_global_reserve", 2)
        self._empresa_reserve = getattr(settings, "rag_empresa_reserve", 2)
        self._mmr_lambda = getattr(settings, "rag_mmr_lambda", 0.7)
        # Sesión de la corrida (T14.5): marca los chunks web para promover solo lo citado.
        self.session_id: str | None = None

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

        # Chunks web: se etiquetan con la sesión de la corrida para promover solo lo citado
        # al ensamblar (T14.5, DT-020). Otras fuentes no llevan session_id.
        stamp_session = self.session_id if fuente_tipo == "web" else None

        for i, text in enumerate(texts):
            split = chunker_mod.chunk_text(text)
            url = urls[i] if i < len(urls) else None
            meta = metadatos_extra[i] if metadatos_extra and i < len(metadatos_extra) else None
            if stamp_session:
                meta = {**(meta or {}), "session_id": stamp_session}
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
        sector_gics: str | None = None,
        solo_activos: bool = True,
    ) -> list[ChunkResult]:
        k = top_k if top_k is not None else self._top_k
        t = threshold if threshold is not None else self._threshold

        query_vec = self._embedder.embed(query)
        rows = self._repo.search_similar(
            query_vec, k, t, empresa_id,
            sector_gics=sector_gics,
            solo_activos=solo_activos,
            max_chunks_per_doc=self._max_chunks_per_doc,
            mmr_lambda=self._mmr_lambda,
        )

        # Prioridad final: empresa > sector > global > resto por score.
        # Cada capa se recupera en búsqueda estricta y se antepone a las capas de menor
        # prioridad, eliminando duplicados. Esto garantiza que la evidencia más relevante
        # para el informe aflore pese al volumen de chunks web genéricos (ADR-012 addendum).
        t_reserve = min(t, self._sector_reserve_threshold)

        # Capa 1 — corpus sectorial estricto (ADR-012)
        capa_sectorial: list[tuple] = []
        if sector_gics is not None and self._sector_reserve > 0:
            capa_sectorial = self._repo.search_similar(
                query_vec, self._sector_reserve, t_reserve, empresa_id,
                sector_gics=sector_gics,
                solo_activos=solo_activos,
                sector_estricto=True,
            )

        # Capa 2 — docs globales cross-sector (Fase 18, DT-031)
        capa_global: list[tuple] = []
        if self._global_reserve > 0:
            capa_global = self._repo.search_similar(
                query_vec, self._global_reserve, t_reserve, None,
                solo_activos=solo_activos,
                global_estricto=True,
            )

        # Capa 3 — docs de la empresa específica del informe (Fase 18, T18.3)
        capa_empresa: list[tuple] = []
        if empresa_id is not None and self._empresa_reserve > 0:
            capa_empresa = self._repo.search_similar(
                query_vec, self._empresa_reserve, t_reserve, empresa_id,
                solo_activos=solo_activos,
                empresa_estricto=True,
            )

        # Ensamblar en orden de prioridad decreciente: empresa > sector > global > resto.
        # Se construye de mayor a menor prioridad: cada nivel de mayor prioridad se antepone
        # al acumulado anterior, deduplicando por id.
        def _prepend(priority: list[tuple], base: list[tuple], limit: int) -> list[tuple]:
            seen = {obj.id for obj, _ in priority}
            return (priority + [(obj, sc) for obj, sc in base if obj.id not in seen])[:limit]

        # Orden de construcción: primero el "fondo" (resto por score), luego se anteponen
        # en orden inverso de prioridad (global → sector → empresa).
        rows = _prepend(capa_global, rows, k)
        rows = _prepend(capa_sectorial, rows, k)
        rows = _prepend(capa_empresa, rows, k)

        return [
            ChunkResult(
                chunk_texto=obj.chunk_texto,
                fuente_tipo=obj.fuente_tipo,
                fuente_url=obj.fuente_url,
                score=score,
                metadatos=obj.metadatos,
                chunk_id=str(obj.id) if obj.id is not None else None,
            )
            for obj, score in rows
        ]
