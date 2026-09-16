"""Verificacion de servicios externos (Ollama, PostgreSQL)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ic.shared.config import Settings


def check_services(settings: Settings) -> tuple[bool, bool]:
    """Comprueba conectividad con Ollama y PostgreSQL."""
    import httpx
    import sqlalchemy

    ollama_ok = False
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        ollama_ok = resp.status_code == 200
    except Exception:
        pass

    pg_ok = False
    try:
        engine = sqlalchemy.create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        engine.dispose()
        pg_ok = True
    except Exception:
        pass

    return ollama_ok, pg_ok
