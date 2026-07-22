from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from ic.data.models.retrieval_cache import RetrievalCache


def _make_hash(connector: str, query: str, max_results: int) -> str:
    key = f"{connector}:{max_results}:{query}"
    return hashlib.sha256(key.encode()).hexdigest()


class RetrievalCacheRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_fresh(self, connector: str, query: str, max_results: int) -> list | None:
        """Devuelve el payload cacheado si existe y no ha expirado; None en otro caso."""
        qhash = _make_hash(connector, query, max_results)
        now = datetime.now(UTC)
        row = (
            self._db.query(RetrievalCache)
            .filter(RetrievalCache.query_hash == qhash, RetrievalCache.expires_at > now)
            .first()
        )
        return row.payload if row is not None else None

    def upsert(
        self,
        connector: str,
        query: str,
        max_results: int,
        payload: list,
        ttl_hours: int,
    ) -> None:
        """Inserta o actualiza la entrada de caché (upsert por query_hash)."""
        qhash = _make_hash(connector, query, max_results)
        now = datetime.now(UTC)
        expires = now + timedelta(hours=ttl_hours)
        row = (
            self._db.query(RetrievalCache)
            .filter(RetrievalCache.query_hash == qhash)
            .first()
        )
        if row is None:
            row = RetrievalCache(
                connector=connector,
                query_hash=qhash,
                query=query,
                payload=payload,
                expires_at=expires,
            )
            self._db.add(row)
        else:
            row.payload = payload
            row.expires_at = expires
            row.created_at = now
        self._db.commit()
