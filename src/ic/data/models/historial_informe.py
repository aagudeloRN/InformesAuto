import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base
from ic.shared.constants import EstadoInforme


class HistorialInforme(Base):
    __tablename__ = "historial_informes"
    __table_args__ = (
        CheckConstraint(
            f"estado IN ({', '.join(repr(v.value) for v in EstadoInforme)})",
            name="ck_historial_estado",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False
    )
    estado: Mapped[str] = mapped_column(Text, nullable=False, default=EstadoInforme.PENDIENTE)
    costo_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    tiempo_generacion_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    parametros_entrada: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ruta_documento_final: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
