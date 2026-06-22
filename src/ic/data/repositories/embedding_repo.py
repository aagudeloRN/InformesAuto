import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

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
    ) -> list[tuple[EmbeddingVectorial, float]]:
        fetch_k = top_k * 2
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        table = EmbeddingVectorial.__table__.fullname

        where_clause = "WHERE (empresa_id = :empresa_id OR empresa_id IS NULL)"
        params: dict = {"vec": vec_str, "fetch_k": fetch_k}
        if empresa_id is not None:
            params["empresa_id"] = str(empresa_id)
        else:
            where_clause = ""

        sql = text(
            f"""
            SELECT id, 1 - (embedding <=> CAST(:vec AS vector)) AS score
            FROM {table}
            {where_clause}
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :fetch_k
            """
        )
        rows = self._db.execute(sql, params).fetchall()

        result = []
        for row in rows:
            score = float(row.score)
            if score < threshold:
                continue
            obj = self._db.get(EmbeddingVectorial, row.id)
            if obj is not None:
                result.append((obj, score))
            if len(result) >= top_k:
                break
        return result
