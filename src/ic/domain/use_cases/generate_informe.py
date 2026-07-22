"""Orchestrator use case: genera el informe completo de IC (Caps 1–6 + Resumen Ejecutivo).

El progreso se reporta vía callback `on_step(n, total, label)` para desacoplar la
ejecución del concern de presentación (CLI, Streamlit, tests).
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

StepCallback = Callable[[int, int, str], None]


@dataclass
class InformeParams:
    empresa: str
    ciiu: str | None = None
    output_path: str | None = None


@dataclass
class InformeResult:
    ruta_docx: str
    n_referencias: int
    costo_usd: float
    tokens_in: int
    tokens_out: int
    tiempo_total_s: float
    cost_records: list
    ruta_pdf: str | None = None


@dataclass
class _PipelineContext:
    params: InformeParams
    settings: Any
    step_fn: Any
    total_start: float
    session_id: str = ""
    llm: Any = None
    api_llm: Any = None
    api_llm_alt: Any = None
    api_llm_synth: Any = None
    cap1_llms: list = field(default_factory=list)
    embedder: Any = None
    web: Any = None
    tracker: Any = None
    intro_chain: Any = None
    output_path: str = ""
    empresa: Any = None
    gics: Any = None
    cap: Any = None
    cap_tend: Any = None
    cap_eco: Any = None
    cap_conv: Any = None
    cap_acc: Any = None
    resumen: Any = None


class GenerateInforme:
    """Orquesta el pipeline completo: Cap 1 → GICS → N1 paralelo → N2 → N3 → .docx."""

    TOTAL_PASOS = 10

    def __init__(self, settings) -> None:
        self._settings = settings

    def run(
        self,
        params: InformeParams,
        on_step: StepCallback | None = None,
    ) -> InformeResult:
        import logging as _logging
        _logging.getLogger("sqlalchemy.engine").setLevel(_logging.WARNING)
        _logging.getLogger("httpx").setLevel(_logging.WARNING)
        _logging.getLogger("httpcore").setLevel(_logging.WARNING)

        def _step(n: int, label: str) -> None:
            if on_step:
                on_step(n, self.TOTAL_PASOS, label)

        ctx = self._setup_infra(params, _step, time.time())
        self._sweep_stale_web(ctx)
        self._run_n0(ctx)
        self._run_n1(ctx)
        self._run_n2(ctx)
        return self._run_n3(ctx)

    def _setup_infra(
        self, params: InformeParams, step_fn: Any, total_start: float
    ) -> _PipelineContext:
        from ic.domain.chains.chain_intro import build_chain_intro
        from ic.infrastructure.llm.gateway import CostTracker, build_api_llm, build_llm
        from ic.infrastructure.retrieval.embedder import Embedder
        from ic.infrastructure.sources.web_connector import WebConnector

        s = self._settings
        tracker = CostTracker(budget_limit=s.llm_budget_limit_usd)
        api_llm = (
            build_api_llm(s, tier="free", cost_tracker=tracker) if s.openrouter_api_key else None
        )
        api_llm_alt = (
            build_api_llm(s, tier="free_alt", cost_tracker=tracker)
            if s.openrouter_api_key and s.llm_api_free_alt_model else None
        )
        api_llm_synth = (
            build_api_llm(s, tier="synth", cost_tracker=tracker) if s.openrouter_api_key else None
        )
        llm = build_llm(s, cost_tracker=tracker)
        cap1_llms = [m for m in [api_llm, api_llm_alt, llm] if m is not None]
        slug = params.empresa.replace(" ", "_").replace(".", "").lower()
        output_path = params.output_path or f"./output/{slug}_informe.docx"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        import uuid
        return _PipelineContext(
            params=params, settings=s, step_fn=step_fn, total_start=total_start,
            session_id=uuid.uuid4().hex,
            llm=llm, api_llm=api_llm, api_llm_alt=api_llm_alt, api_llm_synth=api_llm_synth,
            cap1_llms=cap1_llms, embedder=Embedder(s), web=WebConnector(s),
            tracker=tracker,
            intro_chain=build_chain_intro(api_llm) if api_llm else None,
            output_path=output_path,
        )

    def _sweep_stale_web(self, ctx: _PipelineContext) -> None:
        """Barre chunks web huérfanos de corridas previas (crash) antes de empezar (T14.5)."""
        from ic.data.database import SessionLocal
        from ic.data.repositories.embedding_repo import EmbeddingRepository

        try:
            with SessionLocal() as db:
                n = EmbeddingRepository(db).sweep_stale_web_sessions(ctx.session_id)
                if n:
                    logger.info("Barrido de %d chunks web huérfanos de sesiones previas", n)
        except Exception:
            logger.warning("No se pudo barrer chunks web huérfanos", exc_info=True)

    def _promote_cited_web(self, ctx: _PipelineContext, chunks_usados: list) -> None:
        """Promueve solo los chunks web citados; borra el resto de la sesión (T14.5)."""
        from ic.data.database import SessionLocal
        from ic.data.repositories.embedding_repo import EmbeddingRepository

        cited_ids = [
            c.chunk_id for c in chunks_usados
            if getattr(c, "fuente_tipo", None) == "web" and getattr(c, "chunk_id", None)
        ]
        try:
            with SessionLocal() as db:
                borrados, promovidos = EmbeddingRepository(db).promote_cited_web(
                    ctx.session_id, cited_ids
                )
                logger.info(
                    "Persistencia web: %d chunks promovidos (citados), %d descartados",
                    promovidos, borrados,
                )
        except Exception:
            logger.warning("No se pudo promover/purgar chunks web de la sesión", exc_info=True)

    def _run_n0(self, ctx: _PipelineContext) -> None:
        from ic.domain.chains.chain_01_descripcion import build_chain_01
        from ic.domain.chains.chain_02_gics import build_chain_02
        from ic.domain.use_cases.classify_gics import ClassifyGICS
        from ic.domain.use_cases.generate_empresa_description import GenerateEmpresaDescription

        ctx.step_fn(1, "Cap 1 — Descripción de la empresa")
        uc_desc = GenerateEmpresaDescription(
            chain=build_chain_01(ctx.cap1_llms), web_connector=ctx.web
        )
        ctx.empresa = uc_desc.execute(ctx.params.empresa)
        if ctx.params.ciiu:
            ctx.empresa = ctx.empresa.__class__(
                nombre_empresa=ctx.empresa.nombre_empresa,
                actividad_ciiu=ctx.params.ciiu,
                texto=ctx.empresa.texto,
            )
        ctx.step_fn(2, "GICS — Clasificación de sector")
        ctx.gics = ClassifyGICS(chain=build_chain_02(ctx.api_llm or ctx.llm)).execute(
            nombre_empresa=ctx.params.empresa, descripcion_empresa=ctx.empresa.texto,
            ciiu=ctx.params.ciiu,
        )

    def _run_n1(self, ctx: _PipelineContext) -> None:
        from ic.domain.use_cases.generate_n1 import run_n1_parallel
        run_n1_parallel(ctx)

    def _run_n2(self, ctx: _PipelineContext) -> None:
        from ic.data.database import SessionLocal
        from ic.data.repositories.embedding_repo import EmbeddingRepository
        from ic.domain.chains.chain_06_convergencia import build_chain_06_synth
        from ic.domain.chains.chain_06a_convergencia_eje import build_chain_06a
        from ic.domain.chains.chain_07_accionables import build_chain_07
        from ic.domain.use_cases.generate_accionables import GenerateAccionables
        from ic.domain.use_cases.generate_convergencia import GenerateConvergencia
        from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
        from ic.shared.constants.gics_groups import extract_gics_code

        e, g = ctx.params.empresa, ctx.gics.grupo_gics
        g_code = extract_gics_code(g)
        with SessionLocal() as db_n2:
            store_n2 = PGVectorStore(ctx.embedder, EmbeddingRepository(db_n2), ctx.settings)
            store_n2.session_id = ctx.session_id

            ctx.step_fn(6, "Cap 5 — Convergencia Empresarial")
            if ctx.api_llm_synth is not None:
                ctx.cap_conv = GenerateConvergencia(
                    chain=build_chain_06_synth(ctx.api_llm_synth),
                    chain_eje=build_chain_06a(ctx.api_llm) if ctx.api_llm else None,
                    store=store_n2, web_connector=ctx.web,
                ).execute(
                    nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
                    sector_gics_code=g_code,
                )

            ctx.step_fn(7, "Cap 6 — Accionables Estratégicos")
            if ctx.api_llm is not None:
                ctx.cap_acc = GenerateAccionables(
                    chain=build_chain_07(ctx.api_llm), store=store_n2,
                ).execute(
                    nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
                    sector_gics_code=g_code,
                )

        ctx.step_fn(8, "Párrafos introductorios N2")
        if ctx.intro_chain is not None:
            for cap_obj, titulo in [
                (ctx.cap_conv, "Convergencia Empresarial"),
                (ctx.cap_acc, "Accionables Estratégicos"),
            ]:
                if cap_obj is not None and cap_obj.retrieval_suficiente:
                    intro = ctx.intro_chain.invoke({
                        "titulo": titulo, "empresa": ctx.params.empresa,
                        "resumen_cap": cap_obj.texto[:500],
                    })
                    cap_obj.texto = intro + "\n\n" + cap_obj.texto

    def _run_n3(self, ctx: _PipelineContext) -> InformeResult:
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
        )
        from ic.shared.types import InformePiloto

        ctx.step_fn(9, "Resumen Ejecutivo")
        if ctx.api_llm_synth is not None:
            cap_textos: dict[str, str] = {
                "Cap 1: Descripción": ctx.empresa.texto,
                "Cap 2: Benchmarking": ctx.cap.texto,
            }
            for key, obj in [
                ("Cap 3: Tendencias", ctx.cap_tend),
                ("Cap 4: Ecosistema", ctx.cap_eco),
                ("Cap 5: Convergencia", ctx.cap_conv),
                ("Cap 6: Accionables", ctx.cap_acc),
            ]:
                if obj:
                    cap_textos[key] = obj.texto
            ctx.resumen = GenerateResumenEjecutivo(
                chain=build_chain_08(ctx.api_llm_synth)
            ).execute(
                nombre_empresa=ctx.params.empresa,
                descripcion_empresa=ctx.empresa.texto,
                sector_gics=ctx.gics.grupo_gics,
                cap_textos=cap_textos,
            )

        ctx.step_fn(10, "Referencias + Ensamblado .docx")
        todos_chunks = list(ctx.cap.chunks_usados)
        for cap_obj in [ctx.cap_tend, ctx.cap_eco, ctx.cap_conv, ctx.cap_acc]:
            if cap_obj and cap_obj.chunks_usados:
                todos_chunks += cap_obj.chunks_usados
        refs = build_references_section(todos_chunks)

        # Persistencia web "solo lo citado" (T14.5, DT-020): de los chunks web de esta sesión,
        # se promueven los efectivamente usados y se borra el resto de la búsqueda.
        self._promote_cited_web(ctx, todos_chunks)

        texto_completo = " ".join(
            c.texto
            for c in [ctx.cap, ctx.cap_tend, ctx.cap_eco, ctx.cap_conv, ctx.cap_acc, ctx.resumen]
            if c is not None
        )
        orphans = find_orphan_citations(texto_completo, refs)
        if orphans:
            logger.warning("Citas huérfanas detectadas (sin referencia): %s", orphans)

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
            "tiempo_ollama_total_s": round(ctx.tracker.total_ollama_time_s(), 2),
        }

        informe = InformePiloto(
            empresa=ctx.empresa, gics=ctx.gics, cap_benchmarking=ctx.cap,
            cap_tendencias=ctx.cap_tend, cap_ecosistema=ctx.cap_eco,
            cap_convergencia=ctx.cap_conv, cap_accionables=ctx.cap_acc,
            resumen_ejecutivo=ctx.resumen, referencias=refs,
        )

        from ic.infrastructure.charts.radar_chart import generate_placeholder_radar
        from ic.infrastructure.render.docx_renderer import DocxRenderer
        from ic.infrastructure.render.pdf_renderer import convert_docx_to_pdf

        chart_path = ctx.output_path.replace(".docx", "_radar.png")
        try:
            generate_placeholder_radar(chart_path, ctx.params.empresa)
        except Exception:
            logger.warning("No se pudo generar radar chart", exc_info=True)
            chart_path = None

        assembler = PilotAssembler(disclaimer=ctx.settings.informe_disclaimer)
        report_doc = assembler.build(informe, figura_benchmarking=chart_path)
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
                empresa_orm = EmpresaRepository(db_h).upsert_by_name(ctx.params.empresa)
                informe_repo = InformeRepository(db_h)
                rec = informe_repo.create(empresa_orm.id, {"empresa": ctx.params.empresa})
                informe_repo.update_completado(
                    rec.id, ruta_docx=ctx.output_path, costo=ctx.tracker.total_cost(),
                    tiempo_s=time.time() - ctx.total_start,
                    tokens_in=tokens_in, tokens_out=tokens_out,
                    metricas=metricas_fiabilidad,
                )
        except Exception:
            logger.warning("No se pudo persistir historial", exc_info=True)

        return InformeResult(
            ruta_docx=ctx.output_path, n_referencias=len(refs),
            costo_usd=ctx.tracker.total_cost(), tokens_in=tokens_in, tokens_out=tokens_out,
            tiempo_total_s=time.time() - ctx.total_start, cost_records=ctx.tracker.records(),
            ruta_pdf=ruta_pdf,
        )
