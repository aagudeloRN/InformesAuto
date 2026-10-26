"""Nodos N0 (Cap 1, GICS, KB) y N1 (análisis paralelo) del pipeline de informes (DT-039)."""

from __future__ import annotations

import logging
from dataclasses import replace

from ic.domain.use_cases import checkpoint_hooks
from ic.domain.use_cases._informe_context import _PipelineContext
from ic.shared.text_productos import extract_productos_servicios

logger = logging.getLogger(__name__)


def run_n0(ctx: _PipelineContext) -> None:
    from ic.data.database import SessionLocal
    from ic.domain.chains.chain_01_descripcion import build_chain_01
    from ic.domain.chains.chain_02_gics import build_chain_02
    from ic.domain.use_cases.classify_gics import ClassifyGICS
    from ic.domain.use_cases.generate_empresa_description import GenerateEmpresaDescription
    from ic.infrastructure.sources.cached_connector import CachedWebConnector

    ctx.step_fn(1, "Cap 1 — Descripción de la empresa")
    # T22.3: reanudar desde checkpoint evita recomputar Cap 1 (búsquedas web + LLM).
    ctx.empresa = checkpoint_hooks.restore(ctx, "empresa")
    if ctx.empresa is None:
        # T16.0-B: CachedWebConnector para Cap 1 (sesión breve, single-threaded)
        with SessionLocal() as db_n0:
            cached_web_n0 = CachedWebConnector(
                ctx.web, db_n0, ctx.settings, counter=ctx.cache_web_counter
            )
            uc_desc = GenerateEmpresaDescription(
                chain=build_chain_01(ctx.cap1_llms), web_connector=cached_web_n0
            )
            ctx.empresa = uc_desc.execute(ctx.params.empresa)
        if ctx.params.ciiu:
            # `replace` preserva TODOS los campos (incl. productos_servicios de DT-063); antes
            # se reconstruía a mano y se perdía la señal de producto → el descubrimiento caía a
            # nivel grupo (contaminación tabaco en Alpina).
            ctx.empresa = replace(ctx.empresa, actividad_ciiu=ctx.params.ciiu)
        ctx.empresa = checkpoint_hooks.commit_best(ctx, "empresa", ctx.empresa)
    # DT-063: red de seguridad — si productos_servicios llega vacío (checkpoint viejo sin el
    # campo, o cualquier ruta que lo pierda) pero hay descripción, se re-deriva de la prosa.
    if not getattr(ctx.empresa, "productos_servicios", "") and ctx.empresa.texto:
        ctx.empresa = replace(
            ctx.empresa,
            productos_servicios=extract_productos_servicios(ctx.empresa.texto),
        )
    ctx.step_fn(2, "GICS — Clasificación de sector")
    ctx.gics = checkpoint_hooks.restore(ctx, "gics")
    if ctx.gics is None:
        ctx.gics = ClassifyGICS(chain=build_chain_02(ctx.api_llm or ctx.llm)).execute(
            nombre_empresa=ctx.params.empresa,
            descripcion_empresa=ctx.empresa.texto,
            ciiu=ctx.params.ciiu,
        )
        ctx.gics = checkpoint_hooks.commit_best(ctx, "gics", ctx.gics)
    # Resolver empresa_id al inicio del pipeline para pasarlo a todos los use cases (T18.3).
    # Esto permite que el retrieval priorice docs asociados a esta empresa.
    try:
        from ic.data.database import SessionLocal, engine
        from ic.data.models.historial_informe import ensure_historial_columns
        from ic.data.repositories.empresa_repo import EmpresaRepository

        ensure_historial_columns(engine)
        with SessionLocal() as db_e:
            empresa_orm = EmpresaRepository(db_e).upsert_by_name(ctx.params.empresa)
            ctx.empresa_id = empresa_orm.id
    except Exception:
        logger.warning(
            "No se pudo resolver empresa_id temprano — retrieval sin filtro empresa",
            exc_info=True,
        )
    # DT-056/T4 (base viva): nutrir el KB con la empresa principal (identidad verificada,
    # descripción como candidato). Falla suave: es enriquecimiento, no debe romper la corrida.
    try:
        from ic.data.database import SessionLocal, engine
        from ic.data.models.entidad import ALCANCE_LOCAL, ensure_entidades_tables
        from ic.data.repositories.entidad_repo import EntidadRepository
        from ic.domain.use_cases.nurture_kb import NurtureKB
        from ic.shared.constants.gics_groups import extract_gics_code

        ensure_entidades_tables(engine)
        with SessionLocal() as db_kb:
            # La empresa analizada es el jugador regional colombiano → alcance=local + su
            # perfil de producto, para reusarla como competidor regional en informes futuros.
            NurtureKB(EntidadRepository(db_kb)).execute(
                nombre=ctx.params.empresa,
                sector_gics=extract_gics_code(ctx.gics.grupo_gics),
                descripcion=ctx.empresa.texto,
                alcance=ALCANCE_LOCAL,
                productos=ctx.empresa.productos_servicios,
            )
    except Exception:
        logger.warning("No se pudo nutrir el KB con la empresa principal", exc_info=True)


def run_n1(ctx: _PipelineContext) -> None:
    from ic.domain.use_cases.generate_n1 import run_n1_parallel

    run_n1_parallel(ctx)
