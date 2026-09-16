from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_05_ecosistema import (
    SUBSECCIONES,
    build_secciones_solicitadas,
    format_academic_sources,
    format_chunks_as_context,
)
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.text_utils import has_cjk_characters, strip_preamble
from ic.shared.types import CapEcosistema

_MIN_CHUNKS = 3


class GenerateEcosistema:
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
    ) -> CapEcosistema:
        sector_query = f"{sector_gics} {nombre_empresa}"

        web_queries = [
            f"{nombre_empresa} ecosistema proveedores",
            f"{sector_gics} sector alianzas partners",
        ]
        all_web_results: list = []
        for q in web_queries:
            results = self._web.search(q)
            if results:
                all_web_results.extend(results)
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )

        # DT-058: capítulo adaptativo. Cada subsección 4.x se gatea por su propio retrieval; solo
        # se solicitan al modelo las que superan el umbral (ADR-002). Si ninguna lo supera, el
        # capítulo se OMITE con párrafo de ausencia (no se borra del informe).
        activas: list[tuple[str, str, str, str]] = []
        chunks_usados: list = []
        vistos: set = set()
        for subsec in SUBSECCIONES:
            _sid, _titulo, _desc, query = subsec
            sub_chunks = self._store.search(
                f"{sector_query} {query}",
                sector_gics=sector_gics_code,
                empresa_id=empresa_id,
            )
            if not check_retrieval_sufficient(sub_chunks, min_chunks=_MIN_CHUNKS):
                continue
            activas.append(subsec)
            for ch in sub_chunks:
                clave = ch.chunk_id or ch.chunk_texto
                if clave not in vistos:
                    vistos.add(clave)
                    chunks_usados.append(ch)

        if not activas:
            return CapEcosistema(
                texto=build_absent_paragraph("Cap 4 — Ecosistema Empresarial"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context = format_chunks_as_context(chunks_usados)
        web_context = format_academic_sources(all_web_results)

        texto = self._chain.invoke(
            {
                "descripcion_empresa": descripcion_empresa,
                "sector_gics": sector_gics,
                "retrieval_sector": context,
                "fuentes_web": web_context,
                "secciones_solicitadas": build_secciones_solicitadas(activas),
            }
        )
        texto = strip_preamble(texto)

        if has_cjk_characters(texto):
            return CapEcosistema(
                texto=build_absent_paragraph(
                    "Cap 4 — Ecosistema Empresarial",
                    "El modelo generó texto en un idioma incorrecto (no español)",
                ),
                n_chunks_usados=len(chunks_usados),
                retrieval_suficiente=False,
                chunks_usados=chunks_usados,
            )

        return CapEcosistema(
            texto=texto,
            n_chunks_usados=len(chunks_usados),
            retrieval_suficiente=True,
            chunks_usados=chunks_usados,
        )
