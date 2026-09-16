"""Seed fixture para tests de integraci?n sectoriales."""

from __future__ import annotations

import uuid
from typing import Any

from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.data.models.empresa import Empresa


def seed_sector_data(
    db_session: Any, sector_gics: str = "302020", empresa_nombre: str = "Alpina S.A.S."
) -> dict[str, Any]:
    """Inserta datos de prueba en la base de datos para pruebas de integraci?n."""
    # 1. Empresa
    empresa = Empresa(
        id=uuid.uuid4(),
        nombre=empresa_nombre,
        sector_gics=sector_gics,
    )
    db_session.add(empresa)

    # 2. Embedding sectorial
    emb = EmbeddingVectorial(
        id=uuid.uuid4(),
        fuente_tipo="pdf",
        fuente_url="/mock/sector.pdf",
        chunk_texto=f"El sector {sector_gics} presenta alto crecimiento en l?cteos.",
        chunk_index=0,
        embedding=[0.05] * 768,
        metadatos={"sector_gics": sector_gics, "tipo": "sectorial"},
    )
    db_session.add(emb)
    db_session.commit()

    return {"empresa_id": empresa.id, "embedding_id": emb.id}
