"""Repositorio del checkpoint de capítulos (T22.3, DT-030).

Persiste/lee el estado serializado de los capítulos por corrida (run_key). El
payload es un dict JSON-serializable producido por domain/checkpoint_serde.py; este
repositorio no conoce los tipos de dominio (SoC).
"""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ic.data.models.checkpoint import CheckpointCapitulo


class CheckpointRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save_capitulo(self, run_key: str, cap_nombre: str, payload: dict) -> None:
        """Upsert idempotente del payload de un capítulo (sobrescribe si ya existe)."""
        stmt = (
            pg_insert(CheckpointCapitulo)
            .values(run_key=run_key, cap_nombre=cap_nombre, payload=payload)
            .on_conflict_do_update(
                index_elements=["run_key", "cap_nombre"],
                set_={"payload": payload},
            )
        )
        self._db.execute(stmt)
        self._db.commit()

    def load_capitulos(self, run_key: str) -> dict[str, dict]:
        """Devuelve {cap_nombre: payload} de los capítulos persistidos de la corrida."""
        stmt = select(CheckpointCapitulo).where(CheckpointCapitulo.run_key == run_key)
        rows = self._db.execute(stmt).scalars().all()
        return {row.cap_nombre: row.payload for row in rows}

    def get_capitulo(self, run_key: str, cap_nombre: str) -> dict | None:
        """Payload de un capítulo cacheado (keep-best/fallback, Fase 1), o None si no existe."""
        stmt = select(CheckpointCapitulo.payload).where(
            CheckpointCapitulo.run_key == run_key,
            CheckpointCapitulo.cap_nombre == cap_nombre,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def clear(self, run_key: str) -> None:
        """Borra el checkpoint de una corrida (p. ej. tras completarla con éxito)."""
        self._db.execute(delete(CheckpointCapitulo).where(CheckpointCapitulo.run_key == run_key))
        self._db.commit()
