from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_04_tendencias import (
    format_academic_sources,
    format_chunks_as_context,
)
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.text_utils import has_cjk_characters
from ic.shared.types import CapTendencias

_MIN_CHUNKS = 3


class GenerateTendencias:
    def __init__(
        self,
        chain: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        openalex_connector: OpenAlexConnector,
    ) -> None:
        self._chain = chain
        self._store = store
        self._web = web_connector
        self._openalex = openalex_connector

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
        sector_gics_code: str | None = None,
    ) -> CapTendencias:
        sector_query = f"{sector_gics} {nombre_empresa}"

        # Fuentes web (usa DDG en tests vía force_ddg=True en el caller)
        web_queries = [
            f"{sector_gics} tendencias tecnológicas económicas sociales Colombia",
            f"{sector_gics} sector tendencias estratégicas 2025 2026",
        ]
        for q in web_queries:
            results = self._web.search(q)
            if results:
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )

        # Fuentes académicas (OpenAlex — silencioso si no disponible)
        academic_results = self._openalex.search(
            f"{sector_gics} trends innovation sustainability", max_results=4
        )
        if academic_results:
            self._store.ingest(
                texts=[r.content for r in academic_results],
                fuente_tipo="openalex",
                urls=[r.url for r in academic_results],
            )

        # Retrieval del índice
        chunks = self._store.search(
            f"{sector_query} tendencias estratégicas sector", sector_gics=sector_gics_code
        )

        if not check_retrieval_sufficient(chunks, min_chunks=_MIN_CHUNKS):
            return CapTendencias(
                texto=build_absent_paragraph("Cap 3 — Análisis Tendencial"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context = format_chunks_as_context(chunks)
        academic_context = format_academic_sources(academic_results)

        texto = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_sector": context,
            "fuentes_academicas": academic_context,
        })

        if has_cjk_characters(texto):
            return CapTendencias(
                texto=build_absent_paragraph(
                    "Cap 3 — Análisis Tendencial",
                    "El modelo generó texto en un idioma incorrecto (no español)",
                ),
                n_chunks_usados=len(chunks),
                retrieval_suficiente=False,
                chunks_usados=chunks,
            )

        return CapTendencias(
            texto=texto,
            n_chunks_usados=len(chunks),
            retrieval_suficiente=True,
            chunks_usados=chunks,
        )
