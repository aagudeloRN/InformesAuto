"""Curación humana de fragmentos enriquecidos ``candidato`` (RN-001, Spec 008 / FR-016)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ic.data.database import SessionLocal
from ic.data.repositories.embedding_estado_repo import (
    DESCARTADO,
    VERIFICADO,
    EmbeddingEstadoRepository,
)

logger = logging.getLogger(__name__)


def listar_candidatos(limit: int = 50) -> list[dict[str, Any]]:
    """Fragmentos web pendientes de aprobación; [] si la consulta falla."""
    try:
        with SessionLocal() as db:
            return EmbeddingEstadoRepository(db).list_candidatos(limit)
    except Exception as exc:
        logger.warning("Error al listar candidatos: %s", exc)
        return []


def resolver_candidato(chunk_id: str, aprobar: bool) -> bool:
    """Aprueba (``verificado``) o descarta (``descartado``) un candidato. True si cambió."""
    try:
        with SessionLocal() as db:
            return EmbeddingEstadoRepository(db).set_estado_verificacion(
                uuid.UUID(chunk_id), VERIFICADO if aprobar else DESCARTADO
            )
    except Exception as exc:
        logger.warning("Error al resolver candidato %s: %s", chunk_id, exc)
        return False
