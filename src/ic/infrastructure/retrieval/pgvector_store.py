import uuid

from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval import chunker as chunker_mod
from ic.infrastructure.retrieval.embedder import Embedder
from ic.shared.config import Settings
from ic.shared.types import ChunkResult

# Fase 22 (DT-049): factor de ampliación del pool base para poder rellenar la garantía de
# diversidad. Se piden más candidatos de los que caben en top_k; el excedente (ya filtrado por
# umbral y diversificado por MMR) sirve para sustituir chunks de documentos sobre-representados.
_DIVERSITY_POOL_MULT = 3


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
        # Piso de diversidad de documentos (Fase 22, DT-049): mínimo de docs distintos que
        # search() intenta devolver cuando el corpus los tiene.
        self._min_distinct_docs = getattr(settings, "rag_min_distinct_docs", 5)
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
        fuente_tipo_filter: str | None = None,
    ) -> list[ChunkResult]:
        k = top_k if top_k is not None else self._top_k
        t = threshold if threshold is not None else self._threshold

        query_vec = self._embedder.embed(query)
        # Pool ampliado (Fase 22, DT-049): se piden más candidatos que top_k para poder rellenar
        # la garantía de diversidad. El slice [:k] preserva el comportamiento previo como base;
        # el resto del pool alimenta la sustitución por documentos no representados.
        pool_k = max(k, k * _DIVERSITY_POOL_MULT) if self._min_distinct_docs > 0 else k
        pool = self._repo.search_similar(
            query_vec,
            pool_k,
            t,
            empresa_id,
            sector_gics=sector_gics,
            solo_activos=solo_activos,
            max_chunks_per_doc=self._max_chunks_per_doc,
            mmr_lambda=self._mmr_lambda,
            fuente_tipo_filter=fuente_tipo_filter,
        )
        rows = pool[:k]

        # Prioridad final: empresa > sector > global > resto por score.
        # Cada capa se recupera en búsqueda estricta y se antepone a las capas de menor
        # prioridad, eliminando duplicados. Esto garantiza que la evidencia más relevante
        # para el informe aflore pese al volumen de chunks web genéricos (ADR-012 addendum).
        t_reserve = min(t, self._sector_reserve_threshold)

        # Capa 1 — corpus sectorial estricto (ADR-012)
        capa_sectorial: list[tuple] = []
        if sector_gics is not None and self._sector_reserve > 0:
            capa_sectorial = self._repo.search_similar(
                query_vec,
                self._sector_reserve,
                t_reserve,
                empresa_id,
                sector_gics=sector_gics,
                solo_activos=solo_activos,
                sector_estricto=True,
                fuente_tipo_filter=fuente_tipo_filter,
            )

        # Capa 2 — docs globales cross-sector (Fase 18, DT-031)
        capa_global: list[tuple] = []
        if self._global_reserve > 0:
            capa_global = self._repo.search_similar(
                query_vec,
                self._global_reserve,
                t_reserve,
                None,
                solo_activos=solo_activos,
                global_estricto=True,
                fuente_tipo_filter=fuente_tipo_filter,
            )

        # Capa 3 — docs de la empresa específica del informe (Fase 18, T18.3)
        capa_empresa: list[tuple] = []
        if empresa_id is not None and self._empresa_reserve > 0:
            capa_empresa = self._repo.search_similar(
                query_vec,
                self._empresa_reserve,
                t_reserve,
                empresa_id,
                solo_activos=solo_activos,
                empresa_estricto=True,
                fuente_tipo_filter=fuente_tipo_filter,
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

        # Garantía de diversidad (Fase 22, DT-049): si el resultado concentra pocos documentos,
        # sustituye chunks de docs sobre-representados por chunks de docs no representados del
        # pool ampliado. Preserva reservas (prepend al frente; la sustitución mira desde el final)
        # y no introduce chunks bajo umbral (el pool ya está filtrado).
        rows = self._enforce_doc_diversity(rows, pool, k, self._min_distinct_docs)

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

    @staticmethod
    def _doc_key(obj) -> object:
        """Clave de documento para contar diversidad y deduplicar Referencias.

        Alineada con `build_references_section`: un PDF se identifica por su `documento_id`;
        una fuente web (sin documento) por su `fuente_url`. Como último recurso, el id del chunk
        (garantiza que cada chunk sin doc ni url cuente como fuente distinta).
        """
        return getattr(obj, "documento_id", None) or getattr(obj, "fuente_url", None) or obj.id

    def _enforce_doc_diversity(
        self, rows: list[tuple], pool: list[tuple], k: int, min_docs: int
    ) -> list[tuple]:
        """Garantiza ≥`min_docs` documentos distintos en `rows` cuando `pool` los tiene.

        Sustituye los chunks de documentos sobre-representados (empezando por el final, para
        proteger las reservas antepuestas) por chunks de documentos aún no representados tomados
        del pool ampliado. Si queda hueco bajo `k` sin docs sobre-representados que sacrificar,
        los añade. Nunca baja de `len(rows)` chunks ni excede `k`; no introduce candidatos bajo
        umbral porque el pool ya viene filtrado por `search_similar`.
        """
        if min_docs <= 0 or not rows:
            return rows

        current_keys = {self._doc_key(o) for o, _ in rows}
        if len(current_keys) >= min_docs:
            return rows

        ids_in_rows = {o.id for o, _ in rows}
        missing = [
            (o, s)
            for o, s in pool
            if o.id not in ids_in_rows and self._doc_key(o) not in current_keys
        ]
        if not missing:
            return rows

        counts: dict = {}
        for o, _ in rows:
            key = self._doc_key(o)
            counts[key] = counts.get(key, 0) + 1

        result = list(rows)
        seen_keys = set(current_keys)
        for cand_obj, cand_score in missing:
            if len(seen_keys) >= min_docs:
                break
            cand_key = self._doc_key(cand_obj)
            if cand_key in seen_keys:  # otro chunk del mismo doc ya entró en esta pasada
                continue
            # Buscar desde el final un chunk de un documento con >1 representante para sustituir.
            swap_idx = None
            for i in range(len(result) - 1, -1, -1):
                if counts[self._doc_key(result[i][0])] > 1:
                    swap_idx = i
                    break
            if swap_idx is None:
                # Sin doc sobre-representado que sacrificar: añadir si aún cabe bajo k.
                if len(result) < k:
                    result.append((cand_obj, cand_score))
                    counts[cand_key] = counts.get(cand_key, 0) + 1
                    seen_keys.add(cand_key)
                    continue
                break
            removed_key = self._doc_key(result[swap_idx][0])
            result[swap_idx] = (cand_obj, cand_score)
            counts[removed_key] -= 1
            counts[cand_key] = counts.get(cand_key, 0) + 1
            seen_keys.add(cand_key)
        return result
