"""Repositorio de menciones de entidades (sustrato del KB, DT-057/T3).

Upsert idempotente por (entidad_normalizada, chunk_id): correr el NER dos veces sobre el mismo
corpus no duplica filas (ON CONFLICT DO NOTHING sobre el índice único). Solo POBLA el sustrato
con procedencia + estado candidato; el merge/verificación del KB es DT-056.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.entidad_mencion import ESTADO_CANDIDATO, EntidadMencion


@dataclass
class MencionRow:
    """DTO de una mención a insertar (con su procedencia)."""

    entidad_normalizada: str
    entidad_texto: str
    tipo: str
    chunk_id: str
    documento_id: str | None
    sector: str | None
    fuente_tipo: str | None


class EntidadMencionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_many(self, filas: list[MencionRow]) -> int:
        """Inserta menciones ignorando duplicados por (entidad_normalizada, chunk_id).

        Devuelve el nº de filas insertadas (las ya presentes se ignoran → idempotente).
        """
        if not filas:
            return 0
        tabla = EntidadMencion.__table__.fullname
        sql = text(
            f"INSERT INTO {tabla} "
            "(entidad_normalizada, entidad_texto, tipo, chunk_id, documento_id, "
            " sector, fuente_tipo, estado) "
            "VALUES (:entidad_normalizada, :entidad_texto, :tipo, CAST(:chunk_id AS uuid), "
            " CAST(:documento_id AS uuid), :sector, :fuente_tipo, :estado) "
            "ON CONFLICT (entidad_normalizada, chunk_id) DO NOTHING"
        )
        insertadas = 0
        for f in filas:
            res = self._db.execute(
                sql,
                {
                    "entidad_normalizada": f.entidad_normalizada,
                    "entidad_texto": f.entidad_texto,
                    "tipo": f.tipo,
                    "chunk_id": f.chunk_id,
                    "documento_id": f.documento_id,
                    "sector": f.sector,
                    "fuente_tipo": f.fuente_tipo,
                    "estado": ESTADO_CANDIDATO,
                },
            )
            insertadas += int(res.rowcount or 0)
        self._db.commit()
        return insertadas

    def count(self) -> int:
        tabla = EntidadMencion.__table__.fullname
        return int(self._db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar() or 0)
