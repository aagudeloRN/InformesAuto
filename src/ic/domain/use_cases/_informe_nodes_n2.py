"""Nodos N2 (Cap 5, 6) del pipeline de informes (DT-039)."""

from __future__ import annotations

import logging

from ic.domain.use_cases import checkpoint_hooks
from ic.domain.use_cases._informe_context import _PipelineContext

logger = logging.getLogger(__name__)


def run_n2(ctx: _PipelineContext) -> None:
    from ic.data.database import SessionLocal
    from ic.data.repositories.embedding_repo import EmbeddingRepository
    from ic.domain.chains.chain_06_convergencia import build_chain_06_synth
    from ic.domain.chains.chain_06a_convergencia_eje import build_chain_06a
    from ic.domain.chains.chain_07_accionables import build_chain_07
    from ic.domain.chains.chain_judge import CRITERIOS_CAPITULO
    from ic.domain.use_cases.generate_accionables import GenerateAccionables
    from ic.domain.use_cases.generate_convergencia import GenerateConvergencia
    from ic.domain.use_cases.self_review_hooks import review_integration_cap
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.cached_connector import CachedWebConnector
    from ic.shared.constants.gics_groups import extract_gics_code

    e, g = ctx.params.empresa, ctx.gics.grupo_gics
    g_code = extract_gics_code(g)
    _caps = ctx.params.caps_incluidos
    run_cap5 = _caps is None or "cap5" in _caps
    run_cap6 = _caps is None or "cap6" in _caps
    # T22.3 (DT-030): --resume salta Cap 5/6 ya persistidos. Cap 6 es barrera de
    # sincronización (consume Cap 5); si Cap 5 se restaura y Cap 6 no, se recomputa
    # Cap 6 sobre el Cap 5 restaurado — el DAG se respeta.
    ctx.cap_conv = checkpoint_hooks.restore(ctx, "cap5") if run_cap5 else None
    ctx.cap_acc = checkpoint_hooks.restore(ctx, "cap6") if run_cap6 else None
    conv_restaurado = ctx.cap_conv is not None
    acc_restaurado = ctx.cap_acc is not None
    with SessionLocal() as db_n2:
        store_n2 = PGVectorStore(ctx.embedder, EmbeddingRepository(db_n2), ctx.settings)
        store_n2.session_id = ctx.session_id
        cached_web_n2 = CachedWebConnector(  # T16.0-B
            ctx.web, db_n2, ctx.settings, counter=ctx.cache_web_counter
        )

        ctx.step_fn(6, "Cap 5 — Convergencia Empresarial")
        if not conv_restaurado and ctx.api_llm_synth is not None and run_cap5:
            ctx.cap_conv = GenerateConvergencia(
                chain=build_chain_06_synth(ctx.api_llm_synth),
                chain_eje=build_chain_06a(ctx.api_llm) if ctx.api_llm else None,
                store=store_n2,
                web_connector=cached_web_n2,
            ).execute(
                nombre_empresa=e,
                descripcion_empresa=ctx.empresa.texto,
                sector_gics=g,
                sector_gics_code=g_code,
                empresa_id=ctx.empresa_id,
            )
            # DT-059/T3: auto-revisión sabor integración (solo re-sintetiza). Flag OFF = no-op.
            ctx.cap_conv = review_integration_cap(
                settings=ctx.settings,
                llm=ctx.api_llm_synth,
                capitulo_nombre="Cap 5 — Convergencia Empresarial",
                criterios=CRITERIOS_CAPITULO["Cap 5 — Convergencia Empresarial"],
                cap_obj=ctx.cap_conv,
                run_key=ctx.run_key,
            )

        ctx.step_fn(7, "Cap 6 — Accionables Estratégicos")
        if not acc_restaurado and ctx.api_llm is not None and run_cap6:
            # Coherencia (T22.1, Q1): pasar un resumen de los hallazgos de los caps ya
            # generados (2/3/4/5) para que los accionables los referencien explícitamente,
            # no solo el retrieval. Todos están disponibles en este punto del DAG.
            from ic.domain.coherence import build_caps_summary

            hallazgos = build_caps_summary(
                [
                    (etiqueta, obj.texto)
                    for etiqueta, obj in [
                        ("Cap 2 — Benchmarking", ctx.cap),
                        ("Cap 3 — Tendencias", ctx.cap_tend),
                        ("Cap 4 — Ecosistema", ctx.cap_eco),
                        ("Cap 5 — Convergencia", ctx.cap_conv),
                    ]
                    if obj is not None and obj.retrieval_suficiente
                ]
            )
            ctx.cap_acc = GenerateAccionables(
                chain=build_chain_07(ctx.api_llm),
                store=store_n2,
            ).execute(
                nombre_empresa=e,
                descripcion_empresa=ctx.empresa.texto,
                sector_gics=g,
                sector_gics_code=g_code,
                empresa_id=ctx.empresa_id,
                hallazgos_caps_previos=hallazgos,
            )
            ctx.cap_acc = review_integration_cap(
                settings=ctx.settings,
                llm=ctx.api_llm,
                capitulo_nombre="Cap 6 — Accionables Estratégicos",
                criterios=CRITERIOS_CAPITULO["Cap 6 — Accionables Estratégicos"],
                cap_obj=ctx.cap_acc,
                run_key=ctx.run_key,
            )

    ctx.step_fn(8, "Párrafos introductorios N2")
    if ctx.intro_chain is not None:
        # El intro se aplica solo a caps recién computados; los restaurados ya lo incluyen.
        for cap_obj, titulo, restaurado in [
            (ctx.cap_conv, "Convergencia Empresarial", conv_restaurado),
            (ctx.cap_acc, "Accionables Estratégicos", acc_restaurado),
        ]:
            if not restaurado and cap_obj is not None and cap_obj.retrieval_suficiente:
                intro = ctx.intro_chain.invoke(
                    {
                        "titulo": titulo,
                        "empresa": ctx.params.empresa,
                        "resumen_cap": cap_obj.texto[:500],
                    }
                )
                # DT-055: intro saneado puede quedar vacío → no anteponer líneas en blanco
                if intro:
                    cap_obj.texto = intro + "\n\n" + cap_obj.texto

    # Persistir los caps recién computados (con intro) con keep-best + fallback (Fase 1).
    if not conv_restaurado and run_cap5:
        ctx.cap_conv = checkpoint_hooks.commit_best(ctx, "cap5", ctx.cap_conv)
    if not acc_restaurado and run_cap6:
        ctx.cap_acc = checkpoint_hooks.commit_best(ctx, "cap6", ctx.cap_acc)
