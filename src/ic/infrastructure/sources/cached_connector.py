"""Wrappers con caché para WebConnector y OpenAlexConnector (Fase 15, T15.2).

El caché opera por (connector_name, query, max_results) con TTL configurable en .env.
Los resultados se serializan como JSONB en la tabla retrieval_cache del esquema informes_ic.
Dependency Agnosticism: el repo vive en data/; este wrapper vive en infrastructure/.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict

from sqlalchemy.orm import Session

from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository
from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.config import Settings
from ic.shared.types import WebResult

logger = logging.getLogger(__name__)


class CacheCounter:
    """Contador thread-safe de hits/misses de caché (T17.1, DT-026).

    Compartido entre las múltiples instancias de Cached*Connector que el pipeline
    crea por-thread (generate_n1 corre Caps 2/3/4 en paralelo). El Lock garantiza
    la agregación correcta cross-thread.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def hit(self) -> None:
        with self._lock:
            self.hits += 1

    def miss(self) -> None:
        with self._lock:
            self.misses += 1


def _to_payload(results: list[WebResult]) -> list[dict]:
    return [asdict(r) for r in results]


def _from_payload(payload: list[dict]) -> list[WebResult]:
    return [WebResult(**item) for item in payload]


class CachedWebConnector:
    """WebConnector con caché de resultados por (query, max_results, TTL)."""

    def __init__(
        self,
        connector: WebConnector,
        db: Session,
        settings: Settings,
        counter: CacheCounter | None = None,
    ) -> None:
        self._connector = connector
        self._repo = RetrievalCacheRepository(db)
        self._ttl = settings.retrieval_cache_ttl_hours
        self._counter = counter
        self.hits = 0
        self.misses = 0

    def _hit(self) -> None:
        self.hits += 1
        if self._counter is not None:
            self._counter.hit()

    def _miss(self) -> None:
        self.misses += 1
        if self._counter is not None:
            self._counter.miss()

    def search(
        self,
        query: str,
        max_results: int = 5,
        force_ddg: bool = False,
        search_depth: str = "basic",
    ) -> list[WebResult]:
        # La profundidad de búsqueda cambia el contenido devuelto: se incorpora a la
        # clave de caché solo cuando no es "basic", para no invalidar las claves ya
        # cacheadas de las búsquedas básicas.
        cache_query = query if search_depth == "basic" else f"{query} [depth={search_depth}]"
        if not force_ddg:
            cached = self._repo.get_fresh("web", cache_query, max_results)
            if cached is not None:
                logger.debug("Cache HIT web: %r", cache_query[:60])
                self._hit()
                return _from_payload(cached)
            self._miss()

        results = self._connector.search(
            query, max_results=max_results, force_ddg=force_ddg, search_depth=search_depth
        )
        if results and not force_ddg:
            self._repo.upsert("web", cache_query, max_results, _to_payload(results), self._ttl)
        return results

    def extract_ciiu(self, results: list[WebResult]) -> str | None:
        return self._connector.extract_ciiu(results)


class CachedOpenAlexConnector:
    """OpenAlexConnector con caché de resultados por (query, max_results, TTL)."""

    def __init__(
        self,
        connector: OpenAlexConnector,
        db: Session,
        settings: Settings,
        counter: CacheCounter | None = None,
    ) -> None:
        self._connector = connector
        self._repo = RetrievalCacheRepository(db)
        self._ttl = settings.retrieval_cache_ttl_hours
        self._counter = counter
        self.hits = 0
        self.misses = 0

    def _hit(self) -> None:
        self.hits += 1
        if self._counter is not None:
            self._counter.hit()

    def _miss(self) -> None:
        self.misses += 1
        if self._counter is not None:
            self._counter.miss()

    def search(self, query: str, max_results: int = 5) -> list[WebResult]:
        cached = self._repo.get_fresh("openalex", query, max_results)
        if cached is not None:
            logger.debug("Cache HIT openalex: %r", query[:60])
            self._hit()
            return _from_payload(cached)
        self._miss()

        results = self._connector.search(query, max_results=max_results)
        if results:
            self._repo.upsert("openalex", query, max_results, _to_payload(results), self._ttl)
        return results
