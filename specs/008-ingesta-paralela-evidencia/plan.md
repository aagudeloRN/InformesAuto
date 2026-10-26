# Implementation Plan: 008 — Ingesta Masiva Paralela de PDFs e Infraestructura de Evidencia

**Branch**: `008-ingesta-paralela-evidencia` | **Date**: 2026-09-17 | **Spec**: [spec.md](spec.md)

---

## Summary

Dos mejoras de infraestructura independientes: (A) paralelizar la ingesta de PDFs en `ingest_batch.py` usando `ThreadPoolExecutor` con `PdfIngestor` ya thread-safe, y (B) añadir el caso de uso `AutoEnrich` que detecta sectores con evidencia insuficiente y los enriquece desde OpenAlex/web antes de declarar ausencia.

---

## Technical Context

**Language/Version**: Python 3.12 (uv)

**Primary Dependencies**: `concurrent.futures.ThreadPoolExecutor`, `PdfIngestor` (existente), `OpenAlexConnector` (existente), SQLAlchemy sessions (una por thread), pgvector

**Storage**: PostgreSQL + pgvector (esquema `informes_ic`); misma tabla `embeddings_vectoriales` para chunks de PDFs manuales y enriquecidos

**Testing**: `uv run pytest`; mocks de `PdfIngestor` y `OpenAlexConnector`; tests unitarios sin BD real

**Target Platform**: Linux server (WSL2 en dev, contenedor Docker en prod)

**Performance Goals**: SC-001 — lote de 50 PDFs con 4 workers en tiempo ≤ 40% del secuencial (≥ 2.5×)

**Constraints**: <300L por archivo (Constitución I); sesiones SQLAlchemy no compartidas entre threads; `openalex_email` en Settings ya existente

**Scale/Scope**: ~250 PDFs por lote; ~10 queries/sector para enriquecimiento

---

## Constitution Check

| Principio | Estado | Evidencia |
|-----------|--------|-----------|
| I — <300L por archivo | PASS | `parallel_ingestor.py` 147L; `auto_enrich.py` 213L; `enrichment_connector.py` 94L (medido 2026-10-26) |
| II — Agnosticismo de dependencias | PASS | `parallel_ingestor.py` bajo `infrastructure/`; `auto_enrich.py` bajo `domain/use_cases/` |
| I — Mezcla negocio/BD (regla 1) | EXCEPCIÓN DOCUMENTADA (ADR-018) | `auto_enrich.py` abre `SessionLocal` y construye `EmbeddingVectorial`, igual que otros 12 archivos de `domain/` (13 en total). Deuda estructural transversal, fuera del alcance de esta spec; el SQL ya vive en `EmbeddingRepository` (T025) |
| III — Sin alucinación / regla datos ausentes / RN-001 | PASS (tras T021–T024; RN-001: T031–T032 hechas; promoción en T033–T035) | `AutoEnrich` preserva la regla: si no hay evidencia post-enriquecimiento, párrafo de ausencia. El historial del informe registra cada evento de enriquecimiento (T023) |
| IV — Sin credenciales en código | PASS | `openalex_email` ya en Settings/.env; ningún secreto nuevo hardcodeado |
| V — Tests en mismo PR | PASS | `test_parallel_ingestor.py` + `test_auto_enrich.py` incluidos |
| VI — Cambios atómicos | PASS | `--workers 1` mantiene comportamiento secuencial; sin regresión |

---

## Decisión de Diseño — Deduplicación de Chunks

El spec (Q1) menciona constraint `(documento_id, chunk_index)`. El código existente en `pdf_ingestor.py` usa `chunk_sha256` (SHA-256 del texto del chunk) como clave de idempotencia — más robusto porque detecta duplicados cross-documento.

**Decisión: mantener SHA-256**. No se migra el esquema. `chunk_index` existe como campo posicional pero la identidad del chunk permanece en `chunk_sha256`. Esto evita una migración DDL sobre la BD compartida y es consistente con el comportamiento ya validado. `spec.md` (Q1, FR-003, caso límite) ya refleja esta decisión.

**Matices verificados en el código:**
- `chunk_sha256` NO es un constraint de la BD: `PdfIngestor` consulta `metadatos->>'chunk_sha256'` antes de insertar (`pdf_ingestor.py:57`). La consulta y la inserción no son atómicas, por lo que una carrera exacta entre dos workers podría duplicar un chunk.
- Los chunks de `AutoEnrich` guardan `chunk_sha256` y omiten los ya existentes o repetidos en el lote (FR-013, T025–T028).

---

## Decisión de Diseño — Umbral de Enriquecimiento

El spec (Q3) indica reutilizar `RETRIEVAL_MIN_SCORE`. El nombre real en `Settings` es `rag_sector_reserve_threshold` (0.5, más permisivo) y `rag_similarity_threshold` (0.6). El enriquecimiento se activa cuando el score máximo de retrieval es < `rag_sector_reserve_threshold` — el umbral más relajado, para no enriquecer innecesariamente cuando hay algo de evidencia. `spec.md` (Q3, FR-007) ya usa este nombre real.

---

## Project Structure

### Documentación (este feature)

```text
specs/008-ingesta-paralela-evidencia/
├── plan.md              <- este archivo
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── parallel_ingestor_api.md
└── tasks.md             (generado por /speckit-tasks)
```

### Código fuente

```text
scripts/
└── ingest_batch.py               [MODIFY] --workers N + ThreadPoolExecutor

src/ic/infrastructure/sources/
├── parallel_ingestor.py          [NEW] wrapper ThreadPoolExecutor, <120L
└── enrichment_connector.py       [NEW] fachada OpenAlex+web, <200L

src/ic/domain/use_cases/
└── auto_enrich.py                [NEW] caso de uso AutoEnrich, <180L

tests/
├── test_parallel_ingestor.py     [NEW]
└── test_auto_enrich.py           [NEW]
```

---

## Cambios por Capa

### A. `scripts/ingest_batch.py` [MODIFY]

- Añadir `--workers N` (entero ≥ 1, default 1).
- Si `N > 1`: recolectar filas CSV en lista de `TareaIngesta` y delegar a `ParallelIngestor.run_batch()`.
- Si `N == 1`: mantener bucle secuencial actual sin cambios (sin regresión).
- Emitir JSON lines a stdout por cada resultado: `{"procesados": N, "total": M, "archivo": ..., "estado": "ok"|"error", ...}`.

### B. `src/ic/infrastructure/sources/parallel_ingestor.py` [NEW, ~120L]

```
ParallelIngestor(settings, max_workers)
  run_batch(tareas: list[TareaIngesta]) -> list[ResultadoIngesta]
    ThreadPoolExecutor(max_workers)
    submit(_ingest_one, tarea) por cada tarea
    as_completed() → recoger ResultadoIngesta; print JSON line (con threading.Lock)
    return lista de resultados

_ingest_one(tarea, settings) -> ResultadoIngesta   [top-level, pickleable]
  PdfIngestor(settings)  <- sesión propia en el thread
  ingest_batched(...)    <- ya thread-safe (abre su SessionLocal internamente)
  retry ×3 con backoff si Ollama no responde
  capturar Exception → ResultadoIngesta(estado="error", error_msg=str(e))
```

### C. `src/ic/infrastructure/sources/enrichment_connector.py` [NEW, ~200L]

```
EnrichmentConnector(settings)
  fetch_fragments(query, sector_gics, max_results=5) -> list[FragmentoEnriquecido]
    1. OpenAlexConnector(settings).search(query, max_results)
    2. Si len(resultados) < 2: WebConnector(settings).search(query) como fallback
    3. Para cada resultado: chunking simple (párrafos) → FragmentoEnriquecido
       con metadatos: titulo, autores, año, url, fuente="openalex"|"web_enrichment", idioma
```

### D. `src/ic/domain/use_cases/auto_enrich.py` [NEW + MODIFY por T021, ~175L]

```
AutoEnrich(settings, embedder)            <- embedder OBLIGATORIO (T021); sin None ni vector de ceros
  try_enrich(sector_gics, query_text, threshold) -> EventoEnriquecimiento
    1. scores = search_scores(...)                       (PGVectorStore, sesión propia)
    2. if max(scores, default=0) >= threshold: resultado="suficiente"
    3. fragmentos = connector.fetch_fragments(query_text, sector_gics)
    4. if not fragmentos: resultado="sin_evidencia"
    4b. descartar fragmentos con chunk_sha256 ya existente (repo.exists_by_sha256) o repetidos; si no queda ninguno: resultado="ya_existentes" (sin reintentar retrieval)
    5. Para cada fragmento: embedder.embed(texto) → EmbeddingRepository.insert_many(chunks)
    6. resultado="enriquecido"; cualquier excepción → resultado="fallido" (+ error)
  EventoEnriquecimiento.enriquecido -> bool    (True solo si resultado == "enriquecido")
```

**Punto de integración**: `_maybe_auto_enrich` en `_n1_chapter_builders.py`, después de un retrieval < threshold y ANTES de `datos_ausentes()`:
- Comprobar `sector_gics not in ctx._enriched_sectors`
- Llamar `AutoEnrich(...).try_enrich(...)`
- Añadir sector a `ctx._enriched_sectors`
- Anexar el evento a `ctx.eventos_enriquecimiento` (T022); registrar excepciones con `logger.warning` (sin `except` silencioso)
- Si `evento.enriquecido`: reintentar retrieval una vez

### E. Trazabilidad del enriquecimiento (T021–T024)

- `EventoEnriquecimiento` (dataclass en `auto_enrich.py`) registra cada activación (spec US2/AC4, constitución III).
- `ctx.eventos_enriquecimiento: list` (nuevo campo en `_informe_context.py`).
- Persistencia: `_informe_nodes_n3.py` los guarda en `historial_informes.metricas_fiabilidad` (JSONB existente), clave `enriquecimiento`. Sin migración de esquema.
- `embedder` obligatorio (opción B acordada): en producción `ctx.embedder` siempre se construye con `Embedder(s)` (`_informe_context.py:144`), así que el `None` y el vector `[0.0] * 768` eran código muerto con riesgo de contaminar el índice compartido.

---

## Plan de Verificación

```bash
# 1. Tests unitarios
uv run pytest tests/test_parallel_ingestor.py tests/test_auto_enrich.py -v

# 2. Lint
uv run ruff check . && black --check .

# 3. Invariante <300L
find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -10

# 4. Smoke test ingesta paralela (requiere PDFs de prueba)
uv run python scripts/ingest_batch.py --dir docs/test_pdfs --csv docs/test_pdfs/indice.csv --workers 2
```
