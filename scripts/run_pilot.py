"""Script CLI para generar un informe de IC piloto (Caps 1–6 + Resumen Ejecutivo).

Uso:
    uv run python scripts/run_pilot.py --empresa "Noel S.A.S."
    uv run python scripts/run_pilot.py --empresa "Noel S.A.S." --ciiu 1081
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Asegurar que src/ está en el path cuando se corre desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Silenciar logs verbosos de SQLAlchemy e httpx para que la salida sea legible
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

import httpx


def _check_ollama(base_url: str) -> bool:
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def _check_postgres(database_url: str) -> bool:
    try:
        import sqlalchemy

        engine = sqlalchemy.create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


def _banner(msg: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {msg}")
    print(f"{'─' * 60}")


def _step(n: int, total: int, msg: str) -> None:
    print(f"[{n}/{total}] {msg}... ", end="", flush=True)


def _ok(elapsed: float) -> None:
    print(f"✓  ({elapsed:.1f}s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un informe de inteligencia competitiva piloto en .docx"
    )
    parser.add_argument("--empresa", required=True, help='Nombre de la empresa, ej: "Noel S.A.S."')
    parser.add_argument(
        "--ciiu",
        default=None,
        help="Código CIIU (opcional; se extrae automáticamente del RUES si se omite)",
    )
    parser.add_argument(
        "--salida",
        default=None,
        help='Ruta de salida del .docx (default: ./output/<empresa>.docx)',
    )
    args = parser.parse_args()

    from ic.shared.config import get_settings

    settings = get_settings()

    # ── Verificación de servicios ──────────────────────────────────────
    _banner("Verificando servicios")

    ollama_ok = _check_ollama(settings.ollama_base_url)
    pg_ok = _check_postgres(settings.database_url)

    print(f"  Ollama    ({settings.ollama_base_url}): {'✅' if ollama_ok else '❌ NO DISPONIBLE'}")
    print(f"  PostgreSQL ({settings.database_url[:40]}...): {'✅' if pg_ok else '❌ NO DISPONIBLE'}")

    if not ollama_ok:
        print("\nError: Ollama no está corriendo. Verifica con: curl http://127.0.0.1:11434/api/tags")
        sys.exit(1)
    if not pg_ok:
        print("\nError: PostgreSQL no responde. Verifica que repositorio_postgres esté activo.")
        sys.exit(1)

    # ── Wiring de dependencias ─────────────────────────────────────────
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
    from ic.infrastructure.llm.gateway import build_api_llm, build_llm
    from ic.infrastructure.retrieval.embedder import Embedder
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
    from ic.infrastructure.sources.web_connector import WebConnector
    from ic.shared.types import InformePiloto

    llm = build_llm(settings)
    embedder = Embedder(settings)
    web = WebConnector(settings)

    empresa_slug = args.empresa.replace(" ", "_").replace(".", "").lower()
    output_path = args.salida or f"./output/{empresa_slug}_informe.docx"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    total_start = time.time()
    tiempos: dict[str, float] = {}

    _banner(f"Generando informe: {args.empresa}")

    # ── Construir LLMs por tier ────────────────────────────────────────
    api_llm = build_api_llm(settings, tier="free") if settings.openrouter_api_key else None
    api_llm_alt = (
        build_api_llm(settings, tier="free_alt")
        if settings.openrouter_api_key and settings.llm_api_free_alt_model
        else None
    )
    api_llm_synth = (
        build_api_llm(settings, tier="synth")
        if settings.openrouter_api_key
        else None
    )

    # Cadena de fallback para Cap 1: free API → free_alt API → local Ollama
    # Si no hay API key configurada, usa directamente el modelo local.
    cap1_llms = [m for m in [api_llm, api_llm_alt, llm] if m is not None]

    TOTAL_PASOS = 10

    with SessionLocal() as db:
        repo = EmbeddingRepository(db)
        store = PGVectorStore(embedder, repo, settings)

        # ── Cap 1: Descripción empresa ─────────────────────────────────
        _step(1, TOTAL_PASOS, "Cap 1 — Descripción de la empresa")
        t0 = time.time()
        uc_desc = GenerateEmpresaDescription(chain=build_chain_01(cap1_llms), web_connector=web)
        empresa = uc_desc.execute(args.empresa)
        # Si el usuario pasó --ciiu, sobreescribir el extraído automáticamente
        if args.ciiu:
            empresa = empresa.__class__(
                nombre_empresa=empresa.nombre_empresa,
                actividad_ciiu=args.ciiu,
                texto=empresa.texto,
            )
        tiempos["Cap 1"] = time.time() - t0
        _ok(tiempos["Cap 1"])
        print(f"       CIIU detectado: {empresa.actividad_ciiu}")

        # ── Clasificación GICS ─────────────────────────────────────────
        _step(2, TOTAL_PASOS, "GICS — Clasificación de sector")
        t0 = time.time()
        uc_gics = ClassifyGICS(chain=build_chain_02(llm))
        gics = uc_gics.execute(
            nombre_empresa=args.empresa, descripcion_empresa=empresa.texto
        )
        tiempos["GICS"] = time.time() - t0
        _ok(tiempos["GICS"])
        print(f"       Grupo GICS: {gics.grupo_gics}")

        # ── Cap 2: Benchmarking ────────────────────────────────────────
        _step(3, TOTAL_PASOS, "Cap 2 — Análisis Competitivo (búsqueda + retrieval + LLM)")
        t0 = time.time()
        uc_bench = GenerateBenchmarking(
            chain=build_chain_03(llm), store=store, web_connector=web
        )
        cap = uc_bench.execute(
            nombre_empresa=args.empresa,
            descripcion_empresa=empresa.texto,
            sector_gics=gics.grupo_gics,
        )
        tiempos["Cap 2"] = time.time() - t0
        _ok(tiempos["Cap 2"])
        retrieval_estado = (
            f"{cap.n_chunks_usados} chunks usados"
            if cap.retrieval_suficiente
            else "⚠️  retrieval insuficiente — párrafo de ausencia insertado"
        )
        print(f"       Retrieval: {retrieval_estado}")

        # ── Cap 3: Análisis Tendencial ─────────────────────────────────
        _step(4, TOTAL_PASOS, "Cap 3 — Análisis Tendencial (OpenAlex + web + LLM)")
        t0 = time.time()
        cap_tend = None
        if api_llm is not None:
            uc_tend = GenerateTendencias(
                chain=build_chain_04(api_llm),
                store=store,
                web_connector=web,
                openalex_connector=OpenAlexConnector(settings),
            )
            cap_tend = uc_tend.execute(
                nombre_empresa=args.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
            )
            tiempos["Cap 3"] = time.time() - t0
            _ok(tiempos["Cap 3"])
            retrieval_tend = (
                f"{cap_tend.n_chunks_usados} chunks usados"
                if cap_tend and cap_tend.retrieval_suficiente
                else "⚠️  retrieval insuficiente — párrafo de ausencia insertado"
            )
            print(f"       Retrieval: {retrieval_tend}")
        else:
            tiempos["Cap 3"] = 0.0
            print(f"⚠️  OPENROUTER_API_KEY no configurada — Cap 3 omitido")

        # ── Cap 4: Ecosistema Empresarial ──────────────────────────────
        _step(5, TOTAL_PASOS, "Cap 4 — Ecosistema Empresarial (web + LLM)")
        t0 = time.time()
        cap_eco = None
        if api_llm is not None:
            uc_eco = GenerateEcosistema(
                chain=build_chain_05(api_llm),
                store=store,
                web_connector=web,
            )
            cap_eco = uc_eco.execute(
                nombre_empresa=args.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
            )
            tiempos["Cap 4"] = time.time() - t0
            _ok(tiempos["Cap 4"])
            retrieval_eco = (
                f"{cap_eco.n_chunks_usados} chunks usados"
                if cap_eco and cap_eco.retrieval_suficiente
                else "⚠️  retrieval insuficiente — párrafo de ausencia insertado"
            )
            print(f"       Retrieval: {retrieval_eco}")
        else:
            tiempos["Cap 4"] = 0.0
            print(f"⚠️  OPENROUTER_API_KEY no configurada — Cap 4 omitido")

        # ── PDF Convergencia (ingesta automática condicional) ──────────
        PDF_CONVERGENCIA = Path(__file__).parent.parent / "InformeConvergenciaLocal2026V3RvADAA.pdf"
        if PDF_CONVERGENCIA.exists():
            _step(6, TOTAL_PASOS, "PDF Convergencia — ingesta automática")
            t0 = time.time()
            sys.path.insert(0, str(Path(__file__).parent))
            from ingest_pdf import _ensure_metadatos_column, ingest_pdf as _ingest_pdf
            _ensure_metadatos_column()
            n_pdf = _ingest_pdf(
                pdf_path=str(PDF_CONVERGENCIA),
                empresa_id=None,
                titulo="Informe de Convergencia Local Medellín 2026",
                autor="Alcaldía de Medellín",
                año=2026,
            )
            tiempos["PDF Convergencia"] = time.time() - t0
            _ok(tiempos["PDF Convergencia"])
            print(f"       {n_pdf} chunks ingestados (0 = ya ingestado previamente)")
        else:
            tiempos["PDF Convergencia"] = 0.0
            print(
                f"[6/{TOTAL_PASOS}] PDF Convergencia — archivo no encontrado, "
                "Cap 5 usará solo RAG de capítulos anteriores"
            )

        # ── Cap 5: Convergencia Empresarial ───────────────────────────
        _step(7, TOTAL_PASOS, "Cap 5 — Convergencia Empresarial (synth + RAG cruzado)")
        t0 = time.time()
        cap_conv = None
        if api_llm_synth is not None:
            uc_conv = GenerateConvergencia(
                chain=build_chain_06(api_llm_synth),
                store=store,
                web_connector=web,
            )
            cap_conv = uc_conv.execute(
                nombre_empresa=args.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
            )
            tiempos["Cap 5"] = time.time() - t0
            _ok(tiempos["Cap 5"])
            retrieval_conv = (
                f"{cap_conv.n_chunks_usados} chunks usados"
                if cap_conv and cap_conv.retrieval_suficiente
                else "⚠️  retrieval insuficiente — párrafo de ausencia insertado"
            )
            print(f"       Retrieval: {retrieval_conv}")
        else:
            tiempos["Cap 5"] = 0.0
            print(f"⚠️  OPENROUTER_API_KEY no configurada — Cap 5 omitido")

        # ── Cap 6: Accionables Estratégicos ───────────────────────────
        _step(8, TOTAL_PASOS, "Cap 6 — Accionables Estratégicos (free + RAG cruzado)")
        t0 = time.time()
        cap_acc = None
        if api_llm is not None:
            uc_acc = GenerateAccionables(
                chain=build_chain_07(api_llm),
                store=store,
            )
            cap_acc = uc_acc.execute(
                nombre_empresa=args.empresa,
                descripcion_empresa=empresa.texto,
                sector_gics=gics.grupo_gics,
            )
            tiempos["Cap 6"] = time.time() - t0
            _ok(tiempos["Cap 6"])
            retrieval_acc = (
                f"{cap_acc.n_chunks_usados} chunks usados"
                if cap_acc and cap_acc.retrieval_suficiente
                else "⚠️  retrieval insuficiente — párrafo de ausencia insertado"
            )
            print(f"       Retrieval: {retrieval_acc}")
        else:
            tiempos["Cap 6"] = 0.0
            print(f"⚠️  OPENROUTER_API_KEY no configurada — Cap 6 omitido")

    # ── Resumen Ejecutivo (N3 — sin retrieval) ────────────────────────
    _step(9, TOTAL_PASOS, "Resumen Ejecutivo (synth — síntesis del informe completo)")
    t0 = time.time()
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
            nombre_empresa=args.empresa,
            descripcion_empresa=empresa.texto,
            sector_gics=gics.grupo_gics,
            cap_textos=cap_textos,
        )
        tiempos["Resumen Ejecutivo"] = time.time() - t0
        _ok(tiempos["Resumen Ejecutivo"])
    else:
        tiempos["Resumen Ejecutivo"] = 0.0
        print(f"⚠️  OPENROUTER_API_KEY no configurada — Resumen Ejecutivo omitido")

    # ── Referencias APA ───────────────────────────────────────────────
    _step(10, TOTAL_PASOS, "Referencias + Ensamblado .docx")
    t0 = time.time()
    todos_chunks = list(cap.chunks_usados)
    if cap_tend and cap_tend.chunks_usados:
        todos_chunks += cap_tend.chunks_usados
    if cap_eco and cap_eco.chunks_usados:
        todos_chunks += cap_eco.chunks_usados
    if cap_conv and cap_conv.chunks_usados:
        todos_chunks += cap_conv.chunks_usados
    if cap_acc and cap_acc.chunks_usados:
        todos_chunks += cap_acc.chunks_usados
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
    assembler = PilotAssembler(DocxBuilder(settings.docx_template_path or None))
    assembler.assemble(informe, output_path)
    tiempos["Ensamblado"] = time.time() - t0
    _ok(tiempos["Ensamblado"])
    print(f"       {len(refs)} referencias únicas")

    # ── Resumen de ejecución ───────────────────────────────────────────
    total_s = time.time() - total_start
    _banner("Resumen de ejecución")
    for paso, seg in tiempos.items():
        bar = "█" * int(seg / max(tiempos.values()) * 20)
        print(f"  {paso:<15} {bar:<20} {seg:5.1f}s")
    print(f"\n  Tiempo total:  {total_s:.1f}s")
    print(f"  Modelo local:  {settings.llm_local_analytic_model}")
    print(f"  Costo API:     $0.00 (solo local — Etapa B implementará tracking)")
    print(f"\n  ✅ Documento guardado en: {output_path}")


if __name__ == "__main__":
    main()
