"""Carga masiva del corpus sectorial desde documentos_sectoriales/indice.csv (Fase 13, T13.5).

Uso:
    uv run python scripts/ingest_batch.py
    uv run python scripts/ingest_batch.py --workers 4

Idempotente: PdfIngestor.ingest_batched salta documentos ya indexados (por título).
Recomendado ejecutar en tmux/nohup: el lote de 25 PDFs puede tardar 5-20 min.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

# Asegurar src/ en el path al ejecutar como script suelto
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ic.infrastructure.sources.parallel_ingestor import ParallelIngestor, TareaIngesta  # noqa: E402
from ic.infrastructure.sources.pdf_ingestor import PdfIngestor  # noqa: E402
from ic.shared.config import get_settings  # noqa: E402
from ic.shared.constants import TipoDocumento  # noqa: E402
from ic.shared.constants.gics_groups import gics_options  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_batch")


def _tipo_from_csv(valor: str) -> str:
    """Mapea el texto del CSV (ej. 'PDF_SECTORIAL') al valor del enum TipoDocumento."""
    try:
        return TipoDocumento[valor.strip()].value
    except KeyError:
        return TipoDocumento.PDF_SECTORIAL.value


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingesta masiva del corpus sectorial")
    parser.add_argument("--dir", default="documentos_sectoriales", help="Carpeta con los PDFs")
    parser.add_argument(
        "--csv", default="documentos_sectoriales/indice.csv", help="Índice CSV del corpus"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Número de hilos para ingesta paralela (default: 1)",
    )
    args = parser.parse_args()

    if args.workers < 1:
        logger.error("El número de workers debe ser >= 1 (recibido: %d)", args.workers)
        return 1

    start_time = time.time()
    base_dir = (_ROOT / args.dir).resolve()
    csv_path = (_ROOT / args.csv).resolve()

    if not csv_path.exists():
        logger.error("No existe el índice CSV: %s", csv_path)
        return 1

    nombre_por_codigo = dict(gics_options())
    settings = get_settings()

    tareas: list[TareaIngesta] = []
    errores_previos = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            archivo = (fila.get("archivo") or "").strip()
            sector = (fila.get("sector_gics") or "").strip()
            if not archivo:
                continue
            pdf_path = base_dir / archivo
            if not pdf_path.exists():
                pdf_path = _ROOT / archivo
            if not pdf_path.exists():
                logger.error("Archivo no encontrado: %s — se omite", pdf_path)
                errores_previos += 1
                continue

            nombre_sector = nombre_por_codigo.get(sector, sector)
            titulo_csv = (fila.get("titulo") or "").strip()
            titulo = titulo_csv or f"Informe sectorial: {nombre_sector}"
            tipo = _tipo_from_csv(fila.get("tipo") or "")
            autor = (fila.get("autor") or "Ruta N Medellín").strip() or "Ruta N Medellín"
            año_raw = (fila.get("año") or "").strip()
            año = int(año_raw) if año_raw.isdigit() else None
            sectores_add_raw = (fila.get("sectores_adicionales") or "").strip()
            sectores_adicionales = (
                [s.strip() for s in sectores_add_raw.split("|") if s.strip()]
                if sectores_add_raw
                else None
            )

            tareas.append(
                TareaIngesta(
                    pdf_path=str(pdf_path),
                    titulo=titulo,
                    autor=autor,
                    año=año,
                    sector_gics=sector or None,
                    tipo=tipo,
                    sectores_adicionales=sectores_adicionales,
                )
            )

    if args.workers > 1:
        logger.info("Iniciando ingesta paralela con %d workers...", args.workers)
        parallel_ingestor = ParallelIngestor(settings=settings, max_workers=args.workers)
        resultados = parallel_ingestor.run_batch(tareas)

        total_docs = len(resultados)
        total_chunks = sum(r.n_chunks_creados for r in resultados)
        errores = sum(1 for r in resultados if r.estado == "error") + errores_previos
    else:
        ingestor = PdfIngestor(settings)
        total_docs = 0
        total_chunks = 0
        errores = errores_previos

        for t in tareas:
            total_docs += 1
            logger.info("[%s] %s → %s", t.sector_gics, Path(t.pdf_path).name, t.titulo)
            try:
                n = ingestor.ingest_batched(
                    pdf_path=t.pdf_path,
                    titulo=t.titulo,
                    autor=t.autor,
                    año=t.año,
                    sector_gics=t.sector_gics,
                    tipo=t.tipo,
                    sectores_adicionales=t.sectores_adicionales,
                )
                total_chunks += n
                logger.info("  → %d chunks nuevos", n)
            except Exception:
                logger.exception("  ✗ Error al ingerir %s", Path(t.pdf_path).name)
                errores += 1

    duracion = round(time.time() - start_time, 2)
    summary_json = {
        "tipo": "resumen",
        "total": total_docs,
        "ok": max(0, total_docs - errores),
        "errores": errores,
        "duracion_s": duracion,
    }
    sys.stdout.write(json.dumps(summary_json, ensure_ascii=False) + "\n")
    sys.stdout.flush()

    logger.info(
        "Lote completado: %d documentos, %d chunks nuevos, %d errores (%s s)",
        total_docs,
        total_chunks,
        errores,
        duracion,
    )
    return 0 if errores == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
