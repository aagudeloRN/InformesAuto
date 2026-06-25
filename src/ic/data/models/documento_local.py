import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base
from ic.shared.constants import EstadoIngesta, TipoDocumento


class DocumentoLocal(Base):
    __tablename__ = "documentos_locales"
    __table_args__ = (
        CheckConstraint(
            f"tipo IN ({', '.join(repr(v.value) for v in TipoDocumento)})",
            name="ck_doc_tipo",
        ),
        CheckConstraint(
            f"estado_ingesta IN ({', '.join(repr(v.value) for v in EstadoIngesta)})",
            name="ck_doc_estado_ingesta",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True
    )
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, default=TipoDocumento.OTRO)
    estado_ingesta: Mapped[str] = mapped_column(
        Text, nullable=False, default=EstadoIngesta.PENDIENTE
    )
    metadatos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
