"""Sub-orquestador para Cap 2 (Analisis Competitivo) en N1."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ic.data.database import SessionLocal
from ic.data.database import engine as db_engine
from ic.data.models.entidad import (
    ALCANCE_GLOBAL,
    ESTADO_CANDIDATO,
    ESTADO_VERIFICADO,
    FUENTE_LLM,
    FUENTE_WEB,
    SEGMENTO_STARTUP,
    TIPO_COMPETIDOR,
    ensure_entidades_tables,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow
from ic.domain.chains.chain_02b_entidades import build_chain_entidades
from ic.domain.chains.chain_02c_pares_globales import build_chain_pares_globales
from ic.domain.chains.chain_03_benchmarking import build_chain_03
from ic.domain.chains.chain_03b_ficha_fields import build_chain_ficha_fields
from ic.domain.chains.chain_cap2_21_globales import build_chain_cap2_21_globales
from ic.domain.chains.chain_cap2_21_regionales import build_chain_cap2_21_regionales
from ic.domain.chains.chain_cap2_21_startups import build_chain_cap2_21_startups
from ic.domain.chains.chain_judge import CRITERIOS_CAPITULO
from ic.domain.kb.ficha_parser import (
    TIER_GLOBAL,
    TIER_REGIONAL,
    TIER_STARTUP,
    parse_fichas_competidores,
)
from ic.domain.kb.relevance import format_fichas_conocidas, format_jugadores_locales
from ic.domain.use_cases.discover_globales import DiscoverGlobales
from ic.domain.use_cases.generate_21_globales import Generate21Globales
from ic.domain.use_cases.generate_21_jugadores import Generate21Jugadores
from ic.domain.use_cases.generate_21_regionales import Generate21Regionales
from ic.domain.use_cases.generate_21_startups import Generate21Startups
from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
from ic.domain.use_cases.self_review_hooks import review_web_cap
from ic.infrastructure.llm.gateway import build_api_llm
from ic.infrastructure.ner.entity_recognizer import normalize_entity

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext

logger = logging.getLogger(__name__)


def descubrir_globales(
    ctx: _PipelineContext,
    store: Any,
    web: Any,
    g_code: str,
    sectores_local: list[str],
    productos_terms: set[str],
) -> None:
    """Descubrimiento LLM de pares globales corroborados por web."""
    if not g_code:
        return
    e = ctx.params.empresa
    g, s = ctx.gics.grupo_gics, ctx.settings
    productos = ctx.empresa.productos_servicios
    try:
        with SessionLocal() as db_kb:
            ensure_entidades_tables(db_kb.get_bind())
            repo = EntidadRepository(db_kb)
            ya = repo.list_competidores_by_sector(
                sectores_local,
                productos_terms=productos_terms,
                alcance=ALCANCE_GLOBAL,
                limit=100,
                exclude_nombre=e,
            )
            if len(ya) >= 8:
                return

            def _seed(nombre: str, corroborado: bool, _hits: int) -> None:
                estado = ESTADO_VERIFICADO if corroborado else ESTADO_CANDIDATO
                eid = repo.upsert_entidad(
                    EntidadRow(
                        nombre=nombre,
                        nombre_normalizado=normalize_entity(nombre),
                        tipo=TIPO_COMPETIDOR,
                        sector_gics=g_code,
                        alcance=ALCANCE_GLOBAL if corroborado else None,
                        estado=estado,
                    )
                )
                repo.add_atributo(
                    eid,
                    "origen",
                    "llm-corroborado" if corroborado else "llm",
                    FUENTE_LLM,
                    estado=estado,
                )
                if corroborado and productos:
                    repo.add_atributo(
                        eid,
                        "productos_perfil",
                        productos[:2000],
                        FUENTE_LLM,
                        estado=ESTADO_VERIFICADO,
                    )

            DiscoverGlobales(
                chain=build_chain_pares_globales(ctx.api_llm or ctx.llm),
                web_connector=web,
                store=store,
                min_corrob=s.discover_globales_min_corrob,
            ).discover(sector_gics=g, productos=productos, seed_repo_fn=_seed)
    except Exception:
        logger.warning("Descubrimiento LLM de globales fallo (sector %s)", g_code)


def persistir_fichas_ancladas(
    cap: Any, kb_competidores: list[str], kb_locales: list[str], g_code: str
) -> None:
    """Persiste los campos de ficha de los competidores anclados."""
    if cap is None or not getattr(cap, "texto", ""):
        return
    anclados = {normalize_entity(n) for n in (*kb_competidores, *kb_locales)}
    if not anclados:
        return
    try:
        fichas = [
            f
            for f in parse_fichas_competidores(cap.texto)
            if normalize_entity(f.nombre) in anclados
        ]
        if not fichas:
            return
        with SessionLocal() as db_p:
            ensure_entidades_tables(db_p.get_bind())
            repo_p = EntidadRepository(db_p)
            for f in fichas:
                ent_id = repo_p.get_id_by_nombre_sector(normalize_entity(f.nombre), g_code)
                if ent_id is None:
                    continue
                for clave, valor in f.campos.items():
                    repo_p.add_atributo(ent_id, clave, valor, FUENTE_WEB)
    except Exception:
        logger.warning("No se pudieron persistir las fichas del Cap 2", exc_info=True)


def build_fn_cap2_impl(
    ctx: _PipelineContext,
    g_code: str,
    sectores_local: list[str],
    productos_terms: set[str],
):
    """Construye el ejecutor para Cap 2."""
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings

    def _fn_cap2(store: Any, web: Any, _oal: Any):
        if s.discover_globales_enabled:
            descubrir_globales(ctx, store, web, g_code, sectores_local, productos_terms)
        kb_competidores: list[str] = []
        kb_locales: list[str] = []
        jugadores_locales_ctx = ""
        fichas_conocidas_ctx = ""
        tiers_ancla: dict[str, list[str]] = {}
        fichas_kb: dict[str, dict[str, str]] = {}
        try:
            with SessionLocal() as db_kb:
                ensure_entidades_tables(db_kb.get_bind())
                repo_kb = EntidadRepository(db_kb)
                kb_competidores = repo_kb.list_competidores_by_sector(
                    sectores_local,
                    productos_terms=productos_terms,
                    alcance=ALCANCE_GLOBAL,
                    exclude_nombre=e,
                )
                regionales: list = []
                startups: list = []
                if s.anclaje_local_enabled and g_code:
                    n = s.anclaje_local_top_n
                    regionales = repo_kb.list_locales_by_sector(
                        sectores_local,
                        solo_establecidas=True,
                        productos_terms=productos_terms,
                        limit=n,
                        exclude_nombre=e,
                    )
                    startups = repo_kb.list_locales_by_sector(
                        sectores_local,
                        segmento=SEGMENTO_STARTUP,
                        productos_terms=productos_terms,
                        limit=n,
                        exclude_nombre=e,
                    )
                    jugadores_locales_ctx = format_jugadores_locales(regionales, startups)
                    kb_locales = [r.nombre for r in (*regionales, *startups)]
                nombres_ficha = [*kb_competidores, *kb_locales]
                if sectores_local and nombres_ficha:
                    fichas_kb = repo_kb.list_ficha_atributos_by_sector(
                        sectores_local, nombres_ficha
                    )
                    fichas_conocidas_ctx = format_fichas_conocidas(fichas_kb)
                tiers_ancla = {
                    TIER_GLOBAL: list(kb_competidores),
                    TIER_REGIONAL: [r.nombre for r in regionales],
                    TIER_STARTUP: [r.nombre for r in startups],
                }
        except Exception:
            logger.warning("No se pudo consultar el KB de competidores (sector %s)", g_code)

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

    return _fn_cap2
