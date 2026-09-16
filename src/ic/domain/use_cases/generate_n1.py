"""Paralelizacion N1: Caps 2 (Benchmarking), 3 (Tendencias) y 4 (Ecosistema).

Extraido de generate_informe.py (DT-004) para mantener archivos < 300 lineas.
El orquestador (GenerateInforme._run_n1) delega aqui sin cambiar la interfaz publica.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from ic.data.database import SessionLocal
from ic.data.database import engine as db_engine
from ic.data.repositories.embedding_repo import EmbeddingRepository
from ic.domain.chains.chain_02b_entidades import build_chain_entidades
from ic.domain.chains.chain_02c_pares_globales import build_chain_pares_globales
from ic.domain.chains.chain_03_benchmarking import build_chain_03
from ic.domain.chains.chain_03b_ficha_fields import build_chain_ficha_fields
from ic.domain.chains.chain_cap2_21_globales import build_chain_cap2_21_globales
from ic.domain.chains.chain_cap2_21_regionales import build_chain_cap2_21_regionales
from ic.domain.chains.chain_cap2_21_startups import build_chain_cap2_21_startups
from ic.domain.chains.chain_judge import CRITERIOS_CAPITULO
from ic.domain.use_cases import checkpoint_hooks
from ic.domain.use_cases._n1_cap2_helpers import (
    cargar_kb_competidores_ancla,
    descubrir_globales,
    persistir_fichas_ancladas,
)
from ic.domain.use_cases._n1_chapter_builders import (
    apply_n1_intros,
    build_fn_cap3_impl,
    build_fn_cap4_impl,
    build_fn_mercado_impl,
)
from ic.domain.use_cases.generate_21_globales import Generate21Globales
from ic.domain.use_cases.generate_21_jugadores import Generate21Jugadores
from ic.domain.use_cases.generate_21_regionales import Generate21Regionales
from ic.domain.use_cases.generate_21_startups import Generate21Startups
from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
from ic.domain.use_cases.generate_n1_cap22 import build_fn_cap2_with_22
from ic.domain.use_cases.self_review_hooks import review_web_cap
from ic.infrastructure.llm.gateway import build_api_llm
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.cached_connector import (
    CachedOpenAlexConnector,
    CachedWebConnector,
)
from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
from ic.shared.constants.ciiu_gics import sectores_ancla_local
from ic.shared.constants.gics_groups import extract_gics_code
from ic.shared.text_productos import producto_terms

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext

logger = logging.getLogger(__name__)


def run_n1_parallel(ctx: _PipelineContext) -> None:
    """Ejecuta Caps 2/3/4 en paralelo + parrafos introductivos N1."""
    ctx.step_fn(3, "N1 ? Caps 2/3/4 en paralelo")
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings
    g_code = extract_gics_code(g)
    productos = ctx.empresa.productos_servicios
    productos_terms = producto_terms(productos)
    ciiu_ancla = getattr(ctx.empresa, "actividad_ciiu", None) or ctx.params.ciiu
    sectores_local = sectores_ancla_local(g_code, ciiu_ancla)

    def _store(fn: Any):
        with SessionLocal() as db:
            store = PGVectorStore(ctx.embedder, EmbeddingRepository(db), s)
            store.session_id = ctx.session_id
            cached_web = CachedWebConnector(ctx.web, db, s, counter=ctx.cache_web_counter)
            cached_oal = CachedOpenAlexConnector(
                OpenAlexConnector(s), db, s, counter=ctx.cache_oal_counter
            )
            return fn(store, cached_web, cached_oal)

    def _fn_cap2(store: Any, web: Any, _oal: Any):
        if s.discover_globales_enabled:
            descubrir_globales(ctx, store, web, g_code, sectores_local, productos_terms)
        try:
            with SessionLocal() as db_kb:
                (
                    kb_competidores,
                    kb_locales,
                    jugadores_locales_ctx,
                    fichas_conocidas_ctx,
                    tiers_ancla,
                    fichas_kb,
                ) = cargar_kb_competidores_ancla(
                    db_kb, s, g_code, sectores_local, productos_terms, e
                )
        except Exception:
            logger.warning("No se pudo consultar el KB de competidores (sector %s)", g_code)
            kb_competidores, kb_locales = [], []
            jugadores_locales_ctx, fichas_conocidas_ctx = "", ""
            tiers_ancla, fichas_kb = {}, {}

        b2_on = s.seccion21_determinista_enabled and bool(fichas_kb)
        holes_llm = ctx.api_llm_synth or ctx.api_llm or ctx.llm
        holes_chain = build_chain_ficha_fields(holes_llm) if b2_on else None
        escalation_chain = None
        if s.openrouter_api_key:
            tier = getattr(s, "benchmarking_escalation_tier", "synth")
            try:
                escalation_chain = build_chain_03(
                    build_api_llm(s, tier=tier, cost_tracker=ctx.tracker),
                    omitir_21=b2_on,
                )
            except Exception:
                logger.warning("No se pudo construir la cadena de escalada (tier=%s)", tier)
        llm_21 = ctx.api_llm or ctx.llm
        jugadores_use_case = Generate21Jugadores(
            gen_globales=Generate21Globales(
                chain_candidatos=build_chain_pares_globales(llm_21),
                chain_perfil=build_chain_cap2_21_globales(llm_21),
                store=store,
                web_connector=web,
            ),
            gen_regionales=Generate21Regionales(
                chain_perfil=build_chain_cap2_21_regionales(llm_21),
                store=store,
                web_connector=web,
            ),
            gen_startups=Generate21Startups(
                chain_perfil=build_chain_cap2_21_startups(llm_21),
                store=store,
                web_connector=web,
                db_factory=SessionLocal,
            ),
        )
        cap = GenerateBenchmarking(
            chain=build_chain_03(ctx.api_llm or ctx.llm, omitir_21=b2_on),
            store=store,
            web_connector=web,
            entidades_chain=build_chain_entidades(ctx.api_llm or ctx.llm),
            kb_competidores=kb_competidores,
            kb_locales=kb_locales,
            jugadores_locales_ctx=jugadores_locales_ctx,
            fichas_conocidas_ctx=fichas_conocidas_ctx,
            escalation_chain=escalation_chain,
            seccion21_enabled=b2_on,
            tiers=tiers_ancla,
            fichas_kb=fichas_kb,
            holes_chain=holes_chain,
            holefill_max=s.seccion21_holefill_max,
            jugadores_use_case=jugadores_use_case,
            engine=db_engine,
            sub_gics=g_code,
        ).execute(
            nombre_empresa=e,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
        )
        cap = review_web_cap(
            settings=s,
            llm=ctx.api_llm or ctx.llm,
            capitulo_nombre="Cap 2 ? An?lisis Competitivo",
            criterios=CRITERIOS_CAPITULO["Cap 2 ? An?lisis Competitivo"],
            cap_obj=cap,
            run_key=ctx.run_key,
            store=store,
            web=web,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} competitors benchmarking {e}",
            kb_competidores=kb_competidores,
            jugadores_locales_ctx=jugadores_locales_ctx,
        )
        persistir_fichas_ancladas(cap, kb_competidores, kb_locales, g_code)
        return cap

    _fns = {
        "cap2": build_fn_cap2_with_22(_fn_cap2, ctx),
        "mercado": build_fn_mercado_impl(ctx, g_code),
        "cap3": build_fn_cap3_impl(ctx, g_code),
        "cap4": build_fn_cap4_impl(ctx, g_code),
    }

    _caps = ctx.params.caps_incluidos
    if _caps is not None:
        _fns = {k: v for k, v in _fns.items() if k in ("cap2", "mercado") or k in _caps}

    _restored = {name: checkpoint_hooks.restore(ctx, name) for name in _fns}
    _results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        _futures = {
            name: pool.submit(_store, fn) for name, fn in _fns.items() if _restored[name] is None
        }
    for name in _fns:
        _results[name] = _restored[name] if _restored[name] is not None else _futures[name].result()

    ctx.cap, ctx.cap_mercado = _results.get("cap2"), _results.get("mercado")
    ctx.cap_tend, ctx.cap_eco = _results.get("cap3"), _results.get("cap4")

    ctx.step_fn(4, "P?rrafos introductorios N1")
    apply_n1_intros(ctx, _restored)

    _slots = {
        "cap2": "cap",
        "mercado": "cap_mercado",
        "cap3": "cap_tend",
        "cap4": "cap_eco",
    }
    for name, obj in [
        ("cap2", ctx.cap),
        ("mercado", ctx.cap_mercado),
        ("cap3", ctx.cap_tend),
        ("cap4", ctx.cap_eco),
    ]:
        if name in _restored and _restored[name] is None:
            setattr(ctx, _slots[name], checkpoint_hooks.commit_best(ctx, name, obj))
