from __future__ import annotations

import json
import logging
import re

from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.text_utils import has_cjk_characters
from ic.shared.types import CapBenchmarking

logger = logging.getLogger(__name__)

_MIN_CHUNKS = 5

# Bloque JSON de scores del radar emitido al final de la respuesta del LLM (T16.1)
_RADAR_RE = re.compile(r"```radar_json\s*(.*?)```", re.DOTALL)


def _extract_radar(texto: str) -> tuple[str, dict | None]:
    """Extrae el bloque radar_json del texto del LLM y devuelve (texto_limpio, datos).

    Si el bloque no existe o es inválido, devuelve (texto_original, None).
    """
    m = _RADAR_RE.search(texto)
    if not m:
        return texto, None
    raw_json = m.group(1).strip()
    clean = texto[: m.start()].rstrip()
    try:
        data = json.loads(raw_json)
        return clean, data
    except json.JSONDecodeError:
        logger.warning("radar_json no parseable — fallback a placeholder. Raw: %r", raw_json[:120])
        return clean, None


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
        sector_gics_code: str | None = None,
        empresa_id=None,
    ) -> CapBenchmarking:
        # Queries específicas de perfil de empresa (no overviews de sector) con
        # search_depth="advanced": Tavily recupera contenido más profundo, necesario
        # para poblar las fichas de competidor de la sección 2.1 (DT-035).
        queries = [
            f"{sector_gics} principales empresas competidoras Colombia cuota de mercado 2025",
            f"{sector_gics} líderes globales del sector perfil estratégico portafolio",
            f"{sector_gics} referentes regionales LatAm empresas emergentes disruptores",
        ]
        for query in queries:
            web_results = self._web_connector.search(query, search_depth="advanced")
            if web_results:
                self._store.ingest(
                    texts=[r.content for r in web_results],
                    fuente_tipo="web",
                    urls=[r.url for r in web_results],
                )

        chunks = self._store.search(
            f"{sector_gics} competitors benchmarking {nombre_empresa}",
            sector_gics=sector_gics_code, empresa_id=empresa_id,
        )

        if not check_retrieval_sufficient(chunks, min_chunks=_MIN_CHUNKS):
            return CapBenchmarking(
                texto=build_absent_paragraph("Cap 2 — Análisis Competitivo"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context = format_chunks_as_context(chunks)
        texto_raw = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_competidores": context,
        })

        if has_cjk_characters(texto_raw):
            return CapBenchmarking(
                texto=build_absent_paragraph(
                    "Cap 2 — Análisis Competitivo",
                    "El modelo generó texto en un idioma incorrecto (no español)",
                ),
                n_chunks_usados=len(chunks),
                retrieval_suficiente=False,
                chunks_usados=chunks,
            )

        # T16.1: extraer bloque radar_json; si parseable, adjuntar en radar_data
        texto, radar_data = _extract_radar(texto_raw)

        return CapBenchmarking(
            texto=texto,
            n_chunks_usados=len(chunks),
            retrieval_suficiente=True,
            chunks_usados=chunks,
            radar_data=radar_data,
        )
