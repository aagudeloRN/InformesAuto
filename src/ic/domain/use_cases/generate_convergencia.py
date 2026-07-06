from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_06_convergencia import (
    format_chunks_as_context,
)
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.types import CapConvergencia, ChunkResult

_MIN_CHUNKS = 5


class GenerateConvergencia:
    def __init__(
        self,
        chain: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
    ) -> None:
        self._chain = chain
        self._store = store
        self._web = web_connector

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
    ) -> CapConvergencia:
        web_queries = [
            f"{sector_gics} sostenibilidad ambiental Colombia regulaciones",
            f"{sector_gics} transformación digital gobierno inteligente Colombia",
        ]
        for q in web_queries:
            results = self._web.search(q)
            if results:
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )

        query_caps = (
            f"{sector_gics} {nombre_empresa} tendencias ecosistema benchmarking estrategia"
        )
        query_territorial = (
            f"{sector_gics} {nombre_empresa} "
            "sostenibilidad transformación digital desarrollo económico Medellín"
        )

        chunks_caps = self._store.search(query_caps)
        chunks_territorial = self._store.search(query_territorial)

        seen: set[str] = set()
        unique_chunks: list[ChunkResult] = []
        for chunk in chunks_caps + chunks_territorial:
            key = chunk.fuente_url or chunk.chunk_texto[:60]
            if key not in seen:
                seen.add(key)
                unique_chunks.append(chunk)

        if not check_retrieval_sufficient(unique_chunks, min_chunks=_MIN_CHUNKS):
            return CapConvergencia(
                texto=build_absent_paragraph("Cap 5 — Convergencia Empresarial"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context_caps = format_chunks_as_context(chunks_caps)
        context_territorial = format_chunks_as_context(chunks_territorial)

        texto = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_caps_anteriores": context_caps,
            "retrieval_convergencia_territorial": context_territorial,
        })

        return CapConvergencia(
            texto=texto,
            n_chunks_usados=len(unique_chunks),
            retrieval_suficiente=True,
            chunks_usados=unique_chunks,
        )
