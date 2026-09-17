"""Modulo de ingesta masiva paralela de PDFs (Spec 008 / US1)."""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import text

from ic.data.database import SessionLocal
from ic.infrastructure.sources.pdf_ingestor import PdfIngestor
from ic.shared.config import Settings

logger = logging.getLogger("parallel_ingestor")


@dataclass
class TareaIngesta:
    """Representa un PDF individual a procesar dentro del lote."""

    pdf_path: str
    titulo: str
    autor: str
    año: int | None
    sector_gics: str | None
    tipo: str
    sectores_adicionales: list[str] | None = None


@dataclass
class ResultadoIngesta:
    """Resultado del procesamiento de un PDF para serializacion a stdout."""

    archivo: str
    documento_id: str | None
    n_chunks_creados: int
    estado: Literal["ok", "error"]
    error_msg: str | None = None
    procesados: int = 0
    total: int = 0


def _ingest_one(tarea: TareaIngesta, settings: Settings) -> ResultadoIngesta:
    """Procesa un solo PDF instanciando su propio PdfIngestor con reintentos."""
    archivo_name = Path(tarea.pdf_path).name
    ingestor = PdfIngestor(settings)

    max_retries = 3
    backoff = 2.0
    last_err: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            n_chunks = ingestor.ingest_batched(
                pdf_path=tarea.pdf_path,
                titulo=tarea.titulo,
                autor=tarea.autor,
                año=tarea.año,
                sector_gics=tarea.sector_gics,
                tipo=tarea.tipo,
                sectores_adicionales=tarea.sectores_adicionales,
            )

            doc_id_str = None
            try:
                with SessionLocal() as db:
                    schema = getattr(settings, "db_schema", "informes_ic")
                    sql = text(
                        f"SELECT id FROM {schema}.documentos_locales WHERE titulo = :t LIMIT 1"
                    )
                    row = db.execute(sql, {"t": tarea.titulo}).scalar()
                    if row:
                        doc_id_str = str(row)
            except Exception:
                pass

            return ResultadoIngesta(
                archivo=archivo_name,
                documento_id=doc_id_str,
                n_chunks_creados=n_chunks,
                estado="ok",
            )
        except Exception as exc:
            last_err = exc
            if "Ollama" in type(exc).__name__ or "connection" in str(exc).lower():
                time.sleep(backoff**attempt)
                continue
            break

    return ResultadoIngesta(
        archivo=archivo_name,
        documento_id=None,
        n_chunks_creados=0,
        estado="error",
        error_msg=str(last_err) if last_err else "Error desconocido",
    )


class ParallelIngestor:
    """Coordinador multihilo para ingesta paralela de PDFs."""

    def __init__(self, settings: Settings, max_workers: int = 4) -> None:
        self.settings = settings
        self.max_workers = max(1, max_workers)
        self._lock = threading.Lock()

    def run_batch(self, tareas: list[TareaIngesta]) -> list[ResultadoIngesta]:
        """Ejecuta las tareas de ingesta en paralelo con ThreadPoolExecutor."""
        total = len(tareas)
        procesados = 0
        resultados: list[ResultadoIngesta] = []

        if not tareas:
            return resultados

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_tarea = {executor.submit(_ingest_one, t, self.settings): t for t in tareas}

            for future in as_completed(future_to_tarea):
                res = future.result()
                with self._lock:
                    procesados += 1
                    res.procesados = procesados
                    res.total = total
                    resultados.append(res)

                    out_dict = {
                        "archivo": res.archivo,
                        "documento_id": res.documento_id,
                        "estado": res.estado,
                        "n_chunks": res.n_chunks_creados,
                        "procesados": res.procesados,
                        "total": res.total,
                    }
                    if res.error_msg:
                        out_dict["error"] = res.error_msg
                    sys.stdout.write(json.dumps(out_dict, ensure_ascii=False) + "\n")
                    sys.stdout.flush()

        return resultados
