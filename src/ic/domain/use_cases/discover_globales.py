"""DT-062 — descubrimiento de competidores globales recomendados por LLM y corroborados por web.

Motor de recall del componente de clase mundial (2.1.1): el LLM propone actores globales
representativos del sector (nombres); cada candidato dispara una búsqueda web dirigida y solo los
que la evidencia corrobora (umbral ``min_corrob``) se siembran como ``verificado`` /
``alcance=global`` (RN-001/TIER 4: ningún nombre se cita sin corroboración). Reusa identificar→
enriquecer de ``GenerateBenchmarking``: la ingesta web de los corroborados deja evidencia para que
la síntesis pueda citarlos.

``domain/`` no ve BD: la persistencia se inyecta como ``seed_repo_fn`` (callback). El wrapper de la
capa de datos decide el ``EntidadRow`` según ``corroborado``. Modelo por gateway (ADR-002).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from langchain_core.runnables import Runnable

from ic.domain.chains.chain_02c_pares_globales import parse_pares_globales
from ic.domain.kb.corroboracion import contar_corroboracion, es_corroborado
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector

logger = logging.getLogger(__name__)

# Callback de persistencia: (nombre, corroborado, hits) → el wrapper de datos siembra el EntidadRow.
SeedRepoFn = Callable[[str, bool, int], None]


class DiscoverGlobales:
    def __init__(
        self,
        chain: Runnable,
        web_connector: WebConnector,
        store: PGVectorStore,
        min_corrob: int = 2,
        force_ddg: bool = False,
    ) -> None:
        self._chain = chain
        self._web_connector = web_connector
        self._store = store
        self._min_corrob = min_corrob
        # DT-065: forzar DuckDuckGo (gratis) para el pre-warm por lotes, sin gastar Tavily.
        self._force_ddg = force_ddg

    def discover(
        self,
        sector_gics: str,
        productos: str,
        seed_repo_fn: SeedRepoFn,
    ) -> dict[str, int]:
        """Recomienda globales, corrobora por web y siembra vía callback. Devuelve conteos.

        Corroborado (≥ ``min_corrob`` fuentes mencionan el nombre): ingesta la evidencia web y
        siembra (``verificado``/``alcance=global``). No corroborado: siembra solo como candidato
        (``fuente=llm``, sin ``alcance=global`` → nunca entra al anclaje 2.1.1); no se ingiere.
        """
        # DT-063: steerear el recall del LLM por los PRODUCTOS/SERVICIOS de la empresa analizada
        # (señal de precisión), con el sector solo como límite de dominio. Reemplaza el sub-código
        # GICS (frágil): así una láctea recibe globales de lácteos, no del grupo entero.
        raw = self._chain.invoke({
            "sector_gics": sector_gics,
            "productos": productos or "(no especificados; usar el sector como referencia)",
        })
        candidatos = parse_pares_globales(raw)
        corroborados = 0
        for nombre in candidatos:
            query = f"{nombre} {sector_gics} global company profile revenue market share"
            results = self._web_connector.search(
                query, search_depth="advanced", force_ddg=self._force_ddg
            )
            hits = contar_corroboracion(nombre, [r.content for r in results])
            corroborado = es_corroborado(hits, self._min_corrob)
            if corroborado:
                corroborados += 1
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )
            seed_repo_fn(nombre, corroborado, hits)
        conteos = {
            "recomendados": len(candidatos),
            "corroborados": corroborados,
            "no_corroborados": len(candidatos) - corroborados,
        }
        logger.info(
            "DiscoverGlobales sector=%s productos=%r: %s", sector_gics, productos[:80], conteos
        )
        return conteos
