from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base


class RetrievalCache(Base):
    """Caché de resultados web/OpenAlex por (connector, query_hash, ttl). T15.2."""

    __tablename__ = "retrieval_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector: Mapped[str] = mapped_column(String(32), nullable=False)  # "web" | "openalex"
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def ensure_retrieval_cache_table(engine) -> None:  # type: ignore[type-arg]
    """Crea la tabla retrieval_cache si no existe (idempotente)."""
    RetrievalCache.__table__.create(engine, checkfirst=True)
