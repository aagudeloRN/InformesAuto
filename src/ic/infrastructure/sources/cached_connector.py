"""Wrappers con caché para WebConnector y OpenAlexConnector (Fase 15, T15.2).

El caché opera por (connector_name, query, max_results) con TTL configurable en .env.
Los resultados se serializan como JSONB en la tabla retrieval_cache del esquema informes_ic.
Dependency Agnosticism: el repo vive en data/; este wrapper vive en infrastructure/.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from sqlalchemy.orm import Session

from ic.data.repositories.retrieval_cache_repo import RetrievalCacheRepository
from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.config import Settings
from ic.shared.types import WebResult

logger = logging.getLogger(__name__)


def _to_payload(results: list[WebResult]) -> list[dict]:
    return [asdict(r) for r in results]


def _from_payload(payload: list[dict]) -> list[WebResult]:
    return [WebResult(**item) for item in payload]


class CachedWebConnector:
    """WebConnector con caché de resultados por (query, max_results, TTL)."""

    def __init__(self, connector: WebConnector, db: Session, settings: Settings) -> None:
        self._connector = connector
        self._repo = RetrievalCacheRepository(db)
        self._ttl = settings.retrieval_cache_ttl_hours

    def search(self, query: str, max_results: int = 5, force_ddg: bool = False) -> list[WebResult]:
        if not force_ddg:
            cached = self._repo.get_fresh("web", query, max_results)
            if cached is not None:
                logger.debug("Cache HIT web: %r", query[:60])
                return _from_payload(cached)

        results = self._connector.search(query, max_results=max_results, force_ddg=force_ddg)
        if results and not force_ddg:
            self._repo.upsert("web", query, max_results, _to_payload(results), self._ttl)
        return results

    def extract_ciiu(self, results: list[WebResult]) -> str | None:
        return self._connector.extract_ciiu(results)


class CachedOpenAlexConnector:
    """OpenAlexConnector con caché de resultados por (query, max_results, TTL)."""

    def __init__(self, connector: OpenAlexConnector, db: Session, settings: Settings) -> None:
        self._connector = connector
        self._repo = RetrievalCacheRepository(db)
        self._ttl = settings.retrieval_cache_ttl_hours

    def search(self, query: str, max_results: int = 5) -> list[WebResult]:
        cached = self._repo.get_fresh("openalex", query, max_results)
        if cached is not None:
            logger.debug("Cache HIT openalex: %r", query[:60])
            return _from_payload(cached)

        results = self._connector.search(query, max_results=max_results)
        if results:
            self._repo.upsert("openalex", query, max_results, _to_payload(results), self._ttl)
        return results
