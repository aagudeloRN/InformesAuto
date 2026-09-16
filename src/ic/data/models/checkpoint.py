"""Checkpoint de capítulos para reanudar corridas interrumpidas (T22.3, DT-030).

Persiste el estado serializado de cada capítulo N0/N1/N2 a medida que se genera,
de modo que una corrida interrumpida pueda reanudarse con --resume sin recomputar lo
ya hecho. Vive en el esquema propio del proyecto; migración idempotente estilo
``ensure_*`` (ver historial_informe.ensure_historial_columns).
"""

from datetime import datetime

from sqlalchemy import DateTime, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base


class CheckpointCapitulo(Base):
    __tablename__ = "checkpoint_capitulos"

    run_key: Mapped[str] = mapped_column(Text, primary_key=True)
    cap_nombre: Mapped[str] = mapped_column(Text, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def ensure_checkpoint_table(engine) -> None:
    """Crea la tabla de checkpoint si no existe (idempotente)."""
    from ic.shared.config import get_settings

    schema = get_settings().db_schema
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {schema}.checkpoint_capitulos ("
                " run_key TEXT NOT NULL,"
                " cap_nombre TEXT NOT NULL,"
                " payload JSONB NOT NULL,"
                " created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
                " PRIMARY KEY (run_key, cap_nombre)"
                ")"
            )
        )
