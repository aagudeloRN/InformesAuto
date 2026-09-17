# Tasks: 008 — Ingesta Masiva Paralela de PDFs e Infraestructura de Evidencia

**Branch**: `008-ingesta-paralela-evidencia`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Fecha**: 2026-09-17

---

## Phase 1: Setup — DTOs y estructura compartida

**Purpose**: Crear los tipos de datos compartidos (`TareaIngesta`, `ResultadoIngesta`, `FragmentoEnriquecido`) que ambas historias necesitan. No requieren BD ni Ollama activos.

- [x] T001 Crear dataclasses `TareaIngesta` y `ResultadoIngesta` en `src/ic/infrastructure/sources/parallel_ingestor.py` (esqueleto del módulo, sin lógica de threading aún)
- [x] T002 [P] Crear dataclass `FragmentoEnriquecido` en `src/ic/infrastructure/sources/enrichment_connector.py` (esqueleto del módulo)

Checkpoint Phase 1: DTOs disponibles para importar en tests y en las fases siguientes.

---

## Phase 2: Foundational — Tests unitarios base

**Purpose**: Escribir los tests antes de la implementación para que fallen primero (TDD). El spec incluye tests en los criterios de aceptación de ambas historias.

**⚠️ CRITICAL**: Completar antes de implementar lógica de negocio en Phases 3 y 4.

- [x] T003 [P] Crear `tests/test_parallel_ingestor.py` con tests que fallan: mock de `PdfIngestor.ingest_batched`; verificar N tareas → N futures; fallo aislado en una tarea; JSON lines emitidos a stdout (FR-004/FR-005)
- [x] T004 [P] Crear `tests/test_auto_enrich.py` con tests que fallan: mock de `pgvector_store.search_scores` (score < threshold); mock de `enrichment_connector.fetch_fragments`; verificar `try_enrich` retorna `True` y llama a `embedding_repo.save`; segundo llamado al mismo sector retorna `False` (FR-007/FR-010)

Checkpoint Phase 2: `uv run pytest tests/test_parallel_ingestor.py tests/test_auto_enrich.py` → todos FALLAN (rojo).

---

## Phase 3: User Story 1 — Ingesta Paralela Entre PDFs (Priority: P1)

**Goal**: `ingest_batch.py --workers N` procesa PDFs en paralelo con `ThreadPoolExecutor`, sesiones BD independientes por thread, JSON lines a stdout, fallo aislado por PDF.

**Independent Test**: `uv run python scripts/ingest_batch.py --workers 3 --dir docs/test_pdfs --csv docs/test_pdfs/indice.csv` → JSON lines con todos los archivos; re-ejecución produce `"n_chunks": 0` (idempotencia, SC-002).

### Implementación US1

- [x] T005 [US1] Implementar `_ingest_one(tarea, settings) -> ResultadoIngesta` en `src/ic/infrastructure/sources/parallel_ingestor.py`: instancia `PdfIngestor(settings)` propio, llama `ingest_batched()`, retry ×3 con backoff exponencial si `OllamaError`, captura cualquier excepción → `ResultadoIngesta(estado="error")` (FR-002, US1/AC3, US1/AC4)
- [x] T006 [US1] Implementar `ParallelIngestor.run_batch(tareas) -> list[ResultadoIngesta]` en `src/ic/infrastructure/sources/parallel_ingestor.py`: `ThreadPoolExecutor(max_workers)`, `submit(_ingest_one, tarea, settings)` por tarea, `as_completed()` con `threading.Lock` para print JSON lines a stdout (FR-001, FR-004, FR-005)
- [x] T007 [US1] Modificar `scripts/ingest_batch.py`: añadir `--workers N` (entero ≥ 1, default 1) a `argparse`; si `N > 1` recolectar filas CSV en lista de `TareaIngesta` y llamar `ParallelIngestor(settings, N).run_batch(tareas)`; si `N == 1` mantener bucle secuencial actual sin cambios; emitir JSON line de resumen final (FR-001, FR-004, FR-005, US1/AC1, US1/AC2)

Checkpoint US1: Tests `test_parallel_ingestor.py` en VERDE. `ingest_batch.py --workers 1` mantiene comportamiento anterior.

---

## Phase 4: User Story 2 — Enriquecimiento Automático de Sectores con Baja Evidencia (Priority: P2)

**Goal**: El pipeline de generación detecta sectores con retrieval score < `rag_sector_reserve_threshold` (0.5) y consulta OpenAlex/web para persistir fragmentos en pgvector antes de declarar ausencia.

**Independent Test**: Sector de prueba sin docs en índice → log muestra `AutoEnrich.try_enrich` activado → al menos 1 fragmento en `embedding_vectorial` con `metadatos->>'fuente' = 'openalex'` → degradación elegante si OpenAlex no responde (US2/AC4).

### Implementación US2

- [x] T008 [US2] Implementar `EnrichmentConnector.fetch_fragments(query, sector_gics, max_results=5) -> list[FragmentoEnriquecido]` en `src/ic/infrastructure/sources/enrichment_connector.py`: instancia `OpenAlexConnector(settings).search(query, max_results)` (polite pool ya configurado); si < 2 resultados → `WebConnector(settings).search(query)` como fallback; chunking simple por párrafos (≤512 tokens) → `FragmentoEnriquecido` con metadatos APA completos (`titulo`, `autores`, `año`, `url`, `fuente`, `idioma`) (FR-008, FR-012)
- [x] T009 [US2] Implementar `AutoEnrich.try_enrich(sector_gics, query_text, threshold) -> bool` en `src/ic/domain/use_cases/auto_enrich.py`: (1) `scores = pgvector_store.search_scores(query_text, sector_gics, top_k=5)`; (2) si `max(scores, default=0) >= threshold` → `return False`; (3) `fragmentos = enrichment_connector.fetch_fragments(query_text, sector_gics)`; (4) si no hay fragmentos → `return False`; (5) embedder.embed + embedding_repo.save por cada fragmento; (6) `return True` (FR-007, FR-008, FR-009, FR-010, FR-011)
- [x] T010 [US2] Integrar `AutoEnrich` en el pipeline de generación: añadir `_enriched_sectors: set[str]` a `InformeContext` en `src/ic/domain/use_cases/_informe_context.py`; en `src/ic/domain/use_cases/_n1_chapter_builders.py` (o el helper de retrieval de capítulos), después de retrieval < threshold y ANTES de `datos_ausentes()`, comprobar `sector_gics not in ctx._enriched_sectors`, llamar `auto_enrich.try_enrich(...)`, marcar sector como enriquecido, y si retorna `True` reintentar retrieval una vez (FR-007, FR-010, FR-011, US2/AC1, US2/AC2, US2/AC3, US2/AC4)

Checkpoint US2: Tests `test_auto_enrich.py` en VERDE. El pipeline no lanza excepción si `EnrichmentConnector` falla (degradación elegante).

---

## Phase 5: Polish — Verificación de invariantes y documentación

**Purpose**: Garantizar 0 regresiones, regla <300L, lint limpio.

- [x] T011 [P] Ejecutar `uv run ruff check . && black --check .` — 0 errores en todos los archivos nuevos y modificados (SC-007)
- [x] T012 [P] Ejecutar `uv run pytest tests/test_parallel_ingestor.py tests/test_auto_enrich.py -v` — todos VERDES (SC-007)
- [x] T013 [P] Verificar `find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -10` — ningún archivo supera 300 líneas (SC-006)
- [x] T014 Actualizar `docs/PROXIMA_SESION.md` y `CHANGELOG.md` documentando la finalización del Spec 008 y las instrucciones de migración (aplicar `scripts/migrations/007_add_aliases_column.sql` si aún no se ha hecho en prod)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Sin dependencias — empezar aquí
- **Phase 2 (Tests)**: Depende de Phase 1 (DTOs disponibles) — BLOQUEANTE para Phases 3 y 4
- **Phase 3 (US1)**: Depende de Phase 2; T005 y T006 son secuenciales entre sí; T007 depende de T006
- **Phase 4 (US2)**: Puede iniciar en paralelo con Phase 3 desde Phase 2; T008 y T009 son paralelos entre sí; T010 depende de T009
- **Phase 5 (Polish)**: Depende de Phases 3 y 4 completas

### Parallel Opportunities

- T001 y T002 (Phase 1): archivos distintos — paralelos
- T003 y T004 (Phase 2): archivos distintos — paralelos
- T005 y T008 (inicio de US1/US2): archivos distintos — paralelos si recursos disponibles
- T011, T012, T013 (Phase 5): independientes — paralelos

---

## Implementation Strategy

### MVP (Solo US1 — Ingesta Paralela)

1. Completar Phase 1: DTOs
2. Completar T003 (tests US1 en rojo)
3. Completar Phase 3: T005 → T006 → T007
4. **VALIDAR**: `uv run pytest tests/test_parallel_ingestor.py` en verde + smoke test con PDFs reales
5. Phase 5 parcial: lint + line count

### Entrega Completa

1. Phase 1 + Phase 2 (tests en rojo)
2. Phase 3 (US1) → tests en verde → validar
3. Phase 4 (US2) → tests en verde → validar con sector vacío
4. Phase 5 completa

---

## Phase 6: Convergence

- [x] T015 Emitir JSON summary line a stdout al final del lote paralelo en `scripts/ingest_batch.py`: `{"tipo": "resumen", "total": N, "ok": K, "errores": E, "duracion_s": T}` usando `sys.stdout.write` (no `logger.info`) por contrato (contract: resumen / FR-005) (missing)
- [x] T016 Añadir test de integración para `_maybe_auto_enrich` en `tests/test_auto_enrich.py` o `tests/test_n1_chapter_builders.py`: verificar que un segundo llamado al mismo `g_code` no dispara `AutoEnrich.try_enrich` (guard `_enriched_sectors`) per FR-010 / T004 (missing)
- [x] T017 Resolver `ResultadoIngesta.documento_id = None` en `src/ic/infrastructure/sources/parallel_ingestor.py`: obtener UUID del documento tras `ingest_batched()` o documentar en el contrato que este campo es `null` y eliminar del ejemplo JSON para no confundir per contract: output / data-model (partial)
- [x] T018 Usar idioma de metadatos en `EnrichmentConnector._to_fragmentos` en `src/ic/infrastructure/sources/enrichment_connector.py`: leer `res.metadatos.get("idioma")` o `res.language` con fallback `"es"` per spec edge-case / FR-012 (partial)
- [x] T019 Validar `args.workers >= 1` en `scripts/ingest_batch.py` y salir con código 1 si `--workers 0` o negativo per contract exit-codes / SC-001 (partial)
- [x] T020 Crear `specs/008-ingesta-paralela-evidencia/walkthrough.md` documentando evidencia de avance: lista de archivos creados/modificados, estado de tests (ruta para ejecutarlos), smoke test de ingesta paralela y enriquecimiento, instrucciones de migración de aliases (SQL 007) per user input (missing)
