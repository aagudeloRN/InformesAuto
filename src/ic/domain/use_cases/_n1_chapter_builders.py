"""Sub-orquestadores para Caps 3, 4, Mercado e Intros en N1."""

from __future__ import annotations

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


def build_fn_mercado_impl(ctx: _PipelineContext, g_code: str):
    """Construye el ejecutor para Mercado (Cap 2.2)."""
    e, g = ctx.params.empresa, ctx.gics.grupo_gics

    def _fn_mercado(store: Any, web: Any, _oal: Any):
        if ctx.api_llm is None:
            return None
        return GenerateMercado(
            chain=build_chain_03b(ctx.api_llm), store=store, web_connector=web
        ).execute(
            nombre_empresa=e,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
        )

    return _fn_mercado


def build_fn_cap3_impl(ctx: _PipelineContext, g_code: str):
    """Construye el ejecutor para Cap 3 (Tendencias)."""
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings

    def _fn_cap3(store: Any, web: Any, oal: Any):
        if ctx.api_llm is None:
            return None
        cap = GenerateTendencias(
            chain=build_chain_04(ctx.api_llm),
            store=store,
            web_connector=web,
            openalex_connector=oal,
        ).execute(
            nombre_empresa=e,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
        )
        return review_web_cap(
            settings=s,
            llm=ctx.api_llm,
            capitulo_nombre="Cap 3 ? An?lisis Sectorial Tendencial",
            criterios=CRITERIOS_CAPITULO["Cap 3 ? An?lisis Sectorial Tendencial"],
            cap_obj=cap,
            run_key=ctx.run_key,
            store=store,
            web=web,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} tendencias sectoriales tecnologicas {e}",
        )

    return _fn_cap3


def build_fn_cap4_impl(ctx: _PipelineContext, g_code: str):
    """Construye el ejecutor para Cap 4 (Ecosistema)."""
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings

    def _fn_cap4(store: Any, web: Any, _oal: Any):
        if ctx.api_llm is None:
            return None
        cap = GenerateEcosistema(
            chain=build_chain_05(ctx.api_llm),
            store=store,
            web_connector=web,
        ).execute(
            nombre_empresa=e,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
        )
        return review_web_cap(
            settings=s,
            llm=ctx.api_llm,
            capitulo_nombre="Cap 4 ? Panorama Ecosistema",
            criterios=CRITERIOS_CAPITULO["Cap 4 ? Panorama Ecosistema"],
            cap_obj=cap,
            run_key=ctx.run_key,
            store=store,
            web=web,
            sector_gics=g,
            sector_gics_code=g_code,
            empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} ecosistema inversiones fusiones adquisiciones alianzas {e}",
        )

    return _fn_cap4


def apply_n1_intros(ctx: _PipelineContext, restored: dict[str, Any]) -> None:
    """Aplica parrafos introductorios a los capitulos recien generados."""
    if ctx.intro_chain is None:
        return
    for cap_obj, titulo, name in [
        (ctx.cap, "An?lisis Competitivo", "cap2"),
        (ctx.cap_tend, "An?lisis Sectorial Tendencial", "cap3"),
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
