from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_03b_mercado import format_chunks_as_context
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.text_utils import has_cjk_characters
from ic.shared.types import CapMercado

_MIN_CHUNKS = 3


class GenerateMercado:
    """Cap 2.3 Mercado (T21.6, DT-044). Mismo patrón que GenerateTendencias."""

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
        sector_gics_code: str | None = None,
        empresa_id=None,
    ) -> CapMercado:
        # Queries de dimensionamiento de mercado con search_depth="advanced" (perfil de datos,
        # no overview): cifras de tamaño, segmentos y crecimiento por región.
        web_queries = [
            f"{sector_gics} tamaño de mercado segmentos crecimiento Colombia LatAm 2025",
            f"{sector_gics} market size por región participación tendencias",
        ]
        for q in web_queries:
            results = self._web.search(q, search_depth="advanced")
            if results:
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )

        chunks = self._store.search(
            f"{sector_gics} tamaño de mercado segmentos crecimiento por región",
            sector_gics=sector_gics_code, empresa_id=empresa_id,
        )

        if not check_retrieval_sufficient(chunks, min_chunks=_MIN_CHUNKS):
            return CapMercado(
                texto=build_absent_paragraph("Sección 2.3 — Mercado"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context = format_chunks_as_context(chunks)
        texto = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_mercado": context,
        })

        if has_cjk_characters(texto):
            return CapMercado(
                texto=build_absent_paragraph(
                    "Sección 2.3 — Mercado",
                    "El modelo generó texto en un idioma incorrecto (no español)",
                ),
                n_chunks_usados=len(chunks),
                retrieval_suficiente=False,
                chunks_usados=chunks,
            )

        return CapMercado(
            texto=texto,
            n_chunks_usados=len(chunks),
            retrieval_suficiente=True,
            chunks_usados=chunks,
        )
