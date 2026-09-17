"""Funciones auxiliares para Cap 2 en N1 (descubrimiento y persistencia)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ic.data.database import SessionLocal
from ic.data.models.entidad import (
    ALCANCE_GLOBAL,
    ESTADO_CANDIDATO,
    ESTADO_VERIFICADO,
    FUENTE_LLM,
    FUENTE_WEB,
    TIPO_COMPETIDOR,
    ensure_entidades_tables,
)
from ic.data.repositories._entidad_queries import EntidadRow
from ic.data.repositories.entidad_repo import EntidadRepository
from ic.domain.chains.chain_02c_pares_globales import build_chain_pares_globales
from ic.domain.kb.ficha_parser import parse_fichas_competidores
from ic.domain.use_cases.discover_globales import DiscoverGlobales
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


def cargar_kb_competidores_ancla(
    db_kb: Any,
    s: Any,
    g_code: str,
    sectores_local: list[str],
    productos_terms: set[str],
    e: str,
    competidores_curados: dict[str, list[str]] | list[str] | set[str] | None = None,
):
    """Consulta y estructura los competidores ancla del KB (con soporte HITL Spec 007)."""
    from ic.data.models.entidad import ALCANCE_GLOBAL, SEGMENTO_STARTUP, ensure_entidades_tables
    from ic.data.repositories.entidad_repo import EntidadRepository
    from ic.domain.kb.ficha_parser import TIER_GLOBAL, TIER_REGIONAL, TIER_STARTUP
    from ic.domain.kb.relevance import format_fichas_conocidas, format_jugadores_locales

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
    jugadores_locales_ctx = ""
    kb_locales: list[str] = []
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

    if competidores_curados:
        if isinstance(competidores_curados, dict):
            g_sel = set(
                competidores_curados.get(TIER_GLOBAL, competidores_curados.get("globales", []))
            )
            r_sel = set(
                competidores_curados.get(TIER_REGIONAL, competidores_curados.get("regionales", []))
            )
            s_sel = set(
                competidores_curados.get(TIER_STARTUP, competidores_curados.get("startups", []))
            )
            if g_sel:
                kb_competidores = [c for c in kb_competidores if c in g_sel] or list(g_sel)
            if r_sel:
                regionales = [r for r in regionales if r.nombre in r_sel]
            if s_sel:
                startups = [st for st in startups if st.nombre in s_sel]
        elif isinstance(competidores_curados, (list, set)):
            curados_set = set(competidores_curados)
            kb_competidores = [c for c in kb_competidores if c in curados_set]
            regionales = [r for r in regionales if r.nombre in curados_set]
            startups = [st for st in startups if st.nombre in curados_set]

    jugadores_locales_ctx = format_jugadores_locales(regionales, startups)
    kb_locales = [r.nombre for r in (*regionales, *startups)]

    fichas_kb: dict[str, dict[str, str]] = {}
    fichas_conocidas_ctx = ""
    nombres_ficha = [*kb_competidores, *kb_locales]
    if sectores_local and nombres_ficha:
        fichas_kb = repo_kb.list_ficha_atributos_by_sector(sectores_local, nombres_ficha)
        fichas_conocidas_ctx = format_fichas_conocidas(fichas_kb)

    tiers_ancla = {
        TIER_GLOBAL: list(kb_competidores),
        TIER_REGIONAL: [r.nombre for r in regionales],
        TIER_STARTUP: [r.nombre for r in startups],
    }
    return (
        kb_competidores,
        kb_locales,
        jugadores_locales_ctx,
        fichas_conocidas_ctx,
        tiers_ancla,
        fichas_kb,
    )
