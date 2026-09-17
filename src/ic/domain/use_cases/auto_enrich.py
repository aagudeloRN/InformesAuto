"""Caso de uso para enriquecimiento automático de sectores con baja evidencia (Spec 008 / US2)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ic.data.database import SessionLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.enrichment_connector import EnrichmentConnector
from ic.shared.config import Settings
from ic.shared.constants import FuenteTipo

if TYPE_CHECKING:
    from ic.shared.types import Embedder

logger = logging.getLogger("auto_enrich")


class AutoEnrich:
    """Caso de uso de auto-enriquecimiento para sectores con bajo retrieval score."""

    def __init__(
        self,
        settings: Settings,
        embedder: Embedder | None = None,
    ) -> None:
        self.settings = settings
        self._embedder = embedder
        self.connector = EnrichmentConnector(settings)

    def search_scores(self, sector_gics: str, query_text: str, top_k: int = 5) -> list[float]:
        """Obtiene los scores de similitud existentes en el índice vectorial."""
        try:
            with SessionLocal() as db:
                repo = EmbeddingRepository(db)
                if self._embedder:
                    store = PGVectorStore(self._embedder, repo, self.settings)
                    results = store.search(query_text, top_k=top_k, sector_gics=sector_gics)
                    return [r.score for r in results]
                return []
        except Exception as exc:
            logger.warning("Error al consultar scores vectoriales previos: %s", exc)
            return []

    def try_enrich(
        self,
        sector_gics: str,
        query_text: str,
        threshold: float = 0.5,
    ) -> bool:
        """Verifica si la evidencia es baja (< threshold) y enriquece con fuentes secundarias.

        Retorna True si se enriqueció el índice con al menos 1 nuevo fragmento.
        """
        try:
            scores = self.search_scores(sector_gics, query_text)
            max_score = max(scores, default=0.0)

            if max_score >= threshold:
                logger.info(
                    "Evidencia suficiente sector %s (score %.2f >= %.2f). No enriquece.",
                    sector_gics,
                    max_score,
                    threshold,
                )
                return False

            logger.info(
                "Baja evidencia en sector %s (score %.2f < %.2f). Buscando fuentes...",
                sector_gics,
                max_score,
                threshold,
            )

            fragmentos = self.connector.fetch_fragments(query_text, sector_gics)
            if not fragmentos:
                logger.warning(
                    "No se obtuvieron fragmentos adicionales para sector %s", sector_gics
                )
                return False

            chunks: list[EmbeddingVectorial] = []
            for i, frag in enumerate(fragmentos):
                vec = self._embedder.embed(frag.texto) if self._embedder else [0.0] * 768
                fuente_tipo = (
                    FuenteTipo.OPENALEX.value if frag.fuente == "openalex" else FuenteTipo.WEB.value
                )
                metadatos = {
                    "fuente": frag.fuente,
                    "titulo": frag.titulo,
                    "autor": frag.autores,
                    "año": frag.año,
                    "url": frag.url,
                    "sector_gics": frag.sector_gics,
                    "idioma": frag.idioma,
                }
                chunks.append(
                    EmbeddingVectorial(
                        fuente_tipo=fuente_tipo,
                        fuente_url=frag.url,
                        chunk_texto=frag.texto,
                        chunk_index=i,
                        embedding=vec,
                        metadatos=metadatos,
                    )
                )

            with SessionLocal() as db:
                repo = EmbeddingRepository(db)
                repo.insert_many(chunks)

            logger.info(
                "Enriquecimiento exitoso sector %s: %d fragmentos guardados",
                sector_gics,
                len(chunks),
            )
            return len(chunks) > 0
        except Exception as exc:
            logger.warning(
                "Degradación elegante: Error durante auto-enriquecimiento de sector %s: %s",
                sector_gics,
                exc,
            )
            return False
