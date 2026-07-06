"""Orchestrator use case: genera el informe completo de IC (Caps 1–6 + Resumen Ejecutivo).

Separa la lógica de orquestación del pipeline de cualquier concern de presentación
(CLI o UI). El progreso se reporta vía callback `on_step`, que cada cliente implementa
como quiera (print, st.progress, queue, etc.).
"""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

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

        from ic.data.database import SessionLocal
        from ic.data.repositories.embedding_repo import EmbeddingRepository
        from ic.domain.assembler import PilotAssembler
        from ic.domain.chains.chain_01_descripcion import build_chain_01
        from ic.domain.chains.chain_02_gics import build_chain_02
        from ic.domain.chains.chain_03_benchmarking import build_chain_03
        from ic.domain.chains.chain_04_tendencias import build_chain_04
        from ic.domain.chains.chain_05_ecosistema import build_chain_05
        from ic.domain.chains.chain_06_convergencia import build_chain_06
        from ic.domain.chains.chain_07_accionables import build_chain_07
        from ic.domain.chains.chain_08_resumen_ejecutivo import build_chain_08
        from ic.domain.chains.chain_intro import build_chain_intro
        from ic.domain.use_cases.classify_gics import ClassifyGICS
        from ic.domain.use_cases.generate_accionables import GenerateAccionables
        from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
        from ic.domain.use_cases.generate_convergencia import GenerateConvergencia
        from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
        from ic.domain.use_cases.generate_empresa_description import GenerateEmpresaDescription
        from ic.domain.use_cases.generate_resumen_ejecutivo import GenerateResumenEjecutivo
        from ic.domain.use_cases.generate_tendencias import GenerateTendencias
        from ic.infrastructure.citation.apa_formatter import build_references_section
        from ic.infrastructure.docx_builder import DocxBuilder
        from ic.infrastructure.llm.gateway import CostTracker, build_api_llm, build_llm
        from ic.infrastructure.retrieval.embedder import Embedder
        from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
        from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
        from ic.infrastructure.sources.web_connector import WebConnector
        from ic.shared.types import InformePiloto
        _logging.getLogger("sqlalchemy.engine").setLevel(_logging.WARNING)
        _logging.getLogger("httpx").setLevel(_logging.WARNING)
        _logging.getLogger("httpcore").setLevel(_logging.WARNING)

        s = self._settings
        total_start = time.time()

        def _step(n: int, label: str) -> None:
            if on_step:
                on_step(n, self.TOTAL_PASOS, label)

        # ── Wiring de infraestructura ──────────────────────────────────────
        llm = build_llm(s)
        embedder = Embedder(s)
        web = WebConnector(s)
        tracker = CostTracker(budget_limit=s.llm_budget_limit_usd)

        api_llm = (
            build_api_llm(s, tier="free", cost_tracker=tracker)
            if s.openrouter_api_key
            else None
        )
        api_llm_alt = (
            build_api_llm(s, tier="free_alt", cost_tracker=tracker)
            if s.openrouter_api_key and s.llm_api_free_alt_model
            else None
        )
        api_llm_synth = (
            build_api_llm(s, tier="synth", cost_tracker=tracker)
            if s.openrouter_api_key
            else None
        )
        cap1_llms = [m for m in [api_llm, api_llm_alt, llm] if m is not None]

        empresa_slug = params.empresa.replace(" ", "_").replace(".", "").lower()
        output_path = params.output_path or f"./output/{empresa_slug}_informe.docx"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # ── Cap 1 — Descripción ────────────────────────────────────────────
        _step(1, "Cap 1 — Descripción de la empresa")
        uc_desc = GenerateEmpresaDescription(chain=build_chain_01(cap1_llms), web_connector=web)
        empresa = uc_desc.execute(params.empresa)
        if params.ciiu:
            empresa = empresa.__class__(
                nombre_empresa=empresa.nombre_empresa,
                actividad_ciiu=params.ciiu,
                texto=empresa.texto,
            )

        # ── GICS ──────────────────────────────────────────────────────────
        _step(2, "GICS — Clasificación de sector")
        uc_gics = ClassifyGICS(chain=build_chain_02(llm))
        gics = uc_gics.execute(
            nombre_empresa=params.empresa, descripcion_empresa=empresa.texto
        )

        # ── N1 paralelo: Caps 2, 3, 4 ─────────────────────────────────────
        _step(3, "N1 — Caps 2/3/4 en paralelo")

        def _make_store_and_run(fn):
            with SessionLocal() as db_t:
                repo_t = EmbeddingRepository(db_t)
                store_t = PGVectorStore(embedder, repo_t, s)
                return fn(store_t)

        def _fn_cap2(store_t):
            uc = GenerateBenchmarking(chain=build_chain_03(llm), store=store_t, web_connector=web)
            return uc.execute(
                nombre_empresa=params.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
            )

        def _fn_cap3(store_t):
            if api_llm is None:
                return None
            uc = GenerateTendencias(
                chain=build_chain_04(api_llm),
                store=store_t,
                web_connector=web,
                openalex_connector=OpenAlexConnector(s),
            )
            return uc.execute(
                nombre_empresa=params.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
            )

        def _fn_cap4(store_t):
            if api_llm is None:
                return None
            uc = GenerateEcosistema(
                chain=build_chain_05(api_llm),
                store=store_t,
                web_connector=web,
            )
            return uc.execute(
                nombre_empresa=params.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
            )

        with ThreadPoolExecutor(max_workers=3) as pool:
            f2 = pool.submit(_make_store_and_run, _fn_cap2)
            f3 = pool.submit(_make_store_and_run, _fn_cap3)
            f4 = pool.submit(_make_store_and_run, _fn_cap4)

        cap = f2.result()
        cap_tend = f3.result()
        cap_eco = f4.result()

        # ── Párrafos intro N1 ─────────────────────────────────────────────
        _step(4, "Párrafos introductorios N1")
        intro_chain = build_chain_intro(api_llm) if api_llm is not None else None
        if intro_chain is not None:
            for cap_obj, titulo in [
                (cap, "Análisis Competitivo"),
                (cap_tend, "Análisis Sectorial Tendencial"),
                (cap_eco, "Ecosistema Empresarial"),
            ]:
                if cap_obj is not None and cap_obj.retrieval_suficiente:
                    intro = intro_chain.invoke({
                        "titulo": titulo,
                        "empresa": params.empresa,
                        "resumen_cap": cap_obj.texto[:500],
                    })
                    cap_obj.texto = intro + "\n\n" + cap_obj.texto

        # ── PDF Convergencia (ingesta condicional) ─────────────────────────
        _step(5, "PDF Convergencia — ingesta condicional")
        import sys as _sys
        _PDF_NAME = "InformeConvergenciaLocal2026V3RvADAA.pdf"
        PDF_CONV = Path(__file__).parent.parent.parent.parent.parent / _PDF_NAME
        if not PDF_CONV.exists():
            # Buscar en el directorio raíz del proyecto
            PDF_CONV = Path(__file__).resolve()
            for _ in range(6):
                PDF_CONV = PDF_CONV.parent
                candidate = PDF_CONV / "InformeConvergenciaLocal2026V3RvADAA.pdf"
                if candidate.exists():
                    PDF_CONV = candidate
                    break
            else:
                PDF_CONV = Path("InformeConvergenciaLocal2026V3RvADAA.pdf")

        if PDF_CONV.exists():
            scripts_dir = str(PDF_CONV.parent / "scripts")
            if scripts_dir not in _sys.path:
                _sys.path.insert(0, scripts_dir)
            try:
                from ingest_pdf import _ensure_metadatos_column
                from ingest_pdf import ingest_pdf as _ingest_pdf
                _ensure_metadatos_column()
                _ingest_pdf(
                    pdf_path=str(PDF_CONV),
                    empresa_id=None,
                    titulo="Informe de Convergencia Local Medellín 2026",
                    autor="Alcaldía de Medellín",
                    año=2026,
                )
            except Exception as _exc:
                logger.warning("No se pudo ingestar PDF Convergencia", exc_info=True)
                print(f"  ⚠️  PDF Convergencia omitido: {type(_exc).__name__}: {_exc}")

        # ── N2: Caps 5 y 6 ────────────────────────────────────────────────
        cap_conv = None
        cap_acc = None
        with SessionLocal() as db_n2:
            repo_n2 = EmbeddingRepository(db_n2)
            store_n2 = PGVectorStore(embedder, repo_n2, s)

            _step(6, "Cap 5 — Convergencia Empresarial")
            if api_llm_synth is not None:
                uc_conv = GenerateConvergencia(
                    chain=build_chain_06(api_llm_synth),
                    store=store_n2,
                    web_connector=web,
                )
                cap_conv = uc_conv.execute(
                    nombre_empresa=params.empresa,
                    descripcion_empresa=empresa.texto,
                    sector_gics=gics.grupo_gics,
                )

            _step(7, "Cap 6 — Accionables Estratégicos")
            if api_llm is not None:
                uc_acc = GenerateAccionables(
                    chain=build_chain_07(api_llm),
                    store=store_n2,
                )
                cap_acc = uc_acc.execute(
                    nombre_empresa=params.empresa,
                    descripcion_empresa=empresa.texto,
                    sector_gics=gics.grupo_gics,
                )

        # ── Párrafos intro N2 ─────────────────────────────────────────────
        _step(8, "Párrafos introductorios N2")
        if intro_chain is not None:
            for cap_obj, titulo in [
                (cap_conv, "Convergencia Empresarial"),
                (cap_acc, "Accionables Estratégicos"),
            ]:
                if cap_obj is not None and cap_obj.retrieval_suficiente:
                    intro = intro_chain.invoke({
                        "titulo": titulo,
                        "empresa": params.empresa,
                        "resumen_cap": cap_obj.texto[:500],
                    })
                    cap_obj.texto = intro + "\n\n" + cap_obj.texto

        # ── Resumen Ejecutivo (N3) ─────────────────────────────────────────
        _step(9, "Resumen Ejecutivo")
        resumen = None
        if api_llm_synth is not None:
            cap_textos: dict[str, str] = {
                "Cap 1: Descripción": empresa.texto,
                "Cap 2: Benchmarking": cap.texto,
            }
            if cap_tend:
                cap_textos["Cap 3: Tendencias"] = cap_tend.texto
            if cap_eco:
                cap_textos["Cap 4: Ecosistema"] = cap_eco.texto
            if cap_conv:
                cap_textos["Cap 5: Convergencia"] = cap_conv.texto
            if cap_acc:
                cap_textos["Cap 6: Accionables"] = cap_acc.texto

            uc_re = GenerateResumenEjecutivo(chain=build_chain_08(api_llm_synth))
            resumen = uc_re.execute(
                nombre_empresa=params.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
                cap_textos=cap_textos,
            )

        # ── Referencias + Ensamblado ───────────────────────────────────────
        _step(10, "Referencias + Ensamblado .docx")
        todos_chunks = list(cap.chunks_usados)
        for cap_obj in [cap_tend, cap_eco, cap_conv, cap_acc]:
            if cap_obj and cap_obj.chunks_usados:
                todos_chunks += cap_obj.chunks_usados
        refs = build_references_section(todos_chunks)

        informe = InformePiloto(
            empresa=empresa,
            gics=gics,
            cap_benchmarking=cap,
            cap_tendencias=cap_tend,
            cap_ecosistema=cap_eco,
            cap_convergencia=cap_conv,
            cap_accionables=cap_acc,
            resumen_ejecutivo=resumen,
            referencias=refs,
        )
        assembler = PilotAssembler(DocxBuilder(s.docx_template_path or None))
        assembler.assemble(informe, output_path)

        tokens_in, tokens_out = tracker.total_tokens()
        return InformeResult(
            ruta_docx=output_path,
            n_referencias=len(refs),
            costo_usd=tracker.total_cost(),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tiempo_total_s=time.time() - total_start,
            cost_records=tracker.records(),
        )
