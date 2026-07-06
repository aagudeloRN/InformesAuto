from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_07_accionables import format_chunks_as_context
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.shared.types import CapAccionables

_MIN_CHUNKS = 6


class GenerateAccionables:
    def __init__(
        self,
        chain: Runnable,
        store: PGVectorStore,
    ) -> None:
        self._chain = chain
        self._store = store

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
    ) -> CapAccionables:
        query = (
            f"{sector_gics} {nombre_empresa} "
            "estrategia accionables benchmarking tendencias ecosistema convergencia"
        )
        chunks = self._store.search(query)

        if not check_retrieval_sufficient(chunks, min_chunks=_MIN_CHUNKS):
            return CapAccionables(
                texto=build_absent_paragraph("Cap 6 — Accionables Estratégicos"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context = format_chunks_as_context(chunks)

        texto = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_cruzado": context,
        })

        return CapAccionables(
            texto=texto,
            n_chunks_usados=len(chunks),
            retrieval_suficiente=True,
            chunks_usados=chunks,
        )
