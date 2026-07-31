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

# Alcance de una entidad (DT-061b): separa el descubrimiento de competidores de CLASE MUNDIAL
# (`global`) del de jugadores locales grandes (`local`, fuente natural DT-050 base Colombia). NULL =
# sin clasificar (candidatos NER). El anclaje de la sección 2.1.1 filtra `global`.
ALCANCE_GLOBAL = "global"
ALCANCE_LOCAL = "local"

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
# El nombre lo recomendó el LLM (DT-062); solo es citable si la web lo corrobora (RN-001).
FUENTE_LLM = "llm"

# Segmento de la entidad (DT-050): separa el tier de startups (2.1.3) del regional (2.1.2). NULL =
# empresa establecida (default). Solo el corpus StartIA carga `startup`.
SEGMENTO_STARTUP = "startup"


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
    # Alcance global/local (DT-061b): el anclaje de clase mundial (2.1.1) filtra `global`.
    alcance: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Segmento (DT-050): `startup` (tier 2.1.3) vs NULL (empresa establecida, tier 2.1.2).
    segmento: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class EntidadSector(Base):
    """Membresía sectorial de una entidad (DT-050). Multi-sector es feature, no duplicado.

    Una empresa puede pertenecer a varios sectores/verticales (transversalidad real: filas EMIS con
    varias actividades CIIU, startups multi-vertical). Cada membresía lleva su procedencia
    (`fuente`) y estado (RN-001). El anclaje hace join por `sector_gics`; `n_sectores` = COUNT real.
    """

    __tablename__ = "entidad_sectores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entidad_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sector_gics: Mapped[str] = mapped_column(Text, nullable=False)
    sub_gics: Mapped[str | None] = mapped_column(Text, nullable=True)
    # etiqueta de origen (texto CIIU o vertical StartIA)
    vertical: Mapped[str | None] = mapped_column(Text, nullable=True)
    alcance: Mapped[str | None] = mapped_column(Text, nullable=True)
    fuente: Mapped[str] = mapped_column(Text, nullable=False)
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
            " alcance TEXT,"
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
        # Dedup por (nombre_normalizado, sector) SOLO para entidades sin NIT (NER/LLM). Las que
        # tienen NIT se deduplican por NIT: dos empresas reales pueden compartir nombre + sector,
        # y el NIT es la clave real. Por eso el índice es PARCIAL (WHERE nit IS NULL): si no, el
        # INSERT de una fila EMIS con NIT choca contra un candidato NER homónimo (DT-050). Migración
        # idempotente: se retira el índice global antiguo y se crea el parcial (nombre nuevo).
        conn.execute(text(f"DROP INDEX IF EXISTS {schema}.ux_entidad_nombre_sector"))
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_entidad_nombre_sector_nonit "
            f"ON {schema}.entidades (nombre_normalizado, COALESCE(sector_gics, '')) "
            f"WHERE nit IS NULL"
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
        # DT-061b: alcance global/local (idempotente) para el anclaje de clase mundial.
        conn.execute(text(
            f"ALTER TABLE {schema}.entidades ADD COLUMN IF NOT EXISTS alcance TEXT"
        ))
        # DT-050: segmento (startup) para separar el tier 2.1.3 del 2.1.2 (idempotente).
        conn.execute(text(
            f"ALTER TABLE {schema}.entidades ADD COLUMN IF NOT EXISTS segmento TEXT"
        ))
        # DT-050: membresías sectoriales (multi-sector). Único por (entidad, sector, sub_gics) para
        # idempotencia; COALESCE del sub para tratar NULL como valor en el índice.
        conn.execute(text(
            f"CREATE TABLE IF NOT EXISTS {schema}.entidad_sectores ("
            " id BIGSERIAL PRIMARY KEY,"
            " entidad_id BIGINT NOT NULL,"
            " sector_gics TEXT NOT NULL,"
            " sub_gics TEXT,"
            " vertical TEXT,"
            " alcance TEXT,"
            " fuente TEXT NOT NULL,"
            " estado TEXT NOT NULL DEFAULT 'candidato',"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        ))
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_entidad_sector "
            f"ON {schema}.entidad_sectores (entidad_id, sector_gics, COALESCE(sub_gics, ''))"
        ))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_entidad_sector_gics "
            f"ON {schema}.entidad_sectores (sector_gics)"
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
