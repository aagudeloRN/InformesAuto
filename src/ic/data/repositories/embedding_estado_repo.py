"""Estado de verificación (RN-001) de los chunks enriquecidos: candidato → verificado/descartado."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.embedding_vectorial import EmbeddingVectorial

CANDIDATO = "candidato"
VERIFICADO = "verificado"
DESCARTADO = "descartado"
_ESTADOS_DESTINO = (VERIFICADO, DESCARTADO)
# Filtro de retrieval (FR-015): un chunk sin la clave (PDFs, web previa) cuenta como citable.
SQL_SOLO_CITABLES = (
    "coalesce(e.metadatos->>'estado_verificacion','verificado') NOT IN ('candidato','descartado')"
)


class EmbeddingEstadoRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def set_estado_verificacion(self, chunk_id: uuid.UUID, estado: str) -> bool:
        """Pasa un chunk de ``candidato`` a ``verificado``/``descartado``. True si cambió.

        Solo transita desde ``candidato``: un ``descartado`` nunca se re-promueve (FR-016) y un
        chunk sin estado (PDFs, web previa) no se toca.
        """
        if estado not in _ESTADOS_DESTINO:
            raise ValueError(f"estado inválido: {estado!r} (esperado {_ESTADOS_DESTINO})")
        emb = EmbeddingVectorial.__table__.fullname
        res = self._db.execute(
            text(
                f"UPDATE {emb} SET metadatos = jsonb_set(metadatos, '{{estado_verificacion}}', "
                "to_jsonb(CAST(:estado AS text))) "
                f"WHERE id = :id AND metadatos->>'estado_verificacion' = '{CANDIDATO}'"
            ),
            {"estado": estado, "id": str(chunk_id)},
        )
        self._db.commit()
        return res.rowcount > 0

    def list_candidatos(self, limit: int = 50) -> list[dict[str, Any]]:
        """Chunks ``candidato`` pendientes de revisión, los más recientes primero."""
        emb = EmbeddingVectorial.__table__.fullname
        rows = self._db.execute(
            text(
                "SELECT id, chunk_texto, fuente_url, "
                "metadatos->>'titulo' AS titulo, metadatos->>'autor' AS autor, "
                "metadatos->>'año' AS anio, metadatos->>'sector_gics' AS sector, "
                "metadatos->>'fuente' AS fuente "
                f"FROM {emb} WHERE metadatos->>'estado_verificacion' = '{CANDIDATO}' "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        ).fetchall()
        return [
            {
                "id": str(r.id),
                "texto": r.chunk_texto,
                "url": r.fuente_url,
                "titulo": r.titulo,
                "autor": r.autor,
                "año": r.anio,
                "sector": r.sector,
                "fuente": r.fuente,
            }
            for r in rows
        ]
