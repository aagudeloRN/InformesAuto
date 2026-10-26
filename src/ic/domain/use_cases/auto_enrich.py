"""Caso de uso para enriquecimiento automático de sectores con baja evidencia (Spec 008 / US2)."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from ic.data.database import SessionLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.repositories.embedding_estado_repo import EmbeddingEstadoRepository
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.enrichment_connector import EnrichmentConnector
from ic.shared.config import Settings
from ic.shared.constants import FuenteTipo

if TYPE_CHECKING:
    from ic.shared.types import Embedder

logger = logging.getLogger("auto_enrich")

SUFICIENTE = "suficiente"
ENRIQUECIDO = "enriquecido"
YA_EXISTENTES = "ya_existentes"
SIN_EVIDENCIA = "sin_evidencia"
FALLIDO = "fallido"

# Gate RN-001 (FR-014): OpenAlex trae metadatos revisados por pares → verificado de origen;
# la web queda como candidato y el retrieval no la cita hasta corroborarla (FR-015).
VERIFICADO = "verificado"
CANDIDATO = "candidato"


@dataclass
class EventoEnriquecimiento:
    """Resultado trazable de un intento de enriquecimiento (se persiste en métricas)."""

    sector: str
    score_previo: float
    resultado: str
    fuentes: list[str] = field(default_factory=list)
    n_fragmentos: int = 0
    n_promovidos: int = 0
    error: str | None = None

    @property
    def enriquecido(self) -> bool:
        return self.resultado == ENRIQUECIDO

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256_text(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


class AutoEnrich:
    """Caso de uso de auto-enriquecimiento para sectores con bajo retrieval score."""

    def __init__(self, settings: Settings, embedder: Embedder) -> None:
        self.settings = settings
        self._embedder = embedder
        self.connector = EnrichmentConnector(settings)

    def search_scores(self, sector_gics: str, query_text: str, top_k: int = 5) -> list[float]:
        """Obtiene los scores de similitud existentes en el índice vectorial."""
        try:
            with SessionLocal() as db:
                repo = EmbeddingRepository(db)
                store = PGVectorStore(self._embedder, repo, self.settings)
                results = store.search(query_text, top_k=top_k, sector_gics=sector_gics)
                return [r.score for r in results]
        except Exception as exc:
            logger.warning("Error al consultar scores vectoriales previos: %s", exc)
            return []

    def try_enrich(
        self,
        sector_gics: str,
        query_text: str,
        threshold: float = 0.5,
    ) -> EventoEnriquecimiento:
        """Verifica si la evidencia es baja (< threshold) y enriquece con fuentes secundarias.

        Devuelve un evento; ``evento.enriquecido`` es True si se guardó al menos 1 fragmento nuevo.
        """
        evento = EventoEnriquecimiento(sector=sector_gics, score_previo=0.0, resultado=FALLIDO)
        try:
            scores = self.search_scores(sector_gics, query_text)
            evento.score_previo = max(scores, default=0.0)

            if evento.score_previo >= threshold:
                logger.info(
                    "Evidencia suficiente sector %s (score %.2f >= %.2f). No enriquece.",
                    sector_gics,
                    evento.score_previo,
                    threshold,
                )
                evento.resultado = SUFICIENTE
                return evento

            logger.info(
                "Baja evidencia en sector %s (score %.2f < %.2f). Buscando fuentes...",
                sector_gics,
                evento.score_previo,
                threshold,
            )

            fragmentos = self.connector.fetch_fragments(query_text, sector_gics)
            evento.fuentes = sorted({f.fuente for f in fragmentos})
            if not fragmentos:
                logger.warning(
                    "No se obtuvieron fragmentos adicionales para sector %s", sector_gics
                )
                evento.resultado = SIN_EVIDENCIA
                return evento

            chunks = self._build_new_chunks(fragmentos)
            if not chunks:
                logger.info("Sector %s: todos los fragmentos ya estaban en el índice", sector_gics)
                evento.resultado = YA_EXISTENTES
                return evento

            candidatos = [
                (c.id, c.embedding)
                for c in chunks
                if c.metadatos["estado_verificacion"] == CANDIDATO
            ]
            with SessionLocal() as db:
                EmbeddingRepository(db).insert_many(chunks)

            evento.n_fragmentos = len(chunks)
            evento.n_promovidos = self._promover_respaldados(sector_gics, candidatos)
            evento.resultado = ENRIQUECIDO
            logger.info(
                "Enriquecimiento exitoso sector %s: %d fragmentos guardados",
                sector_gics,
                len(chunks),
            )
            return evento
        except Exception as exc:
            logger.warning(
                "Degradación elegante: Error durante auto-enriquecimiento de sector %s: %s",
                sector_gics,
                exc,
            )
            evento.resultado = FALLIDO
            evento.error = str(exc)
            return evento

    def _promover_respaldados(self, sector_gics: str, candidatos: list) -> int:
        """Vía A (FR-015): un candidato pasa a verificado si un chunk citable del mismo sector lo
        respalda con similitud ≥ ``rag_similarity_threshold``; si falla, queda para revisión.
        """
        if not candidatos:
            return 0
        umbral = getattr(self.settings, "rag_similarity_threshold", 0.6)
        promovidos = 0
        try:
            with SessionLocal() as db:
                repo, estados = EmbeddingRepository(db), EmbeddingEstadoRepository(db)
                for chunk_id, embedding in candidatos:
                    respaldo = repo.search_similar(
                        embedding, 1, umbral, sector_gics=sector_gics, sector_estricto=True
                    )
                    if respaldo and estados.set_estado_verificacion(chunk_id, VERIFICADO):
                        promovidos += 1
        except Exception as exc:
            logger.warning("Promoción automática omitida en sector %s: %s", sector_gics, exc)
        return promovidos

    def _build_new_chunks(self, fragmentos: list) -> list[EmbeddingVectorial]:
        """Construye los chunks omitiendo los ya indexados o repetidos dentro del lote (FR-013)."""
        vistos: set[str] = set()
        chunks: list[EmbeddingVectorial] = []
        with SessionLocal() as db:
            repo = EmbeddingRepository(db)
            for frag in fragmentos:
                sha = _sha256_text(frag.texto)
                if sha in vistos or repo.exists_by_sha256(sha):
                    continue
                vistos.add(sha)
                fuente_tipo = (
                    FuenteTipo.OPENALEX.value if frag.fuente == "openalex" else FuenteTipo.WEB.value
                )
                chunks.append(
                    EmbeddingVectorial(
                        id=uuid.uuid4(),
                        fuente_tipo=fuente_tipo,
                        fuente_url=frag.url,
                        chunk_texto=frag.texto,
                        chunk_index=len(chunks),
                        embedding=self._embedder.embed(frag.texto),
                        metadatos={
                            "fuente": frag.fuente,
                            "titulo": frag.titulo,
                            "autor": frag.autores,
                            "año": frag.año,
                            "url": frag.url,
                            "sector_gics": frag.sector_gics,
                            "idioma": frag.idioma,
                            "chunk_sha256": sha,
                            "estado_verificacion": (
                                VERIFICADO if frag.fuente == "openalex" else CANDIDATO
                            ),
                        },
                    )
                )
        return chunks
