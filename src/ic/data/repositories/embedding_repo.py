import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.documento_local import DocumentoLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial


class EmbeddingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def insert_many(self, chunks: list[EmbeddingVectorial]) -> None:
        self._db.add_all(chunks)
        self._db.commit()

    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int,
        threshold: float,
        empresa_id: uuid.UUID | None = None,
        sector_gics: str | None = None,
        solo_activos: bool = True,
        max_chunks_per_doc: int | None = None,
        sector_estricto: bool = False,
    ) -> list[tuple[EmbeddingVectorial, float]]:
        # Margen amplio: el filtro sectorial + el cap por documento reducen candidatos
        fetch_k = top_k * 4
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        emb_table = EmbeddingVectorial.__table__.fullname
        doc_table = DocumentoLocal.__table__.fullname

        conditions: list[str] = []
        params: dict = {"vec": vec_str, "fetch_k": fetch_k}

        if empresa_id is not None:
            conditions.append("(e.empresa_id = :empresa_id OR e.empresa_id IS NULL)")
            params["empresa_id"] = str(empresa_id)
        if sector_gics is not None and sector_estricto:
            # Solo el corpus sectorial compilado del GICS pedido (evidencia sectorial garantizada)
            conditions.append(
                "(e.metadatos->>'sector_gics' = :sector "
                "AND e.metadatos->>'tipo_fuente' = 'informe_compilado')"
            )
            params["sector"] = sector_gics
        elif sector_gics is not None:
            # Incluye el sector pedido + fuentes sin sector (web/académicas)
            conditions.append(
                "(e.metadatos->>'sector_gics' = :sector "
                "OR e.metadatos->>'sector_gics' IS NULL)"
            )
            params["sector"] = sector_gics
        if solo_activos:
            # Activo o sin documento asociado (chunks web no tienen documento_id)
            conditions.append("(d.activo IS NOT FALSE)")

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sql = text(
            f"""
            SELECT e.id, e.documento_id AS doc_id,
                   1 - (e.embedding <=> CAST(:vec AS vector)) AS score
            FROM {emb_table} e
            LEFT JOIN {doc_table} d ON e.documento_id = d.id
            {where_clause}
            ORDER BY e.embedding <=> CAST(:vec AS vector)
            LIMIT :fetch_k
            """
        )
        rows = self._db.execute(sql, params).fetchall()

        result = []
        per_doc: dict = {}
        for row in rows:
            score = float(row.score)
            if score < threshold:
                continue
            # Cap por documento: limita chunks del mismo documento (diversidad, ADR-012)
            if max_chunks_per_doc is not None and row.doc_id is not None:
                seen = per_doc.get(row.doc_id, 0)
                if seen >= max_chunks_per_doc:
                    continue
                per_doc[row.doc_id] = seen + 1
            obj = self._db.get(EmbeddingVectorial, row.id)
            if obj is not None:
                result.append((obj, score))
            if len(result) >= top_k:
                break
        return result
