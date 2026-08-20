# Tasks: Cap 2.1 — Activar Sub-módulos Modulares y Numeración de Secciones

**Input**: Design documents from `specs/003-cap21-activar-submodulos/`

**Branch**: `003-cap21-activar-submodulos`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivos distintos, sin dependencias incompletas)
- **[US?]**: User Story al que pertenece la tarea

---

## Phase 1: Foundational — Thread-safety de Generate21Startups

**Purpose**: Requisito bloqueante para US2 y US3. `Generate21Startups` debe poder abrir su propia sesión de BD cuando se invoca desde un thread pool. Sin este cambio el wiring del pipeline fallaría en runtime con sesión SQLAlchemy cerrada.

**⚠️ CRÍTICO**: Completar antes de comenzar US2.

- [x] T001 Agregar parámetro `db_factory: Callable | None = None` al constructor de `Generate21Startups` en `src/ic/domain/use_cases/generate_21_startups.py` (mantener `entidad_repo` como opcional backward-compatible)
- [x] T002 Modificar `Generate21Startups.execute()` en `src/ic/domain/use_cases/generate_21_startups.py` para usar `db_factory` (abrir sesión fresca) cuando `entidad_repo` es `None`; degradado silencioso (`filas_locales=[]`) si ambos son `None`

**Checkpoint**: `uv run pytest tests/test_generate_21_startups.py -v` pasa sin cambios (backward-compat con `entidad_repo` fake)

---

## Phase 2: User Story 1 — Sub-secciones numeradas (Priority: P1) 🎯 MVP

**Goal**: El texto del Cap 2.1 en cualquier informe generado muestra sub-encabezados `2.1.1.` / `2.1.2.` / `2.1.3.` cuando los sub-módulos producen datos suficientes.

**Independent Test**: `uv run pytest tests/test_generate_21_headings.py -v` → 3 tests pasan verificando el prefijo numérico en `texto` de cada sub-módulo con datos suficientes.

- [x] T003 [P] [US1] Cambiar `_HEADING = "### Referentes Globales"` → `_HEADING = "### 2.1.1. Referentes Globales"` en `src/ic/domain/use_cases/generate_21_globales.py` línea 24
- [x] T004 [P] [US1] Cambiar `_HEADING = "### Referentes Regionales LatAm/Colombia"` → `_HEADING = "### 2.1.2. Referentes Regionales LatAm/Colombia"` en `src/ic/domain/use_cases/generate_21_regionales.py` línea 24
- [x] T005 [P] [US1] Cambiar `_HEADING = "### Startups y Disruptores del sector"` → `_HEADING = "### 2.1.3. Startups y Disruptores del sector"` en `src/ic/domain/use_cases/generate_21_startups.py` línea 24
- [x] T006 [US1] Crear `tests/test_generate_21_headings.py` con tres tests unitarios (mocks, sin BD): verificar que `texto` de `Cap21Globales` / `Cap21Regionales` / `Cap21Startups` comienza con el encabezado numerado correspondiente cuando `retrieval_suficiente=True`

**Checkpoint**: `uv run pytest tests/test_generate_21_headings.py -v` → 3 tests pasan

---

## Phase 3: User Story 2 — Sub-módulos activos en el pipeline (Priority: P1)

**Goal**: `generate_n1._fn_cap2` instancia `Generate21Jugadores` (con sus tres sub-módulos) e inyecta el orquestador en `GenerateBenchmarking` junto con `engine` y `sub_gics`.

**Independent Test**: `uv run pytest tests/test_generate_n1_jugadores.py -v` → test pasa verificando que `jugadores_use_case.execute()` fue invocado al correr `_fn_cap2` con mocks.

- [x] T007 [US2] Añadir lazy imports dentro del cuerpo de `run_n1_parallel` en `src/ic/domain/use_cases/generate_n1.py`: `from ic.data.database import engine as db_engine, SessionLocal`, `from ic.domain.chains.chain_cap2_21_globales import build_chain_cap2_21_globales`, `from ic.domain.chains.chain_cap2_21_regionales import build_chain_cap2_21_regionales`, `from ic.domain.chains.chain_cap2_21_startups import build_chain_cap2_21_startups`, `from ic.domain.use_cases.generate_21_globales import Generate21Globales`, `from ic.domain.use_cases.generate_21_jugadores import Generate21Jugadores`, `from ic.domain.use_cases.generate_21_regionales import Generate21Regionales`, `from ic.domain.use_cases.generate_21_startups import Generate21Startups`
- [x] T008 [US2] Instanciar `Generate21Globales`, `Generate21Regionales`, `Generate21Startups` y `Generate21Jugadores` en `_fn_cap2` dentro de `src/ic/domain/use_cases/generate_n1.py`, justo antes de la llamada a `GenerateBenchmarking`. `Generate21Startups` recibe `db_factory=SessionLocal`. `llm_21 = ctx.api_llm or ctx.llm`.
- [x] T009 [US2] Pasar `jugadores_use_case=jugadores_use_case`, `engine=db_engine`, `sub_gics=g_code` al constructor de `GenerateBenchmarking` en `src/ic/domain/use_cases/generate_n1.py`
- [x] T010 [US2] Crear `tests/test_generate_n1_jugadores.py` con un test que: instancie un `_FakeJugadoresUseCase`, parchee las dependencias de `_fn_cap2` (store, web, LLM, `GenerateBenchmarking`), invoque el flujo, y verifique que `jugadores_use_case.execute()` fue llamado con los argumentos correctos (`nombre_empresa`, `sector_gics`, `sector_gics_code`)

**Checkpoint**: `uv run pytest tests/test_generate_n1_jugadores.py tests/test_generate_benchmarking_jugadores.py -v` → todos pasan

---

## Phase 4: User Story 3 — Cache sectorial activo (Priority: P2)

**Goal**: Verificar que el engine inyectado en T009 habilita la persistencia del cache sectorial: cuando existe un cache previo para el sector, los sub-módulos no se re-ejecutan.

**Independent Test**: `uv run pytest tests/test_generate_n1_jugadores.py::test_sector_cache_hit_pipeline -v` → pasa verificando que con cache previo, `jugadores_use_case.execute()` recibe `cached_globales` no-`None`.

- [x] T011 [US3] Añadir `test_sector_cache_hit_pipeline` a `tests/test_generate_n1_jugadores.py`: parchear `generate_benchmarking._load_sector_cache` para retornar un `Cap21Globales` cacheado y verificar que el argumento `cached_globales` pasa correctamente hacia `jugadores_use_case.execute()`

**Checkpoint**: `uv run pytest tests/test_generate_n1_jugadores.py -v` → todos los tests pasan

---

## Phase 5: Polish & Validación cruzada

**Purpose**: Limpieza, lint y regresión completa de los archivos modificados.

- [x] T012 [P] Ejecutar `uv run ruff check src/ic/domain/use_cases/generate_n1.py src/ic/domain/use_cases/generate_21_startups.py` y corregir cualquier error de lint en los archivos modificados
- [x] T013 [P] Ejecutar `uv run ruff check src/ic/domain/use_cases/generate_21_globales.py src/ic/domain/use_cases/generate_21_regionales.py` para confirmar que los cambios de `_HEADING` son limpios
- [x] T014 Ejecutar la suite de regresión completa: `uv run pytest tests/test_generate_benchmarking_jugadores.py tests/test_generate_21_headings.py tests/test_generate_n1_jugadores.py -v` y confirmar que todos los tests pasan

---

## Phase 6: Convergence

- [x] T015 Agregar test `test_subseccion_ausente_excluida_del_texto_ensamblado` en `tests/test_generate_21_jugadores.py`: dado que un sub-módulo retorna `retrieval_suficiente=False` y los otros dos `True`, verificar que el texto ensamblado de `Cap21Jugadores` NO contiene el sub-encabezado numerado del sub-módulo ausente per FR-006 / US1/AC2 (partial)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: Sin dependencias — comenzar inmediatamente
- **US1 (Phase 2)**: Independiente de la Foundational; puede correr en paralelo con Phase 1
- **US2 (Phase 3)**: Depende de Foundational completa (T001/T002) — `Generate21Startups` necesita `db_factory` antes del wiring
- **US3 (Phase 4)**: Depende de US2 completa (T007-T010)
- **Polish (Phase 5)**: Depende de todas las fases previas

### User Story Dependencies

- **US1 (P1)**: Puede comenzar inmediatamente — sin dependencias de otras stories
- **US2 (P1)**: Depende de Foundational (Phase 1)
- **US3 (P2)**: Depende de US2 completa

### Parallel Opportunities

- T003, T004, T005 → paralelos entre sí (archivos distintos)
- T012, T013 → paralelos entre sí (lint de archivos distintos)
- Phase 1 (Foundational) y Phase 2 (US1) → pueden correr simultáneamente (sin dependencia entre sí)

---

## Parallel Example: US1

```bash
# Los tres cambios de _HEADING son independientes — lanzar juntos:
# T003: generate_21_globales.py
# T004: generate_21_regionales.py
# T005: generate_21_startups.py (nota: mismo archivo que T001/T002 de Foundational — completar T002 antes)
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Phase 1: Foundational (T001-T002) — ~10 min
2. Phase 2: US1 headings (T003-T006) — ~15 min  
3. Phase 3: US2 wiring (T007-T010) — ~30 min
4. **STOP y VALIDAR**: `uv run pytest tests/test_generate_21_headings.py tests/test_generate_n1_jugadores.py tests/test_generate_benchmarking_jugadores.py -v`
5. Prueba manual en UI (quickstart.md validación 4)

### Incremental

1. Foundational → US1 → validar headings en UI → US2 → validar sub-módulos activos → US3 → validar cache → Polish

### Nota sobre `generate_n1.py`

El archivo supera 300 líneas (LEGACY, T043). Este plan agrega ~25 líneas netas de wiring. No se empeora la violación pero no se resuelve — requiere decisión de split por parte del humano.
