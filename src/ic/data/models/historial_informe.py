import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
    text,
)
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
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ruta_documento_final: Mapped[str | None] = mapped_column(Text, nullable=True)
    metricas_fiabilidad: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def ensure_historial_columns(engine) -> None:
    """Migración idempotente: agrega columnas nuevas si no existen."""
    from ic.shared.config import get_settings
    schema = get_settings().db_schema
    with engine.begin() as conn:
        for col, tipo in [
            ("tokens_in", "INTEGER"),
            ("tokens_out", "INTEGER"),
            ("metricas_fiabilidad", "JSONB"),
        ]:
            conn.execute(text(
                f"ALTER TABLE {schema}.historial_informes ADD COLUMN IF NOT EXISTS {col} {tipo}"
            ))
