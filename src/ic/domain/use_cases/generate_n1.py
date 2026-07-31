"""Paralelización N1: Caps 2 (Benchmarking), 3 (Tendencias) y 4 (Ecosistema).

Extraído de generate_informe.py (DT-004) para mantener archivos < 300 líneas.
El orquestador (GenerateInforme._run_n1) delega aquí sin cambiar la interfaz pública.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext

logger = logging.getLogger(__name__)


def run_n1_parallel(ctx: _PipelineContext) -> None:
    """Ejecuta Caps 2/3/4 en paralelo + párrafos introductivos N1."""
    from ic.data.database import SessionLocal
    from ic.data.models.entidad import ensure_entidades_tables
    from ic.data.repositories.embedding_repo import EmbeddingRepository
    from ic.data.repositories.entidad_repo import EntidadRepository
    from ic.domain.chains.chain_02b_entidades import build_chain_entidades
    from ic.domain.chains.chain_03_benchmarking import build_chain_03
    from ic.domain.chains.chain_03b_mercado import build_chain_03b
    from ic.domain.chains.chain_04_tendencias import build_chain_04
    from ic.domain.chains.chain_05_ecosistema import build_chain_05
    from ic.domain.chains.chain_judge import CRITERIOS_CAPITULO
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
    from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
    from ic.domain.use_cases.generate_mercado import GenerateMercado
    from ic.domain.use_cases.generate_tendencias import GenerateTendencias
    from ic.domain.use_cases.self_review_hooks import review_web_cap
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.cached_connector import (
        CachedOpenAlexConnector,
        CachedWebConnector,
    )
    from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
    from ic.shared.constants.gics_groups import extract_gics_code, resolve_sub_gics

    ctx.step_fn(3, "N1 — Caps 2/3/4 en paralelo")
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings
    g_code = extract_gics_code(g)
    # DT-061: sub-código GICS de la empresa analizada (food/beverage/tobacco dentro del grupo) para
    # anclar competidores de la MISMA sub-actividad. None → anclaje a nivel de grupo (invariante).
    sub_code = resolve_sub_gics(ctx.empresa.texto, g_code)

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
        # T22.4 (DT-054): cadena de identificación de entidades para búsqueda dirigida por
        # competidor (enriquece las fichas de 2.1 más allá de las queries a nivel sector).
        # DT-056/T3: anclar con la lista canónica del KB por sector (cierra causas A/E). Sesión
        # propia por thread; [] → comportamiento B1 (SQLAlchemy Session no es thread-safe).
        kb_competidores: list[str] = []
        try:
            with SessionLocal() as db_kb:
                ensure_entidades_tables(db_kb.get_bind())
                kb_competidores = EntidadRepository(db_kb).list_competidores_by_sector(
                    g_code or "", sub_gics=sub_code
                )
        except Exception:  # noqa: BLE001 — el KB es un boost; nunca debe romper la corrida.
            logger.warning("No se pudo consultar el KB de competidores (sector %s)", g_code)
        cap = GenerateBenchmarking(
            chain=build_chain_03(ctx.api_llm or ctx.llm), store=store, web_connector=web,
            entidades_chain=build_chain_entidades(ctx.api_llm or ctx.llm),
            kb_competidores=kb_competidores,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )
        # DT-059/T3: auto-revisión sabor web (re-busca por faltantes + KB). Flag OFF = no-op.
        return review_web_cap(
            settings=s, llm=ctx.api_llm or ctx.llm,
            capitulo_nombre="Cap 2 — Análisis Competitivo",
            criterios=CRITERIOS_CAPITULO["Cap 2 — Análisis Competitivo"],
            cap_obj=cap, run_key=ctx.run_key, store=store, web=web,
            sector_gics=g, sector_gics_code=g_code, empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} competitors benchmarking {e}",
            kb_competidores=kb_competidores,
        )

    def _fn_mercado(store, web, _oal):
        if ctx.api_llm is None:
            return None
        return GenerateMercado(
            chain=build_chain_03b(ctx.api_llm), store=store, web_connector=web
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )

    def _fn_cap3(store, web, oal):
        if ctx.api_llm is None:
            return None
        cap = GenerateTendencias(
            chain=build_chain_04(ctx.api_llm), store=store,
            web_connector=web, openalex_connector=oal,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )
        return review_web_cap(
            settings=s, llm=ctx.api_llm,
            capitulo_nombre="Cap 3 — Análisis Sectorial Tendencial",
            criterios=CRITERIOS_CAPITULO["Cap 3 — Análisis Sectorial Tendencial"],
            cap_obj=cap, run_key=ctx.run_key, store=store, web=web,
            sector_gics=g, sector_gics_code=g_code, empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} tendencias sectoriales tecnológicas {e}",
        )

    def _fn_cap4(store, web, _oal):
        if ctx.api_llm is None:
            return None
        cap = GenerateEcosistema(
            chain=build_chain_05(ctx.api_llm), store=store, web_connector=web,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )
        return review_web_cap(
            settings=s, llm=ctx.api_llm,
            capitulo_nombre="Cap 4 — Panorama Ecosistema",
            criterios=CRITERIOS_CAPITULO["Cap 4 — Panorama Ecosistema"],
            cap_obj=cap, run_key=ctx.run_key, store=store, web=web,
            sector_gics=g, sector_gics_code=g_code, empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} ecosistema inversiones fusiones adquisiciones alianzas {e}",
        )

    # T22.3 (DT-030): --resume salta los caps ya persistidos; solo se computan los faltantes.
    from ic.domain.use_cases import checkpoint_hooks

    _fns = {"cap2": _fn_cap2, "mercado": _fn_mercado, "cap3": _fn_cap3, "cap4": _fn_cap4}
    _restored = {name: checkpoint_hooks.restore(ctx, name) for name in _fns}
    _results: dict = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        _futures = {
            name: pool.submit(_store, fn)
            for name, fn in _fns.items()
            if _restored[name] is None
        }
    for name in _fns:
        _results[name] = (
            _restored[name] if _restored[name] is not None else _futures[name].result()
        )
    ctx.cap, ctx.cap_mercado = _results["cap2"], _results["mercado"]
    ctx.cap_tend, ctx.cap_eco = _results["cap3"], _results["cap4"]

    ctx.step_fn(4, "Párrafos introductorios N1")
    if ctx.intro_chain is not None:
        # El intro se aplica solo a caps recién computados; los restaurados ya lo incluyen.
        for cap_obj, titulo, name in [
            (ctx.cap, "Análisis Competitivo", "cap2"),
            (ctx.cap_tend, "Análisis Sectorial Tendencial", "cap3"),
            (ctx.cap_eco, "Ecosistema Empresarial", "cap4"),
        ]:
            if _restored[name] is None and cap_obj is not None and cap_obj.retrieval_suficiente:
                intro = ctx.intro_chain.invoke({
                    "titulo": titulo, "empresa": ctx.params.empresa,
                    "resumen_cap": cap_obj.texto[:500],
                })
                # DT-055: intro saneado puede quedar vacío → no anteponer líneas en blanco
                if intro:
                    cap_obj.texto = intro + "\n\n" + cap_obj.texto

    # Persistir los caps recién computados (con intro aplicado) para poder reanudar.
    for name, obj in [
        ("cap2", ctx.cap), ("mercado", ctx.cap_mercado),
        ("cap3", ctx.cap_tend), ("cap4", ctx.cap_eco),
    ]:
        if _restored[name] is None:
            checkpoint_hooks.save(ctx, name, obj)
