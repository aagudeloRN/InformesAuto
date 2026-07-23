"""Paralelización N1: Caps 2 (Benchmarking), 3 (Tendencias) y 4 (Ecosistema).

Extraído de generate_informe.py (DT-004) para mantener archivos < 300 líneas.
El orquestador (GenerateInforme._run_n1) delega aquí sin cambiar la interfaz pública.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext


def run_n1_parallel(ctx: _PipelineContext) -> None:
    """Ejecuta Caps 2/3/4 en paralelo + párrafos introductivos N1."""
    from ic.data.database import SessionLocal
    from ic.data.repositories.embedding_repo import EmbeddingRepository
    from ic.domain.chains.chain_03_benchmarking import build_chain_03
    from ic.domain.chains.chain_04_tendencias import build_chain_04
    from ic.domain.chains.chain_05_ecosistema import build_chain_05
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
    from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
    from ic.domain.use_cases.generate_tendencias import GenerateTendencias
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.cached_connector import (
        CachedOpenAlexConnector,
        CachedWebConnector,
    )
    from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
    from ic.shared.constants.gics_groups import extract_gics_code

    ctx.step_fn(3, "N1 — Caps 2/3/4 en paralelo")
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings
    g_code = extract_gics_code(g)

    # T16.0-B: cada thread abre su propia sesión y crea sus propios wrappers cached.
    # SQLAlchemy Session no es thread-safe — nunca compartir entre threads paralelos.
    def _store(fn):
        with SessionLocal() as db:
            store = PGVectorStore(ctx.embedder, EmbeddingRepository(db), s)
            store.session_id = ctx.session_id
            cached_web = CachedWebConnector(ctx.web, db, s, counter=ctx.cache_web_counter)
            cached_oal = CachedOpenAlexConnector(
                OpenAlexConnector(s), db, s, counter=ctx.cache_oal_counter
            )
            return fn(store, cached_web, cached_oal)

    def _fn_cap2(store, web, _oal):
        return GenerateBenchmarking(
            chain=build_chain_03(ctx.api_llm or ctx.llm), store=store, web_connector=web
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )

    def _fn_cap3(store, web, oal):
        if ctx.api_llm is None:
            return None
        return GenerateTendencias(
            chain=build_chain_04(ctx.api_llm), store=store,
            web_connector=web, openalex_connector=oal,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )

    def _fn_cap4(store, web, _oal):
        if ctx.api_llm is None:
            return None
        return GenerateEcosistema(
            chain=build_chain_05(ctx.api_llm), store=store, web_connector=web,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        f2 = pool.submit(_store, _fn_cap2)
        f3 = pool.submit(_store, _fn_cap3)
        f4 = pool.submit(_store, _fn_cap4)
    ctx.cap, ctx.cap_tend, ctx.cap_eco = f2.result(), f3.result(), f4.result()

    ctx.step_fn(4, "Párrafos introductorios N1")
    if ctx.intro_chain is not None:
        for cap_obj, titulo in [
            (ctx.cap, "Análisis Competitivo"),
            (ctx.cap_tend, "Análisis Sectorial Tendencial"),
            (ctx.cap_eco, "Ecosistema Empresarial"),
        ]:
            if cap_obj is not None and cap_obj.retrieval_suficiente:
                intro = ctx.intro_chain.invoke({
                    "titulo": titulo, "empresa": ctx.params.empresa,
                    "resumen_cap": cap_obj.texto[:500],
                })
                cap_obj.texto = intro + "\n\n" + cap_obj.texto
