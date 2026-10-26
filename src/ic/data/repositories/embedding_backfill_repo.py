"""Backfills idempotentes de metadatos sobre chunks ya indexados (DT-057). No re-embeben."""

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.documento_local import DocumentoLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.shared.constants import TipoDocumento, TipoFuente


class EmbeddingBackfillRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def backfill_tipo_fuente_emis(self) -> int:
        """Backfill idempotente de ``tipo_fuente`` a los chunks EMIS ya indexados (DT-057/T1).

        Los informes EMIS individuales se ingirieron sin ``tipo_fuente`` (NULL) → sin telemetría
        ni palanca de reserva/boost (causa raíz de DT-054). Estampa
        ``metadatos->>'tipo_fuente' = 'informe_emis'`` en los chunks cuyo documento es de tipo
        INFORME_EMIS y que aún no tienen la etiqueta. NO re-embebe: solo UPDATE de metadatos.

        Idempotente: el filtro ``tipo_fuente IS NULL`` hace que una segunda corrida afecte 0 filas.
        Acotado al esquema propio vía los ``__table__.fullname`` (incluyen el schema). Devuelve el
        nº de chunks actualizados.
        """
        emb = EmbeddingVectorial.__table__.fullname
        doc = DocumentoLocal.__table__.fullname
        n = self._db.execute(
            text(
                f"UPDATE {emb} SET metadatos = "
                "coalesce(metadatos, '{}'::jsonb) "
                "|| jsonb_build_object('tipo_fuente', :tf) "
                f"WHERE documento_id IN (SELECT id FROM {doc} WHERE tipo = :tipo_emis) "
                "AND (metadatos->>'tipo_fuente') IS NULL"
            ),
            {"tf": TipoFuente.INFORME_EMIS.value, "tipo_emis": TipoDocumento.INFORME_EMIS.value},
        ).rowcount
        self._db.commit()
        return int(n)

    def backfill_sectores(self, titulo: str, sectores: list[str]) -> int:
        """Backfill idempotente de ``metadatos->'sectores'`` para un documento (DT-057/T2, DT-053).

        Puebla el array multi-sector (``[primario] + adicionales``) en los chunks del documento
        identificado por título, activando la capacidad multi-sector dormida: el retrieval no
        estricto aflora el doc en cualquiera de esos sectores vía ``jsonb_exists`` (ya soportado
        en ``search_similar``). NO re-embebe: solo UPDATE de metadatos.

        Idempotente: la guarda ``IS DISTINCT FROM`` hace que una segunda corrida con el mismo array
        no afecte filas. Devuelve el nº de chunks actualizados.
        """
        emb = EmbeddingVectorial.__table__.fullname
        sectores_json = json.dumps(sectores)
        n = self._db.execute(
            text(
                f"UPDATE {emb} SET metadatos = "
                "coalesce(metadatos, '{}'::jsonb) "
                "|| jsonb_build_object('sectores', CAST(:sectores AS jsonb)) "
                "WHERE metadatos->>'titulo' = :titulo "
                "AND (metadatos->'sectores') IS DISTINCT FROM CAST(:sectores AS jsonb)"
            ),
            {"sectores": sectores_json, "titulo": titulo},
        ).rowcount
        self._db.commit()
        return int(n)
