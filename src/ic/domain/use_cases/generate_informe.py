"""Orchestrator use case: genera el informe completo de IC (Caps 1–6 + Resumen Ejecutivo).

El progreso se reporta vía callback `on_step(n, total, label)` para desacoplar la
ejecución del concern de presentación (CLI, Streamlit, tests).
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ic.domain.use_cases import checkpoint_hooks
from ic.shared.text_productos import extract_productos_servicios

logger = logging.getLogger(__name__)

StepCallback = Callable[[int, int, str], None]

# Estimación de latencia de una búsqueda web (ms) para reportar el ahorro de caché (T17.1).
# No es un nombre de modelo: no aplica la regla TIER 1 de config.
_AVG_WEB_MS = 800.0


@dataclass
class InformeParams:
    empresa: str
    ciiu: str | None = None
    output_path: str | None = None
    resume: bool = False  # T22.3 (DT-030): reanuda desde el último capítulo persistido
    # Fase 1 (caché durable keep-best): el caché por (empresa, ciiu) sobrevive a la corrida y sirve
    # de fallback si un capítulo sale degradado. `use_cache=False` → clásico (sin caché);
    # `refresh=True` → invalida el caché al arrancar y regenera todo desde cero.
    use_cache: bool = True
    refresh: bool = False
    # Módulos opcionales: None = usa el default de Settings/.env; True/False = override por corrida.
    # Permite que la UI active/desactive módulos sin tocar el .env global.
    selfreview: bool | None = None
    discover_globales: bool | None = None
    anclaje_local: bool | None = None
    seccion21_determinista: bool | None = None


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
    cache_web_hits: int = 0
    cache_web_misses: int = 0
    cache_oal_hits: int = 0
    cache_oal_misses: int = 0


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
    cap_mercado: Any = None  # Cap 2.3 Mercado (T21.6, DT-044)
    cap_tend: Any = None
    cap_eco: Any = None
    cap_conv: Any = None
    cap_acc: Any = None
    resumen: Any = None
    cache_web_counter: Any = None
    cache_oal_counter: Any = None
    empresa_id: Any = None  # UUID resuelto en N0; se pasa a todos los use cases (T18.3)
    # T22.3 (DT-030): checkpoint --resume
    run_key: str = ""
    checkpoint: dict = field(default_factory=dict)  # {cap_nombre: payload} ya persistido


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
        # Fase 1: --refresh invalida el caché durable al arrancar → regenera todo desde cero.
        if params.refresh:
            checkpoint_hooks.clear(ctx)
        checkpoint_hooks.load(ctx)
        self._sweep_stale_web(ctx)
        self._run_n0(ctx)
        self._run_n1(ctx)
        self._run_n2(ctx)
        return self._run_n3(ctx)

    def _setup_infra(
        self, params: InformeParams, step_fn: Any, total_start: float
    ) -> _PipelineContext:
        from ic.domain.chains.chain_intro import build_chain_intro
        from ic.domain.checkpoint_serde import make_run_key
        from ic.infrastructure.llm.gateway import (
            CostTracker,
            build_llm,
            build_resilient_api_llm,
        )
        from ic.infrastructure.retrieval.embedder import Embedder
        from ic.infrastructure.sources.cached_connector import CacheCounter
        from ic.infrastructure.sources.web_connector import WebConnector

        # Aplicar overrides de módulos desde InformeParams (None = respetar el .env/Settings).
        _overrides = {
            k: v for k, v in {
                "selfreview_enabled": params.selfreview,
                "discover_globales_enabled": params.discover_globales,
                "anclaje_local_enabled": params.anclaje_local,
                "seccion21_determinista_enabled": params.seccion21_determinista,
            }.items() if v is not None
        }
        s = self._settings.model_copy(update=_overrides) if _overrides else self._settings
        tracker = CostTracker(budget_limit=s.llm_budget_limit_usd)
        # T16.0-A: modelo resiliente analítico (free→free_alt→synth→paid→fallback) para Caps 2/3/4.
        resilient_llm = (
            build_resilient_api_llm(s, cost_tracker=tracker) if s.openrouter_api_key else None
        )
        # 2026-08-03: cadena dedicada de SÍNTESIS (Cap 5/6/Resumen) = synth (Gemini 2.5 Flash) +
        # fallback (openrouter/free). Reserva la cuota diaria de Gemini para los POCOS llamados de
        # síntesis; los ~40 analíticos siguen en Nemotron. Sin synth/fallback → usa la general.
        # Invariante: solo se separa si la síntesis va a Gemini (provider+key); si no, la general.
        resilient_synth_llm = resilient_llm
        if s.llm_api_synth_provider == "gemini" and s.gemini_api_key:
            try:
                resilient_synth_llm = build_resilient_api_llm(
                    s, tiers=["synth"], cost_tracker=tracker
                )
            except ValueError:
                resilient_synth_llm = resilient_llm
        llm = build_llm(s, cost_tracker=tracker)
        cap1_llms = [m for m in [resilient_llm, llm] if m is not None]
        slug = params.empresa.replace(" ", "_").replace(".", "").lower()
        output_path = params.output_path or f"./output/{slug}_informe.docx"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        import uuid
        return _PipelineContext(
            params=params, settings=s, step_fn=step_fn, total_start=total_start,
            session_id=uuid.uuid4().hex,
            llm=llm,
            api_llm=resilient_llm,
            api_llm_alt=None,
            api_llm_synth=resilient_synth_llm,  # síntesis: Gemini + fallback openrouter/free
            cap1_llms=cap1_llms, embedder=Embedder(s), web=WebConnector(s),
            tracker=tracker,
            intro_chain=build_chain_intro(resilient_llm) if resilient_llm else None,
            output_path=output_path,
            cache_web_counter=CacheCounter(),
            cache_oal_counter=CacheCounter(),
            run_key=make_run_key(params.empresa, params.ciiu),
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
                nombre_empresa=ctx.params.empresa, descripcion_empresa=ctx.empresa.texto,
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

    def _run_n1(self, ctx: _PipelineContext) -> None:
        from ic.domain.use_cases.generate_n1 import run_n1_parallel
        run_n1_parallel(ctx)

    def _run_n2(self, ctx: _PipelineContext) -> None:
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
        # T22.3 (DT-030): --resume salta Cap 5/6 ya persistidos. Cap 6 es barrera de
        # sincronización (consume Cap 5); si Cap 5 se restaura y Cap 6 no, se recomputa
        # Cap 6 sobre el Cap 5 restaurado — el DAG se respeta.
        ctx.cap_conv = checkpoint_hooks.restore(ctx, "cap5")
        ctx.cap_acc = checkpoint_hooks.restore(ctx, "cap6")
        conv_restaurado = ctx.cap_conv is not None
        acc_restaurado = ctx.cap_acc is not None
        with SessionLocal() as db_n2:
            store_n2 = PGVectorStore(ctx.embedder, EmbeddingRepository(db_n2), ctx.settings)
            store_n2.session_id = ctx.session_id
            cached_web_n2 = CachedWebConnector(  # T16.0-B
                ctx.web, db_n2, ctx.settings, counter=ctx.cache_web_counter
            )

            ctx.step_fn(6, "Cap 5 — Convergencia Empresarial")
            if not conv_restaurado and ctx.api_llm_synth is not None:
                ctx.cap_conv = GenerateConvergencia(
                    chain=build_chain_06_synth(ctx.api_llm_synth),
                    chain_eje=build_chain_06a(ctx.api_llm) if ctx.api_llm else None,
                    store=store_n2, web_connector=cached_web_n2,
                ).execute(
                    nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
                    sector_gics_code=g_code, empresa_id=ctx.empresa_id,
                )
                # DT-059/T3: auto-revisión sabor integración (solo re-sintetiza). Flag OFF = no-op.
                ctx.cap_conv = review_integration_cap(
                    settings=ctx.settings, llm=ctx.api_llm_synth,
                    capitulo_nombre="Cap 5 — Convergencia Empresarial",
                    criterios=CRITERIOS_CAPITULO["Cap 5 — Convergencia Empresarial"],
                    cap_obj=ctx.cap_conv, run_key=ctx.run_key,
                )

            ctx.step_fn(7, "Cap 6 — Accionables Estratégicos")
            if not acc_restaurado and ctx.api_llm is not None:
                # Coherencia (T22.1, Q1): pasar un resumen de los hallazgos de los caps ya
                # generados (2/3/4/5) para que los accionables los referencien explícitamente,
                # no solo el retrieval. Todos están disponibles en este punto del DAG.
                from ic.domain.coherence import build_caps_summary
                hallazgos = build_caps_summary([
                    (etiqueta, obj.texto)
                    for etiqueta, obj in [
                        ("Cap 2 — Benchmarking", ctx.cap),
                        ("Cap 3 — Tendencias", ctx.cap_tend),
                        ("Cap 4 — Ecosistema", ctx.cap_eco),
                        ("Cap 5 — Convergencia", ctx.cap_conv),
                    ]
                    if obj is not None and obj.retrieval_suficiente
                ])
                ctx.cap_acc = GenerateAccionables(
                    chain=build_chain_07(ctx.api_llm), store=store_n2,
                ).execute(
                    nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
                    sector_gics_code=g_code, empresa_id=ctx.empresa_id,
                    hallazgos_caps_previos=hallazgos,
                )
                ctx.cap_acc = review_integration_cap(
                    settings=ctx.settings, llm=ctx.api_llm,
                    capitulo_nombre="Cap 6 — Accionables Estratégicos",
                    criterios=CRITERIOS_CAPITULO["Cap 6 — Accionables Estratégicos"],
                    cap_obj=ctx.cap_acc, run_key=ctx.run_key,
                )

        ctx.step_fn(8, "Párrafos introductorios N2")
        if ctx.intro_chain is not None:
            # El intro se aplica solo a caps recién computados; los restaurados ya lo incluyen.
            for cap_obj, titulo, restaurado in [
                (ctx.cap_conv, "Convergencia Empresarial", conv_restaurado),
                (ctx.cap_acc, "Accionables Estratégicos", acc_restaurado),
            ]:
                if not restaurado and cap_obj is not None and cap_obj.retrieval_suficiente:
                    intro = ctx.intro_chain.invoke({
                        "titulo": titulo, "empresa": ctx.params.empresa,
                        "resumen_cap": cap_obj.texto[:500],
                    })
                    # DT-055: intro saneado puede quedar vacío → no anteponer líneas en blanco
                    if intro:
                        cap_obj.texto = intro + "\n\n" + cap_obj.texto

        # Persistir los caps recién computados (con intro) con keep-best + fallback (Fase 1).
        if not conv_restaurado:
            ctx.cap_conv = checkpoint_hooks.commit_best(ctx, "cap5", ctx.cap_conv)
        if not acc_restaurado:
            ctx.cap_acc = checkpoint_hooks.commit_best(ctx, "cap6", ctx.cap_acc)

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
            sector_code, hist.on_sector, hist.exento, hist.ajeno,
        )
        if hist.ajenos:
            logger.warning("Anti-mezcla: chunks de sector AJENO citados: %s", hist.ajenos)

        # Persistencia web "solo lo citado" (T14.5, DT-020): de los chunks web de esta sesión,
        # se promueven los efectivamente usados y se borra el resto de la búsqueda.
        self._promote_cited_web(ctx, todos_chunks)

        # Saneamiento de citas huérfanas (T22.A2, DT-052): las citas (Autor, año) del texto sin
        # referencia que las respalde se SUPRIMEN, no se inventa una fuente (RN-001). Se aplica a
        # cada capítulo antes del ensamblado y de la detección residual.
        caps_con_texto = [
            ctx.cap, ctx.cap_mercado, ctx.cap_tend, ctx.cap_eco,
            ctx.cap_conv, ctx.cap_acc, ctx.resumen,
        ]
        n_huerfanas_suprimidas = 0
        for cap_obj in caps_con_texto:
            if cap_obj is not None and getattr(cap_obj, "texto", None):
                cap_obj.texto, n_sup = strip_orphan_citations(cap_obj.texto, refs)
                n_huerfanas_suprimidas += n_sup
        if n_huerfanas_suprimidas:
            logger.info(
                "Citas huérfanas suprimidas (sin referencia): %d", n_huerfanas_suprimidas
            )

        texto_completo = " ".join(
            c.texto for c in caps_con_texto if c is not None
        )
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
        }

        informe = InformePiloto(
            empresa=ctx.empresa, gics=ctx.gics, cap_benchmarking=ctx.cap,
            cap_mercado=ctx.cap_mercado,
            cap_tendencias=ctx.cap_tend, cap_ecosistema=ctx.cap_eco,
            cap_convergencia=ctx.cap_conv, cap_accionables=ctx.cap_acc,
            resumen_ejecutivo=ctx.resumen, referencias=refs,
        )

        from ic.infrastructure.charts.radar_chart import (
            generate_placeholder_radar,
            generate_radar_chart,
        )
        from ic.infrastructure.render.docx_renderer import DocxRenderer
        from ic.infrastructure.render.pdf_renderer import convert_docx_to_pdf

        chart_path = ctx.output_path.replace(".docx", "_radar.png")
        try:
            # T16.1-D: usar datos reales del LLM si están disponibles; fallback a placeholder
            rd = ctx.cap.radar_data if ctx.cap else None
            if rd and rd.get("competidores") and rd.get("dimensions"):
                # T17.2 (DT-027): instrumentar hit del bloque radar_json emitido por el LLM.
                logger.info(
                    "Radar: datos reales del LLM — %d competidores, %d dimensiones",
                    len(rd["competidores"]), len(rd["dimensions"]),
                )
                generate_radar_chart(rd["competidores"], rd["dimensions"], chart_path,
                                     title=f"Posicionamiento Competitivo — {ctx.params.empresa}")
            else:
                logger.info("Radar: placeholder (radar_json ausente o no parseable) — DT-027 miss")
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
                # empresa_id ya resuelto en _run_n0 (T18.3); si falló, resolver aquí como fallback
                if ctx.empresa_id is None:
                    ctx.empresa_id = EmpresaRepository(db_h).upsert_by_name(ctx.params.empresa).id
                informe_repo = InformeRepository(db_h)
                rec = informe_repo.create(ctx.empresa_id, {"empresa": ctx.params.empresa})
                informe_repo.update_completado(
                    rec.id, ruta_docx=ctx.output_path, costo=ctx.tracker.total_cost(),
                    tiempo_s=time.time() - ctx.total_start,
                    tokens_in=tokens_in, tokens_out=tokens_out,
                    metricas=metricas_fiabilidad,
                )
        except Exception:
            logger.warning("No se pudo persistir historial", exc_info=True)

        # T17.1 (DT-026): instrumentación de hit-rate de caché por informe.
        wc = ctx.cache_web_counter
        oc = ctx.cache_oal_counter
        logger.info(
            "Cache web: %d HITs / %d MISSes — ahorro estimado: %.0f ms",
            wc.hits, wc.misses, wc.hits * _AVG_WEB_MS,
        )
        logger.info("Cache openalex: %d HITs / %d MISSes", oc.hits, oc.misses)

        # Fase 1: el caché por (empresa, ciiu) es DURABLE (sirve de fallback/reuso entre corridas).
        # Solo se limpia si la corrida no usa caché (clásico T22.3: no dejar checkpoint colgando).
        if not ctx.params.use_cache:
            checkpoint_hooks.clear(ctx)

        return InformeResult(
            ruta_docx=ctx.output_path, n_referencias=len(refs),
            costo_usd=ctx.tracker.total_cost(), tokens_in=tokens_in, tokens_out=tokens_out,
            tiempo_total_s=time.time() - ctx.total_start, cost_records=ctx.tracker.records(),
            ruta_pdf=ruta_pdf,
            cache_web_hits=wc.hits, cache_web_misses=wc.misses,
            cache_oal_hits=oc.hits, cache_oal_misses=oc.misses,
        )
