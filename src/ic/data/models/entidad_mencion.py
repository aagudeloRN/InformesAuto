"""Menciones de entidades extraídas por NER sobre el `chunk_texto` ya almacenado (DT-057/T3).

Sustrato del KB de entidades (DT-056): cada fila es una mención de entidad DETECTADA en un chunk,
con procedencia (documento, chunk, sector, tipo de fuente, fecha) y estado **candidato**. RN-001:
el NER no fabrica — solo registra entidades presentes en el texto; nunca se reusa como hecho sin
verificación (el merge/verificación del KB es DT-056, no esta tabla).

Migración idempotente estilo ``ensure_*`` (ver checkpoint.ensure_checkpoint_table). Vive en el
esquema propio del proyecto (TIER 1 regla 3).
"""

from datetime import datetime

from sqlalchemy import DateTime, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base

# Estado inicial de toda mención: extraída pero sin verificar (gate anti-envenenamiento, RN-001).
ESTADO_CANDIDATO = "candidato"


class EntidadMencion(Base):
    __tablename__ = "entidad_menciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Clave de dedup: nombre normalizado + chunk de origen (una mención por entidad/chunk).
    entidad_normalizada: Mapped[str] = mapped_column(Text, nullable=False)
    entidad_texto: Mapped[str] = mapped_column(Text, nullable=False)  # forma superficial hallada
    tipo: Mapped[str] = mapped_column(Text, nullable=False)  # etiqueta NER (ORG/MISC/…)
    # Procedencia (provenance)
    documento_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    chunk_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    sector: Mapped[str | None] = mapped_column(Text, nullable=True)
    fuente_tipo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default=ESTADO_CANDIDATO)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def ensure_entidad_menciones_table(engine) -> None:
    """Crea la tabla de menciones si no existe (idempotente), con índice único de dedup."""
    from ic.shared.config import get_settings

    schema = get_settings().db_schema
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {schema}.entidad_menciones ("
                " id BIGSERIAL PRIMARY KEY,"
                " entidad_normalizada TEXT NOT NULL,"
                " entidad_texto TEXT NOT NULL,"
                " tipo TEXT NOT NULL,"
                " documento_id UUID,"
                " chunk_id UUID NOT NULL,"
                " sector TEXT,"
                " fuente_tipo TEXT,"
                " estado TEXT NOT NULL DEFAULT 'candidato',"
                " created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
                ")"
            )
        )
        # Dedup idempotente: una mención por (entidad_normalizada, chunk_id).
        conn.execute(
            text(
                f"CREATE UNIQUE INDEX IF NOT EXISTS ux_entidad_mencion_dedup "
                f"ON {schema}.entidad_menciones (entidad_normalizada, chunk_id)"
            )
        )
        # Acelera consultas por sector del KB (DT-056).
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_entidad_mencion_sector "
                f"ON {schema}.entidad_menciones (sector)"
            )
        )
