"""KB de entidades canónicas (DT-056) — consolidación del sustrato `entidad_menciones`.

Cada `Entidad` es una entidad de negocio canónica (empresa, competidor, oportunidad, evento)
deduplicada, con estado **candidato/verificado** (gate anti-envenenamiento RN-001: un dato mal
extraído NO se reusa como hecho). Sus atributos viven en `EntidadAtributo`, **uno por fila con su
procedencia** (fuente, confianza, documento) para poder priorizar en conflicto
(usuario > emis/db_oficial > web) sin borrar el lineage.

Clave de dedup: `nit` cuando existe (empresas colombianas); si no, `(nombre_normalizado,
sector_gics)`. La reconciliación por NIT/ciudad con la base DT-050 es un gancho futuro; hoy el
sustrato es ORG-only sin NIT → se consolida por nombre normalizado + captura de alias (variantes
superficiales del mismo nombre).

Migraciones idempotentes estilo ``ensure_*`` (ver ``entidad_mencion``, ``ensure_*_table``).
Viven en el esquema propio del proyecto (TIER 1 regla 3).
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ic.data.models.base import Base

# Estados del gate anti-envenenamiento (RN-001).
ESTADO_CANDIDATO = "candidato"  # extraído/sin verificar (web, NER)
ESTADO_VERIFICADO = "verificado"  # fuente curada o aprobado por humano
ESTADO_DESCARTADO = "descartado"  # marcado como ruido (no se reusa)

# Tipos de entidad (patrón único, PROPUESTA §1).
TIPO_COMPETIDOR = "competidor"
TIPO_EMPRESA = "empresa"
TIPO_OPORTUNIDAD = "oportunidad"
TIPO_EVENTO = "evento"

# Fuentes de procedencia de un atributo (prioridad de conflicto: usuario > emis/db > web).
FUENTE_USUARIO = "usuario"
FUENTE_EMIS = "emis"
FUENTE_DB_EXTERNA = "db_externa"
FUENTE_INFORME = "informe"
FUENTE_WEB = "web"


class Entidad(Base):
    __tablename__ = "entidades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, default=TIPO_COMPETIDOR)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)  # forma display
    nombre_normalizado: Mapped[str] = mapped_column(Text, nullable=False)  # clave de dedup
    nit: Mapped[str | None] = mapped_column(Text, nullable=True)
    ciudad: Mapped[str | None] = mapped_column(Text, nullable=True)
    pais: Mapped[str | None] = mapped_column(Text, nullable=True)
    sector_gics: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Sub-código GICS de 6 dígitos (DT-061): granularidad food/beverage/tobacco dentro del grupo.
    # NULL en candidatos NER; lo fijan solo los pares sembrados verificados (curación/DT-050).
    sub_gics: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default=ESTADO_CANDIDATO)
    # Formas superficiales vistas del mismo nombre normalizado (variantes marca/empresa).
    aliases: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Señal de consolidación (telemetría/ranking, no son hechos).
    n_menciones: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    n_chunks: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    n_sectores: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EntidadAtributo(Base):
    __tablename__ = "entidad_atributos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entidad_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    clave: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[str | None] = mapped_column(Text, nullable=True)
    fuente: Mapped[str] = mapped_column(Text, nullable=False)  # usuario/emis/web/db_externa/informe
    confianza: Mapped[float | None] = mapped_column(Float, nullable=True)
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    documento_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default=ESTADO_CANDIDATO)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def ensure_entidades_tables(engine) -> None:  # type: ignore[no-untyped-def]
    """Crea las tablas del KB si no existen (idempotente), con índices de dedup y consulta."""
    from ic.shared.config import get_settings

    schema = get_settings().db_schema
    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE TABLE IF NOT EXISTS {schema}.entidades ("
            " id BIGSERIAL PRIMARY KEY,"
            " tipo TEXT NOT NULL DEFAULT 'competidor',"
            " nombre TEXT NOT NULL,"
            " nombre_normalizado TEXT NOT NULL,"
            " nit TEXT,"
            " ciudad TEXT,"
            " pais TEXT,"
            " sector_gics TEXT,"
            " sub_gics TEXT,"
            " estado TEXT NOT NULL DEFAULT 'candidato',"
            " aliases JSONB DEFAULT '[]'::jsonb,"
            " n_menciones BIGINT,"
            " n_chunks BIGINT,"
            " n_sectores BIGINT,"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
            " updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        ))
        # Dedup fuerte por NIT (cuando existe).
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_entidad_nit "
            f"ON {schema}.entidades (nit) WHERE nit IS NOT NULL"
        ))
        # Dedup por nombre normalizado + sector (fallback sin NIT). COALESCE para sector NULL.
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_entidad_nombre_sector "
            f"ON {schema}.entidades (nombre_normalizado, COALESCE(sector_gics, ''))"
        ))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_entidad_sector "
            f"ON {schema}.entidades (sector_gics)"
        ))
        # DT-061: sub-código GICS en tablas ya existentes (idempotente) + índice de anclaje fino.
        conn.execute(text(
            f"ALTER TABLE {schema}.entidades ADD COLUMN IF NOT EXISTS sub_gics TEXT"
        ))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_entidad_sub_gics "
            f"ON {schema}.entidades (sub_gics)"
        ))
        conn.execute(text(
            f"CREATE TABLE IF NOT EXISTS {schema}.entidad_atributos ("
            " id BIGSERIAL PRIMARY KEY,"
            " entidad_id BIGINT NOT NULL,"
            " clave TEXT NOT NULL,"
            " valor TEXT,"
            " fuente TEXT NOT NULL,"
            " confianza REAL,"
            " fecha DATE,"
            " documento_id UUID,"
            " estado TEXT NOT NULL DEFAULT 'candidato',"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        ))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_entidad_atributo_entidad "
            f"ON {schema}.entidad_atributos (entidad_id, clave)"
        ))
        # Idempotencia: una valor actual por (entidad, clave, fuente). El lineage entre fuentes
        # distintas se conserva en filas separadas → la prioridad de conflicto (usuario > emis >
        # web) se resuelve en consulta, sin borrar procedencia.
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_entidad_atributo_clave_fuente "
            f"ON {schema}.entidad_atributos (entidad_id, clave, fuente)"
        ))
