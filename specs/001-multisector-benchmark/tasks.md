# Tasks: Multi-sector en Benchmarking — DT-UI04f

**Input**: Design documents from `specs/001-multisector-benchmark/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Tests incluidos según criterios de aceptación del spec y regla V de la constitución
(cobertura ≥ 80% en domain; tests en el mismo PR).

**Organization**: Tareas agrupadas por User Story para implementación y testing independientes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivos distintos, sin dependencias sobre tareas incompletas)
- **[Story]**: User Story a la que pertenece la tarea (US1, US2, US3)

## Path Conventions

- Repositorio: `src/ic/`, `tests/`
- Repositorio raíz (single project)

---

## Phase 1: Setup (Baseline)

**Purpose**: Verificar que el estado de partida es limpio antes de cualquier cambio.

- [X] T001 Correr suite de tests existente para capturar baseline: `uv run pytest tests/test_kb_entidades.py tests/test_dt064_fichas.py -v --tb=short`
- [X] T002 [P] Verificar lint baseline: `uv run ruff check src/ic/data/repositories/entidad_repo.py src/ic/domain/use_cases/generate_n1.py`

**Checkpoint**: 0 fallos en los tests de regresión, lint limpio. Si algo falla aquí, investigar antes de continuar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No se requieren cambios de infraestructura nueva. `aliases` JSONB ya existe (research D3).
La función `_clave_exclusion` y el patrón `Sequence[str]` ya están en el mismo archivo (research D1).

*(Esta fase no tiene tareas — la Fase 3 puede iniciar directamente tras la Fase 1.)*

---

## Phase 3: User Story 1 — Multi-sector sin duplicados (Priority: P1) 🎯 MVP

**Goal**: `list_competidores_by_sector` acepta lista de sectores, consulta en una sola
operación, deduplica por entidad y el caller pasa la lista correcta.

**Independent Test**: `uv run pytest tests/test_kb_entidades.py -k "multisector" -v`
→ Resultado esperado: competidores de sectores `["1040","1050"]` retornados sin duplicados.

### Implementación — entidad_repo.py

- [X] T003 [US1] Cambiar firma de `list_competidores_by_sector`: `sector_gics: str` → `sectores_gics: str | Sequence[str]`; añadir bloque de normalización (str→lista, filtrar vacíos, corto-circuito si lista vacía) en `src/ic/data/repositories/entidad_repo.py` (línea ~298)
- [X] T004 [US1] Actualizar la query SQL de `list_competidores_by_sector`: cambiar `WHERE e.sector_gics = :sector` por `WHERE e.sector_gics = ANY(:sectores)` y ajustar el dict de params en `src/ic/data/repositories/entidad_repo.py` (línea ~319-328)
- [X] T005 [US1] Añadir deduplicación post-fetch por `_clave_exclusion(nombre)`: insertar set `vistos` y list comprehension que conserva la primera ocurrencia (mayor relevancia) antes de `rank_by_product_overlap` en `src/ic/data/repositories/entidad_repo.py` (línea ~332-344)

### Implementación — generate_n1.py

- [X] T006 [P] [US1] Actualizar la llamada a `list_competidores_by_sector` en `_descubrir_globales` para pasar `sectores_ancla_local(g_code, ciiu_ancla)` en lugar de `g_code` en `src/ic/domain/use_cases/generate_n1.py` (línea ~100)
- [X] T007 [P] [US1] Actualizar la llamada a `list_competidores_by_sector` en `_fn_cap2` para pasar `sectores_ancla_local(g_code, ciiu_ancla)` en lugar de `g_code or ""` en `src/ic/domain/use_cases/generate_n1.py` (línea ~198)

### Tests — User Story 1

- [X] T008 [P] [US1] Añadir `test_list_competidores_multisector_une_candidatos`: `_FakeSession` con entidades en `"1040"` y `"1050"`, verificar que ambas aparecen en el resultado sin duplicados en `tests/test_kb_entidades.py`
- [X] T009 [P] [US1] Añadir `test_list_competidores_multisector_sector_vacio_no_consulta`: lista vacía `[]` → retorna `[]` sin ejecutar SQL en `tests/test_kb_entidades.py`

**Checkpoint**: US1 completo. `uv run pytest tests/test_kb_entidades.py -v` debe pasar al 100%.

---

## Phase 4: User Story 2 — Exclusión por aliases (Priority: P2)

**Goal**: La empresa focal "NOEL SAS" no aparece en resultados aunque esté registrada como
"Compañía de Galletas NOEL" (vía campo `aliases` JSONB).

**Depends on**: T004 (SELECT modificado de US1, sobre el que se añade `e.aliases`)

**Independent Test**: `uv run pytest tests/test_kb_entidades.py -k "alias" -v`
→ La entidad cuyo alias normalizado coincide con `exclude_nombre` no aparece en resultados.

### Implementación — entidad_repo.py

- [X] T010 [US2] Añadir `e.aliases` al SELECT de `list_competidores_by_sector` para traer el campo JSONB en cada fila en `src/ic/data/repositories/entidad_repo.py` (línea ~319 del SELECT existente)
- [X] T011 [US2] Extender el predicado de exclusión: además de `_clave_exclusion(r.nombre)`, iterar `r.aliases or []` y excluir si alguno normaliza al mismo valor que `norm_excl` en `src/ic/data/repositories/entidad_repo.py` (línea ~332, dentro del list comprehension de `candidatos`)

### Tests — User Story 2

- [X] T012 [US2] Añadir `test_list_competidores_excluye_por_alias`: entidad con `aliases=["Compañía de Galletas NOEL"]`; llamar con `exclude_nombre="NOEL SAS"` → entidad no aparece en `tests/test_kb_entidades.py`

**Checkpoint**: US2 completo. `uv run pytest tests/test_kb_entidades.py -v` sigue al 100%.

---

## Phase 5: User Story 3 — Fichas multi-sector + backward compat (Priority: P3)

**Goal**: `list_ficha_atributos_by_sector` acepta lista de sectores; el caller lo usa;
los tests existentes (mono-sector) pasan sin modificación.

**Independent Test**: `uv run pytest tests/test_dt064_fichas.py -v`
→ Tests existentes pasan; test nuevo con lista retorna fichas de ambos sectores.

### Implementación — entidad_repo.py

- [X] T013 [US3] Cambiar firma de `list_ficha_atributos_by_sector`: `sector_gics: str` → `sectores_gics: str | Sequence[str]`; añadir normalización y corto-circuito en `src/ic/data/repositories/entidad_repo.py` (línea ~205)
- [X] T014 [US3] Actualizar SQL de `list_ficha_atributos_by_sector`: `WHERE e.sector_gics = :sector` → `WHERE e.sector_gics = ANY(:sectores)` y ajustar params en `src/ic/data/repositories/entidad_repo.py` (línea ~226-241)

### Implementación — generate_n1.py

- [X] T015 [US3] Actualizar la llamada a `list_ficha_atributos_by_sector` en `_fn_cap2` para pasar `sectores_ancla_local(g_code, ciiu_ancla)` en lugar de `g_code` en `src/ic/domain/use_cases/generate_n1.py` (línea ~225)

### Tests — User Story 3

- [X] T016 [US3] Añadir `test_fichas_multisector`: `_FakeSession` con competidores en `"3020"` y `"3030"`; llamar con `["3020","3030"]` → retorna fichas de ambos sectores en `tests/test_dt064_fichas.py`
- [X] T017 [US3] Ejecutar tests de regresión completos sin modificar los tests existentes: `uv run pytest tests/test_kb_entidades.py tests/test_dt064_fichas.py -v` → 0 fallos (backward compat verificada)

**Checkpoint**: Todos los User Stories completos. Suite completa en verde.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Calidad de código y validación E2E de los escenarios del quickstart.

- [X] T018 [P] Correr `uv run ruff check src/ic/data/repositories/entidad_repo.py src/ic/domain/use_cases/generate_n1.py` y resolver cualquier advertencia
- [X] T019 [P] Correr `uv run black --check src/ic/data/repositories/entidad_repo.py src/ic/domain/use_cases/generate_n1.py`; aplicar `black` si hay diferencias
- [X] T020 Ejecutar los 5 escenarios de validación de `specs/001-multisector-benchmark/quickstart.md` y confirmar que todos retornan los resultados esperados
- [X] T021 Registrar deuda técnica de refactor de `entidad_repo.py` (527 líneas, pre-existing): abrir ticket o entrada en `docs/decisions/` como DT-XXX

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Inicia de inmediato.
- **Foundational (Phase 2)**: No existe — US1 inicia tras Phase 1.
- **US1 (Phase 3)**: Inicia tras Phase 1. Bloquea US2 (T010 depende de T004).
- **US2 (Phase 4)**: Inicia tras T004 de US1. No bloquea US3.
- **US3 (Phase 5)**: Puede iniciarse en paralelo con US2 (archivos distintos en entidad_repo.py; distinto método).
- **Polish (Phase 6)**: Tras US1 + US2 + US3 completos.

### User Story Dependencies

- **US1 (P1)**: Independiente. Puede iniciar tras Phase 1.
- **US2 (P2)**: Depende de T004 (el SELECT de US1 debe estar modificado para añadir `e.aliases`).
- **US3 (P3)**: Independiente de US2. Puede correr en paralelo con US2 tras US1-T004.

### Within Each User Story

- `entidad_repo.py` changes (T003→T005, T010→T011, T013→T014): secuenciales dentro del mismo método.
- `generate_n1.py` changes (T006, T007, T015): [P] entre sí — distintos bloques del mismo archivo.
- Tests (T008, T009, T012, T016): [P] entre sí — distintas funciones en el mismo archivo.

---

## Parallel Opportunities

### US1 — Paralelo tras T004

```
T006 (generate_n1.py _descubrir_globales)  ←→  T007 (generate_n1.py _fn_cap2)
T008 (test multisector)                    ←→  T009 (test sector_vacio)
```

### US2 + US3 — Paralelo entre sí (distinto método en entidad_repo.py)

```
US2: T010 → T011 → T012
US3: T013 → T014 → T015 → T016 → T017
```

### Polish — Paralelo entre sí

```
T018 (ruff)  ←→  T019 (black)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — ~6 tareas de código)

1. Completar Phase 1 (baseline).
2. Completar Phase 3 (US1): T003 → T004 → T005 → (T006 ‖ T007) → (T008 ‖ T009).
3. **PARAR y VALIDAR**: `uv run pytest tests/test_kb_entidades.py -v` → todo verde.
4. Empresas multi-sector reciben competidores de todos sus sectores sin duplicados. ✅

### Incremental Delivery

1. Phase 1 → Phase 3 (US1): Multi-sector funcional. MVP.
2. Phase 4 (US2): Exclusión por alias. Análisis más robusto.
3. Phase 5 (US3): Fichas multi-sector + backward compat formal.
4. Phase 6: Polish y deuda documentada.

### One-Developer Sequence

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009
→ T010 → T011 → T012
→ T013 → T014 → T015 → T016 → T017
→ T018 → T019 → T020 → T021
```

---

## Notes

- `[P]` = archivos o bloques distintos, sin dependencias sobre tareas incompletas.
- `[Story]` mapea la tarea a su User Story para trazabilidad hacia spec.md.
- Los tests de regresión (T017) NO se modifican — su paso verifica backward compat.
- Cada checkpoint es un punto válido de parada y validación independiente.
- Commit sugerido al cerrar cada US: `feat(kb): DT-UI04f US1 — multi-sector competidores globales`.

---

## Phase 7: Convergence

- [X] T022 CRITICAL: Extraer SQL query builders de `entidad_repo.py` (581 líneas) a `src/ic/data/repositories/_entidad_queries.py` para que `entidad_repo.py` quede ≤ 300 líneas; exponer las funciones de construcción de queries como helpers internos del módulo; verificar que todos los tests pasan sin modificación tras el refactor per FR-008 + Constitution I (partial)
