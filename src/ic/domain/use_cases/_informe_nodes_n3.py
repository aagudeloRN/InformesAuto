"""Nodo N3 (Resumen, APA, Ensamblado docx, Guardado) del pipeline (DT-039)."""

from __future__ import annotations

import logging
import time

from ic.domain.use_cases import checkpoint_hooks
from ic.domain.use_cases._informe_context import (
    _AVG_WEB_MS,
    InformeResult,
    _PipelineContext,
    promote_cited_web,
)

logger = logging.getLogger(__name__)


def run_n3(ctx: _PipelineContext) -> InformeResult:
    from ic.data.database import SessionLocal, engine
    from ic.data.models.historial_informe import ensure_historial_columns
    from ic.data.repositories.empresa_repo import EmpresaRepository
    from ic.data.repositories.informe_repo import InformeRepository
    from ic.domain.assembler import PilotAssembler
    from ic.domain.chains.chain_08_resumen_ejecutivo import build_chain_08
    from ic.domain.use_cases.generate_resumen_ejecutivo import GenerateResumenEjecutivo
    from ic.infrastructure.citation.apa_formatter import (
        build_references_section,
        find_orphan_citations,
        strip_orphan_citations,
    )
    from ic.shared.types import InformePiloto

    ctx.step_fn(9, "Resumen Ejecutivo")
    if ctx.api_llm_synth is not None:
        cap_textos: dict[str, str] = {
            "Cap 1: Descripción": ctx.empresa.texto,
            "Cap 2: Benchmarking": ctx.cap.texto,
        }
        for key, obj in [
            ("Cap 2.3: Mercado", ctx.cap_mercado),
            ("Cap 3: Tendencias", ctx.cap_tend),
            ("Cap 4: Ecosistema", ctx.cap_eco),
            ("Cap 5: Convergencia", ctx.cap_conv),
            ("Cap 6: Accionables", ctx.cap_acc),
        ]:
            if obj:
                cap_textos[key] = obj.texto
        ctx.resumen = GenerateResumenEjecutivo(chain=build_chain_08(ctx.api_llm_synth)).execute(
            nombre_empresa=ctx.params.empresa,
            descripcion_empresa=ctx.empresa.texto,
            sector_gics=ctx.gics.grupo_gics,
            cap_textos=cap_textos,
        )

    ctx.step_fn(10, "Referencias + Ensamblado .docx")
    todos_chunks = list(ctx.cap.chunks_usados)
    for cap_obj in [ctx.cap_mercado, ctx.cap_tend, ctx.cap_eco, ctx.cap_conv, ctx.cap_acc]:
        if cap_obj and cap_obj.chunks_usados:
            todos_chunks += cap_obj.chunks_usados
    refs = build_references_section(todos_chunks)

    # Anti-mezcla (T22.A3, TIER 4 trazabilidad): histograma de sectores de los chunks
    # CITADOS. Los globales/web quedan exentos por diseño (ADR-012/018); un chunk de un
    # sector específico ajeno al de la empresa sería contaminación real. Solo mide (RN-001).
    from ic.domain.coherence import sector_histogram
    from ic.shared.constants.gics_groups import extract_gics_code

    sector_code = extract_gics_code(ctx.gics.grupo_gics)
    hist = sector_histogram([c.metadatos for c in todos_chunks], sector_code)
    logger.info(
        "Anti-mezcla chunks citados [sector=%s]: on_sector=%d exento=%d ajeno=%d",
        sector_code,
        hist.on_sector,
        hist.exento,
        hist.ajeno,
    )
    if hist.ajenos:
        logger.warning("Anti-mezcla: chunks de sector AJENO citados: %s", hist.ajenos)

    # Persistencia web "solo lo citado" (T14.5, DT-020): de los chunks web de esta sesión,
    # se promueven los efectivamente usados y se borra el resto de la búsqueda.
    promote_cited_web(ctx, todos_chunks)

    # Saneamiento de citas huérfanas (T22.A2, DT-052): las citas (Autor, año) del texto sin
    # referencia que las respalde se SUPRIMEN, no se inventa una fuente (RN-001). Se aplica a
    # cada capítulo antes del ensamblado y de la detección residual.
    caps_con_texto = [
        ctx.cap,
        ctx.cap_mercado,
        ctx.cap_tend,
        ctx.cap_eco,
        ctx.cap_conv,
        ctx.cap_acc,
        ctx.resumen,
    ]
    n_huerfanas_suprimidas = 0
    for cap_obj in caps_con_texto:
        if cap_obj is not None and getattr(cap_obj, "texto", None):
            cap_obj.texto, n_sup = strip_orphan_citations(cap_obj.texto, refs)
            n_huerfanas_suprimidas += n_sup
    if n_huerfanas_suprimidas:
        logger.info("Citas huérfanas suprimidas (sin referencia): %d", n_huerfanas_suprimidas)

    texto_completo = " ".join(c.texto for c in caps_con_texto if c is not None)
    orphans = find_orphan_citations(texto_completo, refs)
    if orphans:
        logger.warning("Citas huérfanas residuales tras saneamiento: %s", orphans)

    caps_fiabilidad = [
        ("Cap 1 — Descripción", True),
        ("Cap 2 — Benchmarking", ctx.cap.retrieval_suficiente),
    ]
    for nombre, obj in [
        ("Cap 3 — Tendencias", ctx.cap_tend),
        ("Cap 4 — Ecosistema", ctx.cap_eco),
        ("Cap 5 — Convergencia", ctx.cap_conv),
        ("Cap 6 — Accionables", ctx.cap_acc),
        ("Resumen Ejecutivo", ctx.resumen),
    ]:
        if obj is not None:
            caps_fiabilidad.append((nombre, obj.retrieval_suficiente))
    metricas_fiabilidad = {
        "n_caps_ok": sum(1 for _, ok in caps_fiabilidad if ok),
        "n_caps_total": len(caps_fiabilidad),
        "caps_ausencia": [n for n, ok in caps_fiabilidad if not ok],
        "n_fuentes_total": len(refs),
        "n_citas_huerfanas": len(orphans),
        "n_huerfanas_suprimidas": n_huerfanas_suprimidas,
        "tiempo_ollama_total_s": round(ctx.tracker.total_ollama_time_s(), 2),
        "enriquecimiento": [e.to_dict() for e in ctx.eventos_enriquecimiento],
    }

    informe = InformePiloto(
        empresa=ctx.empresa,
        gics=ctx.gics,
        cap_benchmarking=ctx.cap,
        cap_mercado=ctx.cap_mercado,
        cap_22_division=ctx.cap22_division,
        cap_tendencias=ctx.cap_tend,
        cap_ecosistema=ctx.cap_eco,
        cap_convergencia=ctx.cap_conv,
        cap_accionables=ctx.cap_acc,
        resumen_ejecutivo=ctx.resumen,
        referencias=refs,
    )

    from ic.infrastructure.render.docx_renderer import DocxRenderer
    from ic.infrastructure.render.pdf_renderer import convert_docx_to_pdf

    # Radar desconectado: el placeholder no aportaba valor y el LLM raramente emite
    # radar_json confiable. El código de generación se conserva en radar_chart.py.
    assembler = PilotAssembler(disclaimer=ctx.settings.informe_disclaimer)
    report_doc = assembler.build(informe, figura_benchmarking=None)
    DocxRenderer(ctx.settings.docx_template_path or None).render(report_doc, ctx.output_path)

    ruta_pdf: str | None = None
    try:
        ruta_pdf = convert_docx_to_pdf(ctx.output_path)
    except Exception:
        logger.warning("No se pudo generar PDF", exc_info=True)

    tokens_in, tokens_out = ctx.tracker.total_tokens()
    try:
        ensure_historial_columns(engine)
        with SessionLocal() as db_h:
            # empresa_id ya resuelto en _run_n0 (T18.3); si falló, resolver aquí como fallback
            if ctx.empresa_id is None:
                ctx.empresa_id = EmpresaRepository(db_h).upsert_by_name(ctx.params.empresa).id
            informe_repo = InformeRepository(db_h)
            rec = informe_repo.create(ctx.empresa_id, {"empresa": ctx.params.empresa})
            informe_repo.update_completado(
                rec.id,
                ruta_docx=ctx.output_path,
                costo=ctx.tracker.total_cost(),
                tiempo_s=time.time() - ctx.total_start,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                metricas=metricas_fiabilidad,
            )
    except Exception:
        logger.warning("No se pudo persistir historial", exc_info=True)

    # T17.1 (DT-026): instrumentación de hit-rate de caché por informe.
    wc = ctx.cache_web_counter
    oc = ctx.cache_oal_counter
    logger.info(
        "Cache web: %d HITs / %d MISSes — ahorro estimado: %.0f ms",
        wc.hits,
        wc.misses,
        wc.hits * _AVG_WEB_MS,
    )
    logger.info("Cache openalex: %d HITs / %d MISSes", oc.hits, oc.misses)

    # Fase 1: el caché por (empresa, ciiu) es DURABLE (sirve de fallback/reuso entre corridas).
    # Solo se limpia si la corrida no usa caché (clásico T22.3: no dejar checkpoint colgando).
    if not ctx.params.use_cache:
        checkpoint_hooks.clear(ctx)

    return InformeResult(
        ruta_docx=ctx.output_path,
        n_referencias=len(refs),
        costo_usd=ctx.tracker.total_cost(),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tiempo_total_s=time.time() - ctx.total_start,
        cost_records=ctx.tracker.records(),
        ruta_pdf=ruta_pdf,
        cache_web_hits=wc.hits,
        cache_web_misses=wc.misses,
        cache_oal_hits=oc.hits,
        cache_oal_misses=oc.misses,
    )
