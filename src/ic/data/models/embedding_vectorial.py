import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base
from ic.shared.constants import FuenteTipo

_EMBED_DIM = 768  # nomic-embed-text:latest


class EmbeddingVectorial(Base):
    __tablename__ = "embeddings_vectoriales"
    __table_args__ = (
        CheckConstraint(
            f"fuente_tipo IN ({', '.join(repr(v.value) for v in FuenteTipo)})",
            name="ck_embed_fuente_tipo",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fuente_tipo: Mapped[str] = mapped_column(Text, nullable=False)
    fuente_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    documento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documentos_locales.id"), nullable=True
    )
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True
    )
    chunk_texto: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(_EMBED_DIM), nullable=False)
    metadatos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
