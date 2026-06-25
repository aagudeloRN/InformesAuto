from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.types import CapBenchmarking

_MIN_CHUNKS = 5


class GenerateBenchmarking:
    def __init__(
        self,
        chain: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
    ) -> None:
        self._chain = chain
        self._store = store
        self._web_connector = web_connector

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
    ) -> CapBenchmarking:
        queries = [
            f"{sector_gics} competidores líderes globales",
            f"{sector_gics} referentes regionales LatAm Colombia",
            f"{sector_gics} startups FoodTech disruptivas",
        ]
        for query in queries:
            web_results = self._web_connector.search(query)
            if web_results:
                self._store.ingest(
                    texts=[r.content for r in web_results],
                    fuente_tipo="web",
                    urls=[r.url for r in web_results],
                )

        chunks = self._store.search(
            f"{sector_gics} competitors benchmarking {nombre_empresa}"
        )

        if not check_retrieval_sufficient(chunks, min_chunks=_MIN_CHUNKS):
            return CapBenchmarking(
                texto=build_absent_paragraph("Cap 2 — Análisis Competitivo"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
            )

        context = format_chunks_as_context(chunks)
        texto = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "retrieval_competidores": context,
        })

        return CapBenchmarking(
            texto=texto,
            n_chunks_usados=len(chunks),
            retrieval_suficiente=True,
        )
