import json
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.documento_local import DocumentoLocal
from ic.data.models.embedding_vectorial import EmbeddingVectorial
from ic.infrastructure.retrieval.mmr import apply_mmr_reranking
from ic.shared.constants import TipoDocumento, TipoFuente


class EmbeddingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def insert_many(self, chunks: list[EmbeddingVectorial]) -> None:
        self._db.add_all(chunks)
        self._db.commit()

    def promote_cited_web(self, session_id: str, cited_ids: list[str]) -> tuple[int, int]:
        """Persistencia web "solo lo citado" (T14.5, DT-020).

        De los chunks web de esta sesión: borra los NO citados y promueve los citados a
        permanentes (quita `session_id`, marca `promoted=true`). Devuelve (borrados, promovidos).
        """
        emb = EmbeddingVectorial.__table__.fullname
        ids = [str(i) for i in cited_ids]
        # 1) Borrar los no citados de la sesión.
        if ids:
            borrados = self._db.execute(
                text(
                    f"DELETE FROM {emb} WHERE fuente_tipo = 'web' "
                    "AND metadatos->>'session_id' = :sid "
                    "AND id <> ALL(CAST(:ids AS uuid[]))"
                ),
                {"sid": session_id, "ids": ids},
            ).rowcount
            # 2) Promover los citados: quitar session_id y marcar promoted.
            promovidos = self._db.execute(
                text(
                    f"UPDATE {emb} SET metadatos = "
                    "(metadatos - 'session_id') || jsonb_build_object('promoted', 'true') "
                    "WHERE fuente_tipo = 'web' AND metadatos->>'session_id' = :sid "
                    "AND id = ANY(CAST(:ids AS uuid[]))"
                ),
                {"sid": session_id, "ids": ids},
            ).rowcount
        else:
            borrados = self._db.execute(
                text(
                    f"DELETE FROM {emb} WHERE fuente_tipo = 'web' "
                    "AND metadatos->>'session_id' = :sid"
                ),
                {"sid": session_id},
            ).rowcount
            promovidos = 0
        self._db.commit()
        return int(borrados), int(promovidos)

    def sweep_stale_web_sessions(self, keep_session_id: str) -> int:
        """Borra chunks web de sesiones anteriores (huérfanos por crash a mitad de corrida).

        Se llama al inicio de una corrida: cualquier chunk web con `session_id` distinto del
        actual quedó de una corrida que no llegó a promover. Devuelve el nº de chunks borrados.
        """
        emb = EmbeddingVectorial.__table__.fullname
        n = self._db.execute(
            text(
                f"DELETE FROM {emb} WHERE fuente_tipo = 'web' "
                "AND metadatos->>'session_id' IS NOT NULL "
                "AND metadatos->>'session_id' <> :sid"
            ),
            {"sid": keep_session_id},
        ).rowcount
        self._db.commit()
        return int(n)

    def purge_unused_web_backlog(self, limit_ids: list[str] | None = None) -> int:
        """Purga el backlog web no usado (T14.5, DT-020).

        Solo borra los chunks web "legacy": sin `session_id` y sin `promoted`.
        No toca chunks promovidos ni en-sesión.

        limit_ids (T15.5): si se pasa, restringe la purga a esos IDs concretos.
        Útil en tests para borrar únicamente los chunks que el test insertó, sin
        afectar el resto de la BD.
        """
        emb = EmbeddingVectorial.__table__.fullname
        if limit_ids:
            n = self._db.execute(
                text(
                    f"DELETE FROM {emb} WHERE fuente_tipo = 'web' "
                    "AND metadatos->>'session_id' IS NULL "
                    "AND metadatos->>'promoted' IS NULL "
                    "AND id = ANY(CAST(:ids AS uuid[]))"
                ),
                {"ids": limit_ids},
            ).rowcount
        else:
            n = self._db.execute(
                text(
                    f"DELETE FROM {emb} WHERE fuente_tipo = 'web' "
                    "AND metadatos->>'session_id' IS NULL "
                    "AND metadatos->>'promoted' IS NULL"
                )
            ).rowcount
        self._db.commit()
        return int(n)

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

    def count_web(self) -> dict[str, int]:
        """Conteo de chunks web por estado (para verificación T14.5)."""
        emb = EmbeddingVectorial.__table__.fullname
        row = self._db.execute(
            text(
                f"SELECT count(*) AS total, "
                "count(*) FILTER (WHERE metadatos->>'promoted' = 'true') AS promoted, "
                "count(*) FILTER (WHERE metadatos->>'session_id' IS NOT NULL) AS in_session, "
                "count(*) FILTER (WHERE metadatos->>'session_id' IS NULL "
                "  AND metadatos->>'promoted' IS NULL) AS legacy "
                f"FROM {emb} WHERE fuente_tipo = 'web'"
            )
        ).one()
        return {
            "total": int(row.total),
            "promoted": int(row.promoted),
            "in_session": int(row.in_session),
            "legacy": int(row.legacy),
        }

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
        global_estricto: bool = False,
        empresa_estricto: bool = False,
        mmr_lambda: float = 1.0,
        fuente_tipo_filter: str | None = None,
    ) -> list[tuple[EmbeddingVectorial, float]]:
        # Margen amplio: el filtro sectorial + el cap por documento reducen candidatos
        fetch_k = top_k * 4
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        emb_table = EmbeddingVectorial.__table__.fullname
        doc_table = DocumentoLocal.__table__.fullname

        conditions: list[str] = []
        params: dict = {"vec": vec_str, "fetch_k": fetch_k}

        if empresa_estricto and empresa_id is not None:
            # Solo chunks de la empresa específica (reserva empresa, Fase 18 T18.3)
            conditions.append("e.empresa_id = :empresa_id")
            params["empresa_id"] = str(empresa_id)
        elif empresa_id is not None:
            conditions.append("(e.empresa_id = :empresa_id OR e.empresa_id IS NULL)")
            params["empresa_id"] = str(empresa_id)

        if global_estricto:
            # Solo chunks con es_global=true (reserva global cross-sector, Fase 18 DT-031)
            conditions.append("e.metadatos->>'es_global' = 'true'")
        elif sector_gics is not None and sector_estricto:
            # Todo el corpus sectorial del GICS pedido (evidencia sectorial garantizada).
            # DT-054: antes se restringía a tipo_fuente='informe_compilado', lo que excluía de la
            # reserva a los EMIS individuales (tipo_fuente NULL pero con sector_gics seteado). Al
            # filtrar solo por sector_gics, el compilado y los EMIS individuales compiten por score
            # dentro de la reserva; la web/académicas (sector_gics NULL) siguen fuera → la garantía
            # sectorial anti-mezcla de ADR-012 se preserva.
            conditions.append("e.metadatos->>'sector_gics' = :sector")
            params["sector"] = sector_gics
        elif sector_gics is not None:
            # Incluye el sector pedido + docs multi-sector + fuentes sin sector (web/académicas)
            # jsonb_exists verifica si el array "sectores" contiene el código pedido (Fase 18 T18.4)
            conditions.append(
                "(e.metadatos->>'sector_gics' = :sector "
                "OR jsonb_exists(e.metadatos->'sectores', :sector) "
                "OR (e.metadatos->>'sector_gics' IS NULL "
                "    AND NOT coalesce(e.metadatos->>'es_global', 'false') = 'true'))"
            )
            params["sector"] = sector_gics
        if solo_activos:
            # Activo o sin documento asociado (chunks web no tienen documento_id)
            conditions.append("(d.activo IS NOT FALSE)")

        if fuente_tipo_filter is not None:
            conditions.append("e.fuente_tipo = :fuente_tipo")
            params["fuente_tipo"] = fuente_tipo_filter

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

        # Candidatos que superan el umbral (con su doc_id para el reranking por diversidad)
        candidatos = [
            {"id": row.id, "doc_id": row.doc_id, "score": float(row.score)}
            for row in rows
            if float(row.score) >= threshold
        ]

        # MMR (Fase 14, T14.2): reordena por diversidad de documento antes del cap duro.
        # Con λ=1.0 es un no-op y se conserva el orden por score (comportamiento pre-Fase 14).
        candidatos = apply_mmr_reranking(candidatos, mmr_lambda=mmr_lambda)

        result: list[tuple[EmbeddingVectorial, float]] = []
        per_doc: dict = {}
        for cand in candidatos:
            # Cap por documento: tope duro final de diversidad (defensa en profundidad, ADR-012)
            if max_chunks_per_doc is not None and cand["doc_id"] is not None:
                seen = per_doc.get(cand["doc_id"], 0)
                if seen >= max_chunks_per_doc:
                    continue
                per_doc[cand["doc_id"]] = seen + 1
            obj = self._db.get(EmbeddingVectorial, cand["id"])
            if obj is not None:
                result.append((obj, cand["score"]))
            if len(result) >= top_k:
                break
        return result
