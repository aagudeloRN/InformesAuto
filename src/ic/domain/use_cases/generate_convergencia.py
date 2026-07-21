"""Genera Cap 5 — Convergencia Empresarial usando divide y vencerás (RN-009).

3 llamadas paralelas (un eje por llamada con api_llm free ~120B) + 1 síntesis
integradora (api_llm_synth). Tiempo estimado: ~15 min vs 79 min monolítico.
"""

from concurrent.futures import ThreadPoolExecutor

from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_06_convergencia import format_chunks_as_context
from ic.domain.chains.chain_06a_convergencia_eje import EJE_MERCADO, EJE_SOCIAL, EJE_TECNOLOGICO
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.text_utils import has_cjk_characters
from ic.shared.types import CapConvergencia, ChunkResult

_MIN_CHUNKS = 5


class GenerateConvergencia:
    def __init__(
        self,
        chain: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        chain_eje: Runnable | None = None,
    ) -> None:
        self._chain_synth = chain
        self._chain_eje = chain_eje
        self._store = store
        self._web = web_connector

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
    ) -> CapConvergencia:
        for q in [
            f"{sector_gics} sostenibilidad ambiental Colombia regulaciones",
            f"{sector_gics} transformación digital gobierno inteligente Colombia",
        ]:
            results = self._web.search(q)
            if results:
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )

        chunks_caps = self._store.search(
            f"{sector_gics} {nombre_empresa} tendencias ecosistema benchmarking estrategia"
        )
        query_territorial = (
            f"{sector_gics} {nombre_empresa} "
            "sostenibilidad transformación digital desarrollo económico Medellín"
        )
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

        retrieval_context = format_chunks_as_context(unique_chunks)
        base_args = {
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_context": retrieval_context,
        }

        # Ruta rápida: sin chain_eje → llamada monolítica legacy
        if self._chain_eje is None:
            context_caps = format_chunks_as_context(chunks_caps)
            context_territorial = format_chunks_as_context(chunks_territorial)
            texto = self._chain_synth.invoke({
                "descripcion_empresa": descripcion_empresa,
                "sector_gics": sector_gics,
                "retrieval_caps_anteriores": context_caps,
                "retrieval_convergencia_territorial": context_territorial,
            })
            if has_cjk_characters(texto):
                return CapConvergencia(
                    texto=build_absent_paragraph(
                        "Cap 5 — Convergencia Empresarial",
                        "El modelo generó texto en un idioma incorrecto (no español)",
                    ),
                    n_chunks_usados=len(unique_chunks),
                    retrieval_suficiente=False,
                    chunks_usados=unique_chunks,
                )
            return CapConvergencia(texto=texto, n_chunks_usados=len(unique_chunks),
                                   retrieval_suficiente=True, chunks_usados=unique_chunks)

        # Divide y vencerás (RN-009): 3 ejes en paralelo + síntesis
        def _invoke_eje(eje_def: dict) -> str:
            return self._chain_eje.invoke({**base_args, **eje_def})

        with ThreadPoolExecutor(max_workers=3) as pool:
            f_tec = pool.submit(_invoke_eje, EJE_TECNOLOGICO)
            f_mer = pool.submit(_invoke_eje, EJE_MERCADO)
            f_soc = pool.submit(_invoke_eje, EJE_SOCIAL)
        texto_tec, texto_mer, texto_soc = f_tec.result(), f_mer.result(), f_soc.result()

        texto_final = self._chain_synth.invoke({
            "partes": "\n\n---\n\n".join([texto_tec, texto_soc, texto_mer])
        })

        if has_cjk_characters(texto_final):
            return CapConvergencia(
                texto=build_absent_paragraph(
                    "Cap 5 — Convergencia Empresarial",
                    "El modelo generó texto en un idioma incorrecto (no español)",
                ),
                n_chunks_usados=len(unique_chunks),
                retrieval_suficiente=False,
                chunks_usados=unique_chunks,
            )

        return CapConvergencia(
            texto=texto_final,
            n_chunks_usados=len(unique_chunks),
            retrieval_suficiente=True,
            chunks_usados=unique_chunks,
        )
