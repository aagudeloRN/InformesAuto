"""Script CLI para generar un informe de IC piloto (Caps 1, GICS, Cap 2).

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
    from ic.domain.chains.chain_01_descripcion import build_chain_01
    from ic.domain.chains.chain_02_gics import build_chain_02
    from ic.domain.chains.chain_03_benchmarking import build_chain_03
    from ic.domain.use_cases.classify_gics import ClassifyGICS
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
    from ic.domain.use_cases.generate_empresa_description import GenerateEmpresaDescription
    from ic.infrastructure.citation.apa_formatter import build_references_section
    from ic.infrastructure.docx_builder import DocxBuilder
    from ic.infrastructure.llm.gateway import build_llm
    from ic.infrastructure.retrieval.embedder import Embedder
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.web_connector import WebConnector
    from ic.domain.assembler import PilotAssembler
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

    with SessionLocal() as db:
        repo = EmbeddingRepository(db)
        store = PGVectorStore(embedder, repo, settings)

        # ── Cap 1: Descripción empresa ─────────────────────────────────
        TOTAL_PASOS = 5
        _step(1, TOTAL_PASOS, "Cap 1 — Descripción de la empresa")
        t0 = time.time()
        uc_desc = GenerateEmpresaDescription(chain=build_chain_01(llm), web_connector=web)
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

    # ── Referencias APA ───────────────────────────────────────────────
    _step(4, TOTAL_PASOS, "Referencias — Formateo APA 7")
    t0 = time.time()
    refs = build_references_section(cap.chunks_usados)
    tiempos["Referencias"] = time.time() - t0
    _ok(tiempos["Referencias"])
    print(f"       {len(refs)} referencias únicas")

    # ── Ensamblado .docx ──────────────────────────────────────────────
    _step(5, TOTAL_PASOS, f"Ensamblado → {output_path}")
    t0 = time.time()
    informe = InformePiloto(
        empresa=empresa,
        gics=gics,
        cap_benchmarking=cap,
        referencias=refs,
    )
    assembler = PilotAssembler(DocxBuilder(settings.docx_template_path or None))
    assembler.assemble(informe, output_path)
    tiempos["Ensamblado"] = time.time() - t0
    _ok(tiempos["Ensamblado"])

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
