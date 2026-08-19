---
description: "Task list — Cap 2.1 Jugadores Clave Modular"
---

# Tasks: Cap 2.1 — Jugadores Clave Modular

**Input**: `specs/002-cap21-jugadores-clave/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Incluidos — cada US tiene suite mínima con `_FakeSession` (sin DB real).

**Organization**: Tareas agrupadas por fase. Fase 2 bloquea todo lo demás. Las US 1-3 pueden ejecutarse en paralelo una vez Phase 2 esté completa.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: US1 = Referentes Globales, US2 = Referentes Regionales, US3 = Startups/Disruptores

---

## Phase 1: Verificación de entorno

**Purpose**: Confirmar estado de la rama antes de tocar código.

- [X] T001 Verificar que `uv run pytest` corre verde en rama base (ningún test roto previo)
- [X] T002 [P] Verificar que `embedding_repo.py` expone `search_similar` sin `fuente_tipo_filter` (baseline para regresión)
- [X] T003 [P] Verificar que `shared/types.py` no define aún `Cap21Globales` (evitar conflicto)

---

## Phase 2: Infraestructura base (prerequisito de todas las US)

**Purpose**: Parámetro `fuente_tipo_filter` + cuatro dataclasses + registro en checkpoint_serde. CRÍTICO: nada de US puede empezar antes de completar esta fase.

**⚠️ CRÍTICO**: Ninguna US puede empezar hasta completar esta fase.

- [X] T004 Añadir parámetro `fuente_tipo_filter: str | None = None` a `EmbeddingRepository.search_similar` en `src/ic/data/repositories/embedding_repo.py` (cláusula `AND e.fuente_tipo = :fuente_tipo` condicional al WHERE existente; default `None` no afecta callers actuales)
- [X] T005 Añadir parámetro `fuente_tipo_filter: str | None = None` a `PGVectorStore.search` en `src/ic/infrastructure/retrieval/pgvector_store.py` y pasarlo a `search_similar` (cambio de firma aditivo)
- [X] T006 [P] Añadir dataclasses `Cap21Globales`, `Cap21Regionales`, `Cap21Startups`, `Cap21Jugadores` a `src/ic/shared/types.py` (campos y tipos exactos según data-model.md; importar `ChunkResult` ya existente)
- [X] T007 Registrar las cuatro clases nuevas en `_REGISTRY` de `src/ic/shared/checkpoint_serde.py` con claves `cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups`, `cap2_21` (seguir convención de entradas existentes)
- [X] T008 Añadir test de regresión `test_fuente_tipo_filter_none_preserva_comportamiento` y `test_fuente_tipo_filter_emis_aplica_clausula` en `tests/test_embedding_repo.py` (usar `_FakeSession` existente; verificar que el WHERE incluye/excluye la cláusula según el valor del parámetro)

**Checkpoint**: `uv run pytest tests/test_embedding_repo.py -v` → 100% verde antes de continuar.

---

## Phase 3: US1 — Referentes Globales (P1) 🎯 MVP

**Goal**: Sub-módulo que propone candidatos globales vía LLM, busca cada uno en web y genera perfiles en prosa (máx 5 empresas).

**Independent Test**: `uv run pytest tests/test_generate_21_globales.py -v` → 5 tests verdes.

### Tests para US1

> **Escribir ANTES de la implementación — deben FALLAR primero**

- [X] T009 [P] [US1] Crear `tests/test_generate_21_globales.py` con los 5 casos del quickstart.md: `test_candidatos_propuestos_y_filtrados`, `test_candidatos_sin_web_se_omiten`, `test_excluye_empresa_focal`, `test_ausencia_si_cero_candidatos`, `test_max_5_empresas_respetado` (usar stubs para `chain_candidatos`, `chain_perfil`, `store`, `web_connector`; no DB ni red real)

### Implementación de US1

- [X] T010 [P] [US1] Crear chain `src/ic/domain/chains/chain_cap2_21_globales.py` (~80 líneas): prompt de perfil global en inglés→español centrado en modelo de negocio, mercado y diferenciales; entrada: `sector_gics`, `candidatos`, `chunks`; salida: prosa bajo encabezado `### Referentes Globales` (no hardcodear modelo — usar `llm` inyectado)
- [X] T011 [US1] Crear use case `src/ic/domain/use_cases/generate_21_globales.py` (~180 líneas) según contrato UC-1: constructor recibe `chain_candidatos` (reusar `chain_02c_pares_globales`), `chain_perfil` (nueva del T010), `store`, `web_connector`, `max_empresas=5`; método `execute(...)` → `Cap21Globales`; incluye normalización de nombres, filtrado de empresa focal, recorte a `max_empresas`, búsqueda web por candidato, retrieval post-ingesta y regla de ausencia si `chunks < MIN_CHUNKS` (3)
- [X] T012 [US1] Verificar que T009 pasa: `uv run pytest tests/test_generate_21_globales.py -v` → ajustar implementación hasta 100% verde

**Checkpoint**: `uv run pytest tests/test_generate_21_globales.py -v` → 5/5 PASSED.

---

## Phase 4: US2 — Referentes Regionales (P2)

**Goal**: Sub-módulo que usa EMIS como fuente primaria (filtro `fuente_tipo_filter="emis"`) y genera perfiles regionales en prosa (máx 3 empresas); ausencia inmediata si no hay chunks EMIS.

**Independent Test**: `uv run pytest tests/test_generate_21_regionales.py -v` → 4 tests verdes.

### Tests para US2

- [X] T013 [P] [US2] Crear `tests/test_generate_21_regionales.py` con los 4 casos del quickstart.md: `test_retrieval_emis_exclusivo`, `test_ausencia_si_sin_chunks_emis`, `test_complemento_web_no_reemplaza_emis`, `test_max_3_empresas_regionales` (stub de `store.search` retorna lista vacía o lista de `ChunkResult` con `fuente_tipo="emis"` según el test; no DB real)

### Implementación de US2

- [X] T014 [P] [US2] Crear chain `src/ic/domain/chains/chain_cap2_21_regionales.py` (~80 líneas): prompt especializado en perfiles regionales LatAm/Colombia desde chunks EMIS; encabezado `### Referentes Regionales LatAm/Colombia`; priorizar contexto EMIS sobre web complementario (no hardcodear modelo)
- [X] T015 [US2] Crear use case `src/ic/domain/use_cases/generate_21_regionales.py` (~150 líneas) según contrato UC-2: llama `store.search` con `fuente_tipo_filter="emis"` (T004/T005 ya disponibles); si `len(chunks_emis) < 3` → retorna `Cap21Regionales` con párrafo de ausencia y `retrieval_suficiente=False`; extrae nombres EMIS, lanza complemento web solo si hay base EMIS; retorna `Cap21Regionales` completo
- [X] T016 [US2] Verificar que T013 pasa: `uv run pytest tests/test_generate_21_regionales.py -v` → ajustar hasta 100% verde

**Checkpoint**: `uv run pytest tests/test_generate_21_regionales.py -v` → 4/4 PASSED.

---

## Phase 5: US3 — Startups y Disruptores (P3)

**Goal**: Sub-módulo que recupera startups locales de StartIA (máx 3) vía `list_locales_by_sector(segmento="startup")` y complementa con hasta 2 internacionales de web.

**Independent Test**: `uv run pytest tests/test_generate_21_startups.py -v` → 5 tests verdes.

### Tests para US3

- [X] T017 [P] [US3] Crear `tests/test_generate_21_startups.py` con los 5 casos del quickstart.md: `test_startups_locales_desde_kb`, `test_internacionales_desde_web`, `test_ausencia_si_sin_locales_ni_web`, `test_deduplicacion_local_vs_internacional`, `test_locales_aparecen_primero_en_prosa` (stub de `entidad_repo.list_locales_by_sector` retorna lista de `LocalRow`; stub de `web_connector.search`; no DB real)

### Implementación de US3

- [X] T018 [P] [US3] Crear chain `src/ic/domain/chains/chain_cap2_21_startups.py` (~80 líneas): prompt centrado en modelo de negocio disruptivo; encabezado `### Startups y Disruptores del sector`; los locales aparecen primero; contexto incluye atributos StartIA + chunks web de internacionales (no hardcodear modelo)
- [X] T019 [US3] Crear use case `src/ic/domain/use_cases/generate_21_startups.py` (~160 líneas) según contrato UC-3: constructor recibe `chain_perfil`, `store`, `web_connector`, `entidad_repo`, `max_locales=3`, `max_internacionales=2`; `execute(...)` llama `entidad_repo.list_locales_by_sector(sectores_ancla, segmento="startup", limit=max_locales, exclude_nombre=nombre_empresa)`; ordena por `ventas_2025_cop` (JOIN con `entidad_atributos`) como criterio primario, `n_menciones` como desempate cuando `ventas_2025_cop` no disponible (clarificación Q2); si `len(locales) < max_locales` busca internacionales vía web; deduplica locales vs internacionales; retorna `Cap21Startups`
- [X] T020 [US3] Verificar que T017 pasa: `uv run pytest tests/test_generate_21_startups.py -v` → ajustar hasta 100% verde

**Checkpoint**: `uv run pytest tests/test_generate_21_startups.py -v` → 5/5 PASSED.

---

## Phase 6: Orquestador + integración con generate_benchmarking

**Goal**: `generate_21_jugadores.py` coordina los tres sub-módulos, deduplica cross-tier y ensambla el texto completo de 2.1; integración en `generate_benchmarking.py` reemplaza la generación inline.

**Independent Test**: `uv run pytest tests/test_generate_21_jugadores.py -v` → 4 tests verdes + regresión completa.

### Tests para el orquestador

- [X] T021 [P] Crear `tests/test_generate_21_jugadores.py` con los 4 casos del quickstart.md Escenario 4: `test_ensambla_tres_subsecciones_en_orden`, `test_deduplicacion_cross_tier`, `test_resume_desde_checkpoint_parcial`, `test_ausencia_total_si_todos_fallan` (inyectar stubs de `gen_globales`, `gen_regionales`, `gen_startups` que retornen `Cap21Globales`/`Cap21Regionales`/`Cap21Startups` hardcodeados o ausentes; verificar texto ensamblado)

### Implementación del orquestador

- [X] T022 Crear orquestador `src/ic/domain/use_cases/generate_21_jugadores.py` (~120 líneas) según contrato UC-4: constructor recibe `gen_globales`, `gen_regionales`, `gen_startups`; `execute(...)` restaura desde checkpoint los sub-módulos ya computados, ejecuta los restantes (pueden correr en paralelo vía `ThreadPoolExecutor`), aplica deduplicación cross-tier por `_clave_exclusion` (Global > Regional > Startup), ensambla el texto con `## 2.1. Jugadores Clave\n\n` + tres bloques `###`; **caso especial**: si los tres sub-módulos devuelven `retrieval_suficiente=False`, el texto ensamblado es un único párrafo de ausencia consolidado bajo `## 2.1.` (sin los tres `###`) indicando qué fuentes faltan (clarificación Q3); persiste checkpoints y retorna `Cap21Jugadores`
- [X] T023 Integrar orquestador en `src/ic/domain/use_cases/generate_benchmarking.py`: reemplazar la sección de generación inline de 2.1 (Jugadores Clave) por una llamada al nuevo `Generate21Jugadores`; mantener invariante de la interfaz pública de `GenerateBenchmarking` (sin cambios en firma de `execute`)
- [X] T024 Verificar que T021 pasa y que los tests existentes de `generate_benchmarking` no rompen: `uv run pytest tests/test_generate_21_jugadores.py tests/test_generate_benchmarking.py -v` → 0 fallos

**Checkpoint**: `uv run pytest` (suite completa) → 0 fallos antes de pasar a Phase 7.

---

## Phase 7: Polish y validación

**Purpose**: Lint, formato, validación de escenarios del quickstart.md y commit final.

- [X] T025 [P] Correr `ruff check src/ic/domain/use_cases/generate_21_*.py src/ic/domain/chains/chain_cap2_21_*.py` → corregir cualquier warning
- [X] T026 [P] Correr `black --check src/ic/domain/use_cases/generate_21_*.py src/ic/domain/chains/chain_cap2_21_*.py` → formatear si hay diff
- [X] T027 Verificar que ningún archivo nuevo supera 300 líneas (Constitution I): `wc -l src/ic/domain/use_cases/generate_21_*.py src/ic/domain/chains/chain_cap2_21_*.py src/ic/domain/use_cases/generate_21_jugadores.py`
- [X] T028 Ejecutar suite completa final: `uv run pytest -v` → 0 fallos, cobertura domain/ ≥ 80%
- [X] T029 Validar criterios de aceptación de quickstart.md manualmente o con script: SC-003 (0% fabricación), SC-006 (≥70% chunks regionales desde EMIS), SC-007 (≥1 startup local de StartIA)

---

## Phase 8: Convergence

- [X] T030 Añadir persistencia de checkpoints en `generate_21_jugadores.execute`: llamar `checkpoint_hooks.save_cap(engine, run_key, "cap2_21_globales", globales)` después de ejecutar el sub-módulo Globales (antes de lanzar Regionales/Startups) y `save_cap` equivalentes para `cap2_21_regionales` y `cap2_21_startups`; recibir `engine` y `run_key` como parámetros opcionales; si son `None`, omitir persistencia en modo sin-BD per FR-012, SC-004, SC-005 (missing)
- [X] T031 Añadir campo `ventas_2025_cop: float | None = None` a `LocalRow` en `src/ic/domain/kb/relevance.py`; extender la query de `_list_locales` con LEFT JOIN a `entidad_atributos` (clave `"ventas_2025_cop"`) y ordenar `sorted(...)` por `-(r.ventas_2025_cop or 0)` como criterio primario, `-(r.n_menciones or 0)` como desempate; añadir test de regresión que verifica el ordering per FR-008 (partial)
- [X] T032 Crear `tests/test_generate_benchmarking_jugadores.py` con al menos 2 tests unitarios (sin DB): `test_jugadores_use_case_delegado_cuando_inyectado` verifica que `GenerateBenchmarking.execute` llama `jugadores_use_case.execute` y usa su texto cuando `retrieval_suficiente=True`; `test_fallback_a_kb_assembler_si_jugadores_falla` verifica que ante excepción de `jugadores_use_case` se continúa por el path `seccion21_enabled` per Constitution V / T024 (partial)
- [X] T033 Corregir condición de búsqueda de internacionales en `generate_21_startups.py`: cambiar `if len(filas_locales) < self._max_locales:` por `if True:` (o eliminarlo) para que el web search de internacionales ocurra siempre, no solo cuando hay espacio para más locales; actualizar `test_generate_21_startups.py` con caso `test_internacionales_buscados_cuando_locales_llenos` (3 locales y también se retornan ≤2 internacionales) per FR-009, US3/AC2 (partial)
- [X] T034 Filtrar empresa focal en `_extraer_nombres_emis` de `generate_21_regionales.py`: después de extraer los nombres de metadatos EMIS, aplicar `[n for n in nombres if _clave_exclusion(n) != _clave_exclusion(nombre_empresa)]`; importar `_clave_exclusion` desde `ic.data.repositories.entidad_repo`; añadir test `test_excluye_empresa_focal_de_regionales` per FR-016 (partial)
- [X] T035 Desmarcar T029 y dejar constancia explícita de que SC-003/SC-006/SC-007 requieren validación en entorno con BD real y LLM activo (EMIS indexado); añadir un `pytest.mark.slow` o `pytest.mark.integration` al quickstart.md indicando el comando exacto para ejecutarlos cuando el entorno esté disponible per T029/SC-003/SC-006/SC-007 (partial)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (verificación): Sin dependencias — comenzar de inmediato
- **Phase 2** (infraestructura): Depende de Phase 1 — **BLOQUEA todas las US**
- **Phase 3** (US1): Depende de Phase 2 — independiente de US2/US3
- **Phase 4** (US2): Depende de Phase 2 — independiente de US1/US3
- **Phase 5** (US3): Depende de Phase 2 — independiente de US1/US2
- **Phase 6** (orquestador): Depende de que Phase 3, 4 y 5 estén completas
- **Phase 7** (polish): Depende de Phase 6

### User Story Dependencies

- **US1 (P1)**: Puede iniciar en cuanto Phase 2 esté completa. Sin dependencias en US2/US3.
- **US2 (P2)**: Puede iniciar en cuanto Phase 2 esté completa. Usa `fuente_tipo_filter` de T004/T005.
- **US3 (P3)**: Puede iniciar en cuanto Phase 2 esté completa. Usa `Cap21Startups` de T006.
- **Orquestador (Phase 6)**: Requiere los tres use cases (T011, T015, T019).

### Parallel Opportunities

```bash
# Phase 2 — en paralelo una vez verificado que baseline es verde:
T004  # embedding_repo.py
T005  # pgvector_store.py
T006  # shared/types.py
T007  # checkpoint_serde.py
T008  # test_embedding_repo.py

# Phase 3+4+5 — en paralelo tras completar Phase 2:
# Desarrollador A: Phase 3 (US1 — T009 → T010 → T011 → T012)
# Desarrollador B: Phase 4 (US2 — T013 → T014 → T015 → T016)
# Desarrollador C: Phase 5 (US3 — T017 → T018 → T019 → T020)

# Dentro de cada US — en paralelo:
# Tests y chain pueden escribirse juntos antes del use case
```

---

## Implementation Strategy

### MVP First (US1 únicamente)

1. Completar Phase 1 (verificación)
2. Completar Phase 2 (infraestructura) — **crítico**
3. Completar Phase 3 (US1 Globales)
4. **STOP y VALIDAR**: `uv run pytest tests/test_generate_21_globales.py -v` → 5/5
5. Demo del sub-módulo aislado antes de continuar

### Incremental Delivery

1. Phase 1 + Phase 2 → infraestructura lista
2. Phase 3 → US1 Globales testeable → demo
3. Phase 4 → US2 Regionales testeable → demo
4. Phase 5 → US3 Startups testeable → demo
5. Phase 6 → orquestador integrado → regresión completa
6. Phase 7 → polish + commit

### Notas

- Tests marcados `[P]` dentro de una US pueden escribirse en paralelo con la chain del mismo US
- Si `generate_benchmarking.py` es demasiado rígido para T023, abrir tarea nueva antes de improvisar
- No modificar `generate_n1.py` en este feature (ver plan.md: integración diferida)
- Usar `_FakeSession` de `tests/conftest.py` existente para todos los tests unitarios
