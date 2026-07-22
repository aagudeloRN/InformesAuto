import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from ic.data.models.documento_local import DocumentoLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial


class DocumentoRepository:
    """Gestión del corpus de documentos locales (ciclo de vida activo/inactivo, borrado)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[DocumentoLocal]:
        return list(
            self._db.execute(
                select(DocumentoLocal).order_by(DocumentoLocal.created_at.desc())
            ).scalars()
        )

    def set_activo(self, documento_id: uuid.UUID, activo: bool) -> None:
        """Activa/desactiva un documento sin borrar sus chunks (toggle de ciclo de vida)."""
        doc = self._db.get(DocumentoLocal, documento_id)
        if doc is not None:
            doc.activo = activo
            self._db.commit()

    def delete_with_chunks(self, documento_id: uuid.UUID) -> int:
        """Borra el documento y todos sus chunks en embeddings_vectoriales.

        Devuelve el número de chunks eliminados.
        """
        n_chunks = self._db.execute(
            text(
                "SELECT count(*) FROM "
                f"{EmbeddingVectorial.__table__.fullname} "
                "WHERE documento_id = :doc_id"
            ),
            {"doc_id": str(documento_id)},
        ).scalar_one()
        self._db.execute(
            delete(EmbeddingVectorial).where(EmbeddingVectorial.documento_id == documento_id)
        )
        self._db.execute(delete(DocumentoLocal).where(DocumentoLocal.id == documento_id))
        self._db.commit()
        return int(n_chunks)
