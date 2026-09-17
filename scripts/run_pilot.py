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

# Configurar logging: ic.* en INFO, librerías verbosas en WARNING
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("ic").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

import httpx  # noqa: E402


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


# Acumulador de tiempos por paso para el resumen final
_step_times: dict[str, float] = {}
_step_start: float = 0.0
_last_step_label: str = ""


def _console_step(n: int, total: int, label: str) -> None:
    global _step_start, _last_step_label
    # Cerrar el paso anterior con su duración
    if _last_step_label:
        elapsed = time.time() - _step_start
        _step_times[_last_step_label] = elapsed
        print(f"✓  ({elapsed:.1f}s)")

    print(f"[{n}/{total}] {label}... ", end="", flush=True)
    _step_start = time.time()
    _last_step_label = label


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
        help="Ruta de salida del .docx (default: ./output/<empresa>.docx)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanuda una corrida interrumpida desde el último capítulo persistido (T22.3)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Invalida el caché durable de la empresa y regenera todo desde cero (Fase 1)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="No usa el caché durable (sin keep-best/fallback; comportamiento clásico)",
    )
    args = parser.parse_args()

    from ic.shared.config import get_settings

    settings = get_settings()

    # ── Verificación de servicios ──────────────────────────────────────
    _banner("Verificando servicios")

    ollama_ok = _check_ollama(settings.ollama_base_url)
    pg_ok = _check_postgres(settings.database_url)

    print(f"  Ollama    ({settings.ollama_base_url}): {'✅' if ollama_ok else '❌ NO DISPONIBLE'}")
    pg_status = "✅" if pg_ok else "❌ NO DISPONIBLE"
    print(f"  PostgreSQL ({settings.database_url[:40]}...): {pg_status}")

    if not ollama_ok:
        print(
            "\nError: Ollama no está corriendo. Verifica con: curl http://127.0.0.1:11434/api/tags"
        )
        sys.exit(1)
    if not pg_ok:
        print("\nError: PostgreSQL no responde. Verifica que repositorio_postgres esté activo.")
        sys.exit(1)

    from ic.domain.use_cases.generate_informe import GenerateInforme, InformeParams

    empresa_slug = args.empresa.replace(" ", "_").replace(".", "").lower()
    output_path = args.salida or f"./output/{empresa_slug}_informe.docx"

    _banner(f"Generando informe: {args.empresa}")

    uc = GenerateInforme(settings)
    params = InformeParams(
        empresa=args.empresa,
        ciiu=args.ciiu,
        output_path=output_path,
        resume=args.resume,
        refresh=args.refresh,
        use_cache=not args.no_cache,
    )

    global _step_times, _step_start, _last_step_label
    _step_times = {}
    _step_start = 0.0
    _last_step_label = ""

    result = uc.run(params, on_step=_console_step)

    # Cerrar el último paso
    if _last_step_label:
        elapsed = time.time() - _step_start
        _step_times[_last_step_label] = elapsed
        print(f"✓  ({elapsed:.1f}s)")

    # ── Resumen de ejecución ───────────────────────────────────────────
    _banner("Resumen de ejecución")
    if _step_times:
        max_t = max(_step_times.values()) or 1
        for paso, seg in _step_times.items():
            bar = "█" * int(seg / max_t * 20)
            print(f"  {paso:<40} {bar:<20} {seg:5.1f}s")
    print(f"\n  Tiempo total:  {result.tiempo_total_s:.1f}s")
    print(f"  Modelo local:  {settings.llm_local_analytic_model}")
    print(
        f"  Costo API:     ${result.costo_usd:.4f} USD  "
        f"({result.tokens_in:,} in / {result.tokens_out:,} out tokens)"
    )
    if result.cost_records:
        for rec in result.cost_records:
            print(
                f"    {rec.modelo:<52} in={rec.tokens_in:>7,}"
                f"  out={rec.tokens_out:>6,}  ${rec.costo_usd:.4f}"
            )
    print(f"  Referencias:   {result.n_referencias} únicas")
    print(f"\n  ✅ Documento guardado en: {result.ruta_docx}")


if __name__ == "__main__":
    main()
