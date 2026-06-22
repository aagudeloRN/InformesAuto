"""Smoke tests de BD: requieren PostgreSQL corriendo (docker compose up -d + create_schema.py)."""

from sqlalchemy import inspect, text

from ic.data.database import engine
from ic.shared.config import get_settings

EXPECTED_TABLES = {"empresas", "historial_informes", "documentos_locales", "embeddings_vectoriales"}

settings = get_settings()


def test_connection():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_schema_exists():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
            {"schema": settings.db_schema},
        )
        assert result.scalar() == settings.db_schema, f"Schema '{settings.db_schema}' no encontrado"


def test_tables_exist():
    inspector = inspect(engine)
    tables = set(inspector.get_table_names(schema=settings.db_schema))
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Tablas faltantes: {missing}"


def test_pgvector_extension():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        assert result.scalar() == "vector", "Extensión pgvector no instalada"
