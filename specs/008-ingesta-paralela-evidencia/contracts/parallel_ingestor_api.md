# Contract: ParallelIngestor CLI

## `scripts/ingest_batch.py` — CLI extendida

### Interfaz pública (flags)

```
usage: ingest_batch.py [--dir DIR] [--csv CSV] [--workers N]

optional arguments:
  --dir DIR       Carpeta con los PDFs (default: documentos_sectoriales)
  --csv CSV       Índice CSV del corpus (default: documentos_sectoriales/indice.csv)
  --workers N     Número de hilos concurrentes, entero ≥ 1 (default: 1)
```

**Backwards compatibility**: `--workers` es opcional; sin él, el comportamiento es idéntico a la versión anterior.

### Output Contract (stdout — JSON lines)

Cada PDF procesado emite exactamente una línea JSON:

```json
{"procesados": 1, "total": 50, "archivo": "emis_energia_2024.pdf", "estado": "ok", "n_chunks": 42, "documento_id": "uuid-..."}
{"procesados": 2, "total": 50, "archivo": "bad_file.pdf", "estado": "error", "error": "PdfReadError: EOF marker not found"}
```

Línea final de resumen:
```json
{"tipo": "resumen", "total": 50, "ok": 48, "errores": 2, "duracion_s": 87.3}
```

### Exit Codes

| Código | Significado |
|--------|-------------|
| 0 | Todos los archivos procesados sin errores |
| 1 | Error de configuración (CSV no encontrado, --workers < 1) |
| 2 | Completado con ≥ 1 error de PDF individual |

---

## `ParallelIngestor` — API Python interna

```python
from ic.infrastructure.sources.parallel_ingestor import ParallelIngestor, TareaIngesta

ingestor = ParallelIngestor(settings=settings, max_workers=4)
resultados = ingestor.run_batch(tareas=[
    TareaIngesta(pdf_path="/abs/path/doc.pdf", titulo="...", autor="...", año=2024,
                 sector_gics="5510", tipo="PDF_SECTORIAL", sectores_adicionales=None)
])
# resultados: list[ResultadoIngesta]
```

---

## `AutoEnrich` — API Python interna

```python
from ic.domain.use_cases.auto_enrich import AutoEnrich

enricher = AutoEnrich(
    pgvector_store=pgvector_store,
    enrichment_connector=enrichment_connector,
    embedder=embedder,
    embedding_repo=embedding_repo,
)
enriquecido = enricher.try_enrich(
    sector_gics="5510",
    query_text="energías renovables Colombia",
    threshold=0.5,  # rag_sector_reserve_threshold
)
# enriquecido: bool — True si se persistieron fragmentos nuevos
```
