"""Sub-orquestadores para Caps 3, 4, Mercado e Intros en N1."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ic.domain.chains.chain_03b_mercado import build_chain_03b
from ic.domain.chains.chain_04_tendencias import build_chain_04
from ic.domain.chains.chain_05_ecosistema import build_chain_05
from ic.domain.chains.chain_judge import CRITERIOS_CAPITULO
from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
from ic.domain.use_cases.generate_mercado import GenerateMercado
from ic.domain.use_cases.generate_tendencias import GenerateTendencias
from ic.domain.use_cases.self_review_hooks import review_web_cap

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext

logger = logging.getLogger(__name__)


def _maybe_auto_enrich(ctx: _PipelineContext, g_code: str, query_text: str) -> bool:
    """Intenta auto-enriquecer evidencia si el sector no ha sido procesado."""
    if not g_code or g_code in ctx._enriched_sectors:
        return False
    ctx._enriched_sectors.add(g_code)
    try:
        from ic.domain.use_cases.auto_enrich import AutoEnrich

        auto_enrich = AutoEnrich(settings=ctx.settings, embedder=ctx.embedder)
        evento = auto_enrich.try_enrich(
            sector_gics=g_code,
            query_text=query_text,
            threshold=getattr(ctx.settings, "rag_sector_reserve_threshold", 0.5),
        )
        ctx.eventos_enriquecimiento.append(evento)
        return evento.enriquecido
    except Exception as exc:
        logger.warning("Auto-enriquecimiento omitido para sector %s: %s", g_code, exc)
        return False


def build_fn_mercado_impl(ctx: _PipelineContext, g_code: str):
    """Construye el ejecutor para Mercado (Cap 2.2)."""
    e, g = ctx.params.empresa, ctx.gics.grupo_gics

    def _fn_mercado(store: Any, web: Any, _oal: Any):
        if ctx.api_llm is None:
            return None
        gen = GenerateMercado(chain=build_chain_03b(ctx.api_llm), store=store, web_connector=web)
        cap = gen.execute(
            nombre_empresa=e,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
        )
        if cap and not getattr(cap, "retrieval_suficiente", False):
            if _maybe_auto_enrich(ctx, g_code, f"{g} mercado industria {e}"):
                cap = gen.execute(
                    nombre_empresa=e,
                    descripcion_empresa=ctx.empresa.texto,
                    sector_gics=g,
                    sector_gics_code=g_code,
                    empresa_id=ctx.empresa_id,
                )
        return cap

    return _fn_mercado


def build_fn_cap3_impl(ctx: _PipelineContext, g_code: str):
    """Construye el ejecutor para Cap 3 (Tendencias)."""
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings

    def _fn_cap3(store: Any, web: Any, oal: Any):
        if ctx.api_llm is None:
            return None
        gen = GenerateTendencias(
            chain=build_chain_04(ctx.api_llm),
            store=store,
            web_connector=web,
            openalex_connector=oal,
        )
        query = f"{g} tendencias sectoriales tecnologicas {e}"
        cap = gen.execute(
            nombre_empresa=e,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
        )
        if cap and not getattr(cap, "retrieval_suficiente", False):
            if _maybe_auto_enrich(ctx, g_code, query):
                cap = gen.execute(
                    nombre_empresa=e,
                    descripcion_empresa=ctx.empresa.texto,
                    sector_gics=g,
                    sector_gics_code=g_code,
                    empresa_id=ctx.empresa_id,
                )

        return review_web_cap(
            settings=s,
            llm=ctx.api_llm,
            capitulo_nombre="Cap 3 — Análisis Sectorial Tendencial",
            criterios=CRITERIOS_CAPITULO["Cap 3 — Análisis Sectorial Tendencial"],
            cap_obj=cap,
            run_key=ctx.run_key,
            store=store,
            web=web,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
            retrieval_query=query,
        )

    return _fn_cap3


def build_fn_cap4_impl(ctx: _PipelineContext, g_code: str):
    """Construye el ejecutor para Cap 4 (Ecosistema)."""
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings

    def _fn_cap4(store: Any, web: Any, _oal: Any):
        if ctx.api_llm is None:
            return None
        gen = GenerateEcosistema(
            chain=build_chain_05(ctx.api_llm),
            store=store,
            web_connector=web,
        )
        query = f"{g} ecosistema inversiones fusiones adquisiciones alianzas {e}"
        cap = gen.execute(
            nombre_empresa=e,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
        )
        if cap and not getattr(cap, "retrieval_suficiente", False):
            if _maybe_auto_enrich(ctx, g_code, query):
                cap = gen.execute(
                    nombre_empresa=e,
                    descripcion_empresa=ctx.empresa.texto,
                    sector_gics=g,
                    sector_gics_code=g_code,
                    empresa_id=ctx.empresa_id,
                )

        return review_web_cap(
            settings=s,
            llm=ctx.api_llm,
            capitulo_nombre="Cap 4 — Panorama Ecosistema",
            criterios=CRITERIOS_CAPITULO["Cap 4 — Panorama Ecosistema"],
            cap_obj=cap,
            run_key=ctx.run_key,
            store=store,
            web=web,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
            retrieval_query=query,
        )

    return _fn_cap4


def apply_n1_intros(ctx: _PipelineContext, restored: dict[str, Any]) -> None:
    """Aplica parrafos introductorios a los capitulos recien generados."""
    if ctx.intro_chain is None:
        return
    for cap_obj, titulo, name in [
        (ctx.cap, "Análisis Competitivo", "cap2"),
        (ctx.cap_tend, "Análisis Sectorial Tendencial", "cap3"),
        (ctx.cap_eco, "Ecosistema Empresarial", "cap4"),
    ]:
        if (
            name in restored
            and restored[name] is None
            and cap_obj is not None
            and cap_obj.retrieval_suficiente
        ):
            intro = ctx.intro_chain.invoke(
                {
                    "titulo": titulo,
                    "empresa": ctx.params.empresa,
                    "resumen_cap": cap_obj.texto[:500],
                }
            )
            if intro:
                cap_obj.texto = intro + "\n\n" + cap_obj.texto
