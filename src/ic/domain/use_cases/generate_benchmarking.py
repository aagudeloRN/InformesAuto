"""Caso de uso: Generar Capitulo 2 - Analisis Competitivo (Benchmarking).

Genera el analisis competitivo y benchmarking para la empresa objetivo.
La seccion 2.1 (Jugadores Clave) se delega a Generate21Jugadores o se ensambla
directamente desde el Knowledge Base.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_02b_entidades import MAX_ENTIDADES, parse_entidades
from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.domain.kb.relevance import format_referentes_globales
from ic.domain.kb.seccion21_assembler import assemble_seccion_21
from ic.domain.kb.seccion21_holes import fill_holes
from ic.domain.use_cases._benchmarking_matrix import (
    enriquecer_globales_web,
)
from ic.domain.use_cases._benchmarking_matrix import (
    load_sector_cache as _load_sector_cache,
)
from ic.shared.protocols import InvokableChain as Runnable
from ic.shared.text_utils import has_cjk_characters, is_llm_refusal
from ic.shared.types import CapBenchmarking

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from ic.domain.use_cases.generate_21_jugadores import Generate21Jugadores
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.web_connector import WebConnector

logger = logging.getLogger(__name__)

_MIN_CHUNKS = 5


def _requiere_reintento(texto: str) -> bool:
    """El texto no es una redaccion valida: negativa del LLM o idioma incorrecto."""
    return is_llm_refusal(texto) or has_cjk_characters(texto)


class GenerateBenchmarking:
    def __init__(
        self,
        chain: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        entidades_chain: Runnable | None = None,
        kb_competidores: list[str] | None = None,
        kb_locales: list[str] | None = None,
        jugadores_locales_ctx: str = "",
        fichas_conocidas_ctx: str = "",
        escalation_chain: Runnable | None = None,
        seccion21_enabled: bool = False,
        tiers: dict[str, list[str]] | None = None,
        fichas_kb: dict[str, dict[str, str]] | None = None,
        holes_chain: Runnable | None = None,
        holefill_max: int = 3,
        jugadores_use_case: Generate21Jugadores | None = None,
        sectores_ancla: list[str] | None = None,
        sub_gics: str | None = None,
        engine: Engine | None = None,
        run_key: str | None = None,
    ) -> None:
        self._chain = chain
        self._store = store
        self._web_connector = web_connector
        self._entidades_chain = entidades_chain
        self._kb_competidores = kb_competidores or []
        self._kb_locales = kb_locales or []
        self._jugadores_locales_ctx = jugadores_locales_ctx or ""
        self._fichas_conocidas_ctx = fichas_conocidas_ctx or ""
        self._escalation_chain = escalation_chain
        self._seccion21_enabled = seccion21_enabled and bool(tiers)
        self._tiers = tiers or {}
        self._fichas_kb = fichas_kb or {}
        self._holes_chain = holes_chain
        self._holefill_max = holefill_max
        self._jugadores_use_case = jugadores_use_case
        self._sectores_ancla = sectores_ancla or []
        self._sub_gics = sub_gics
        self._engine = engine
        self._run_key = run_key

    def _identificar_entidades(self, chunks: list[Any], sector_gics: str) -> list[str]:
        raw = self._entidades_chain.invoke(
            {
                "sector_gics": sector_gics,
                "retrieval_competidores": format_chunks_as_context(chunks),
            }
        )
        del_llm = parse_entidades(raw)
        fusionadas: list[str] = []
        vistos: set[str] = set()
        for nombre in [*self._kb_competidores, *self._kb_locales, *del_llm]:
            clave = nombre.casefold()
            if clave in vistos:
                continue
            vistos.add(clave)
            fusionadas.append(nombre)
            if len(fusionadas) >= MAX_ENTIDADES:
                break
        return fusionadas

    def _buscar_por_entidad(self, entidades: list[str], sector_gics: str) -> None:
        for entidad in entidades:
            query = (
                f"{entidad} {sector_gics} perfil empresa portafolio productos "
                "cuota de mercado Colombia"
            )
            results = self._web_connector.search(query, search_depth="advanced")
            if results:
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )

    def _redactar_con_escalada(self, payload: dict[str, Any]) -> str:
        texto = self._chain.invoke(payload)
        if not _requiere_reintento(texto):
            return texto
        logger.info("Cap 2: respuesta no valida. Reintentando con el primario.")
        texto = self._chain.invoke(payload)
        if not _requiere_reintento(texto) or self._escalation_chain is None:
            return texto
        logger.info("Cap 2: negativa persistente tras retry. Escalando a tier superior.")
        return self._escalation_chain.invoke(payload)

    def _enriquecer_globales_web(
        self,
        globales: list[str],
        sector_gics: str,
        sector_gics_code: str | None,
        top_n: int = 3,
    ) -> dict[str, dict[str, str]]:
        return enriquecer_globales_web(
            web_connector=self._web_connector,
            llm=None,
            engine=self._engine,
            fichas_kb=self._fichas_kb,
            globales=globales,
            sector_gics=sector_gics,
            sector_gics_code=sector_gics_code,
        )

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
        sector_gics_code: str | None = None,
        empresa_id: Any = None,
    ) -> CapBenchmarking:
        queries = [
            f"{sector_gics} principales empresas competidoras Colombia cuota de mercado 2025",
            f"{sector_gics} lideres globales del sector perfil estrategico portafolio",
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

        retrieval_query = f"{sector_gics} competitors benchmarking {nombre_empresa}"
        chunks = self._store.search(
            retrieval_query,
            sector_gics=sector_gics_code,
            empresa_id=empresa_id,
        )

        if self._entidades_chain is not None and check_retrieval_sufficient(
            chunks, min_chunks=_MIN_CHUNKS
        ):
            entidades = self._identificar_entidades(chunks, sector_gics)
            if entidades:
                self._buscar_por_entidad(entidades, sector_gics)
                chunks = self._store.search(
                    retrieval_query,
                    sector_gics=sector_gics_code,
                    empresa_id=empresa_id,
                )

        if not check_retrieval_sufficient(chunks, min_chunks=_MIN_CHUNKS):
            return CapBenchmarking(
                texto=build_absent_paragraph("Cap 2 — Análisis Competitivo"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context = format_chunks_as_context(chunks)
        payload: dict[str, Any] = {
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_competidores": context,
            "jugadores_locales": self._jugadores_locales_ctx,
            "referentes_globales_anclados": format_referentes_globales(self._kb_competidores),
            "fichas_conocidas": self._fichas_conocidas_ctx,
        }

        seccion_21_md = ""
        if self._jugadores_use_case is not None:
            try:
                cached_glob = cached_reg = cached_start = None
                sub_key = self._sub_gics or "any"
                sector_run_key = (
                    f"sector_{sector_gics_code}_{sub_key}" if sector_gics_code else None
                )
                if self._engine is not None and sector_run_key is not None:
                    cached_glob, cached_reg, cached_start = _load_sector_cache(
                        self._engine, sector_run_key
                    )
                cap21 = self._jugadores_use_case.execute(
                    nombre_empresa=nombre_empresa,
                    descripcion_empresa=descripcion_empresa,
                    sector_gics=sector_gics,
                    sector_gics_code=sector_gics_code,
                    sectores_ancla=self._sectores_ancla or [sector_gics_code or sector_gics],
                    empresa_id=empresa_id,
                    cached_globales=cached_glob,
                    cached_regionales=cached_reg,
                    cached_startups=cached_start,
                    engine=self._engine,
                    run_key=sector_run_key,
                )
                if cap21.retrieval_suficiente:
                    seccion_21_md = cap21.texto
            except Exception as exc:
                logger.warning("Generate21Jugadores fallo: %s", exc)

        if not seccion_21_md and self._seccion21_enabled:
            globales = self._tiers.get("global", [])
            nuevos_web = self._enriquecer_globales_web(globales, sector_gics, sector_gics_code)
            fichas_para_fill = {n: dict(c) for n, c in self._fichas_kb.items()}
            for n, c in nuevos_web.items():
                fichas_para_fill.setdefault(n, {}).update(c)
            fichas_enr, _ = fill_holes(
                self._tiers,
                fichas_para_fill,
                self._holes_chain,
                sector_gics,
                context,
                self._holefill_max,
            )
            seccion_21_md = assemble_seccion_21(self._tiers, fichas_enr)

        if seccion_21_md:
            payload["seccion_21_context"] = seccion_21_md
            payload["fichas_conocidas"] = ""

        texto_raw = self._redactar_con_escalada(payload)

        if has_cjk_characters(texto_raw):
            return CapBenchmarking(
                texto=build_absent_paragraph(
                    "Cap 2 — Análisis Competitivo",
                    "El modelo genero texto en un idioma incorrecto (no espanol)",
                ),
                n_chunks_usados=len(chunks),
                retrieval_suficiente=False,
                chunks_usados=chunks,
            )

        if is_llm_refusal(texto_raw):
            return CapBenchmarking(
                texto=build_absent_paragraph(
                    "Cap 2 — Análisis Competitivo",
                    "El modelo no pudo redactar las fichas de competidores con las fuentes dadas",
                ),
                n_chunks_usados=len(chunks),
                retrieval_suficiente=False,
                chunks_usados=chunks,
            )

        texto = (seccion_21_md + "\n\n" + texto_raw) if seccion_21_md else texto_raw
        return CapBenchmarking(
            texto=texto.strip(),
            n_chunks_usados=len(chunks),
            retrieval_suficiente=True,
            chunks_usados=chunks,
            radar_data=None,
        )
