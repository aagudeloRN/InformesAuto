"""Trazabilidad del loop de auto-revisión (DT-059/T4) — historial por capítulo (TIER 4).

Una fila por corrida-y-capítulo revisado: score inicial/final, nº de iteraciones, iteración
ganadora, motivo de parada, dimensiones y faltantes de la mejor versión. Permite auditar la
mejora que aportó el loop (Δ score, cuántos caps mejoran) sin re-ejecutar.

Vive en el esquema propio del proyecto (TIER 1 regla 3). Migración idempotente estilo
``ensure_*`` (ver ``checkpoint.ensure_checkpoint_table``, ``entidad.ensure_entidades_tables``).
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base


class RevisionCapitulo(Base):
    __tablename__ = "revisiones_capitulo"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_key: Mapped[str] = mapped_column(Text, nullable=False)
    capitulo: Mapped[str] = mapped_column(Text, nullable=False)
    sabor: Mapped[str] = mapped_column(Text, nullable=False)  # web | integracion
    n_iteraciones: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    iter_ganadora: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_inicial: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_final: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    motivo_parada: Mapped[str] = mapped_column(Text, nullable=False)
    dimensiones: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    faltantes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def ensure_revisiones_tables(engine) -> None:  # type: ignore[no-untyped-def]
    """Crea la tabla de trazabilidad de revisiones si no existe (idempotente)."""
    from ic.shared.config import get_settings

    schema = get_settings().db_schema
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {schema}.revisiones_capitulo ("
                " id BIGSERIAL PRIMARY KEY,"
                " run_key TEXT NOT NULL,"
                " capitulo TEXT NOT NULL,"
                " sabor TEXT NOT NULL,"
                " n_iteraciones INTEGER NOT NULL DEFAULT 0,"
                " iter_ganadora INTEGER NOT NULL DEFAULT 0,"
                " score_inicial INTEGER NOT NULL DEFAULT 0,"
                " score_final INTEGER NOT NULL DEFAULT 0,"
                " motivo_parada TEXT NOT NULL,"
                " dimensiones JSONB,"
                " faltantes JSONB,"
                " created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
                ")"
            )
        )
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_revision_runkey "
                f"ON {schema}.revisiones_capitulo (run_key)"
            )
        )
