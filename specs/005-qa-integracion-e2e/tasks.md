# Tasks: QA e Integración E2E + Deuda Estructural

**Input**: Design documents from `specs/005-qa-integracion-e2e/`

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

**Organization**: Tareas ordenadas por historia de usuario en secuencia de ejecución (P1 antes que P2, dentro de P1 por dependencias de código). Las tareas marcadas `[P]` pueden ejecutarse en paralelo dentro de su fase.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: puede correr en paralelo (archivos distintos, sin dependencias incompletas)
- **[Story]**: historia de usuario a la que pertenece (US1–US9)
- Paths relativos desde la raíz del repo

---

## Phase 1: Setup — Configuración pytest

**Purpose**: Configurar pytest para que los tests de integración no corran por defecto.

**⚠️ Prerrequisito de todas las fases**: debe completarse antes de añadir cualquier test nuevo.

- [X] T001 Añadir marker `integration` a `[tool.pytest.ini_options].markers` y `addopts = "-m 'not integration'"` en `pyproject.toml`

**Checkpoint**: `uv run pytest` pasa sin flags y no intenta correr tests de integración.

---

## Phase 2: Foundational — Tipo `CallRecord.costo_usd`

**Purpose**: Cambio de tipo base que bloquea la implementación de US6. Debe completarse antes de la Phase 3.

**⚠️ CRÍTICO**: Los tests de US6 dependen de poder assert sobre `None`; la suite existente debe seguir pasando.

- [X] T002 Cambiar `costo_usd: float` → `costo_usd: float | None` en la dataclass `CallRecord` en `src/ic/infrastructure/llm/gateway.py`
- [X] T003 Actualizar `CostTracker.total_cost()` para sumar solo records donde `costo_usd is not None`; añadir método `has_unknown_pricing() -> bool` que retorna `True` si algún `CallRecord` tiene `costo_usd=None`
- [X] T004 [P] Actualizar `tests/test_cost_tracker.py` — ajustar asserts que asumen `costo_usd: float` para aceptar `float | None`; verificar que la suite existente pasa sin cambios adicionales

**Checkpoint**: `uv run pytest tests/test_cost_tracker.py -q` verde.

---

## Phase 3: US6 — Pricing comprehensivo para todos los modelos (Priority: P1) [DT-040]

**Goal**: `CostTracker.add_call` registra costo correcto para cualquier modelo del proyecto — Gemini, OpenRouter de pago, y `:free` automático.

**Independent Test**: `uv run pytest tests/test_cost_tracker.py -q` — los tests nuevos de T007–T011 pasan; los tests de T004 siguen verdes.

- [X] T005 [US6] Implementar las 3 reglas de lookup en `CostTracker.add_call` en `src/ic/infrastructure/llm/gateway.py`: (1) match exacto en `_PRICING`; (2) sufijo `:free` → `(0.0, 0.0)`; (3) prefijo `"gemini-"` → precio de `gemini-2.5-flash-lite`; (4) desconocido → `None` + `logger.warning`
- [X] T006 [P] [US6] Añadir entradas a `_PRICING` en `src/ic/infrastructure/llm/gateway.py`: `"gemini-2.5-flash-lite": (0.075/1_000_000, 0.30/1_000_000)`, `"gemini-2.5-flash": (0.075/1_000_000, 0.30/1_000_000)`, `"gemini-2.5-pro": (1.25/1_000_000, 10.0/1_000_000)` — con comentario de fecha y fuente (Google AI Studio, Sep 2026)
- [X] T007 [P] [US6] Test en `tests/test_cost_tracker.py`: modelo `"nvidia/nemotron-3-super-120b-a12b:free"` sin entrada explícita → `costo_usd == 0.0` (regla sufijo `:free`)
- [X] T008 [P] [US6] Test en `tests/test_cost_tracker.py`: modelo `"gemini-2.5-flash-lite"` → `costo_usd > 0.0` (match exacto)
- [X] T009 [P] [US6] Test en `tests/test_cost_tracker.py`: modelo `"gemini-2.5-flash-preview-2026-01"` (sin match exacto) → `costo_usd > 0.0` usando precio de `gemini-2.5-flash-lite` (fallback prefijo)
- [X] T010 [P] [US6] Test en `tests/test_cost_tracker.py`: modelo `"google/gemma-3-27b-it"` → `costo_usd > 0.0` (entry explícita existente)
- [X] T011 [P] [US6] Test en `tests/test_cost_tracker.py`: modelo `"unknown-provider/some-model"` → `costo_usd is None` y se emitió `WARNING` (usar `caplog` de pytest)

**Checkpoint**: `uv run pytest tests/test_cost_tracker.py -v` — todos los tests verdes incluyendo T007–T011.

---

## Phase 4: US5 — SoC: presentation sin imports directos a data/ (Priority: P1) [DT-038]

**Goal**: `presentation/app.py` no importa nada de `data/` directamente; todas las llamadas pasan por `domain/use_cases/ui_query_services.py`.

**Independent Test**: `grep -rn "from ic.data" src/ic/presentation/` → 0 resultados.

- [X] T012 [P] [US5] Crear `src/ic/domain/use_cases/ui_query_services.py` con 3 funciones: `list_empresas_conocidas() -> list[tuple[str, str]]`, `list_documentos_indexados() -> list[dict]`, `list_informes_recientes(limit: int, offset: int, empresa_filter: str | None) -> list[dict]` — cada función abre y cierra su propia `SessionLocal`; devuelve tipos primitivos sin acoplamiento a ORM
- [X] T013 [US5] Reemplazar los 3 bloques `from ic.data.*` en `src/ic/presentation/app.py` (líneas 60–61, 132–133, 212–213) con un import único al nivel del módulo: `from ic.domain.use_cases.ui_query_services import list_empresas_conocidas, list_documentos_indexados, list_informes_recientes` y adaptar los call sites para usar los tipos devueltos
- [X] T014 [P] [US5] Crear `tests/test_ui_query_services.py` con tests unitarios usando `_FakeSession` del patrón del proyecto — verificar que cada función retorna el tipo correcto y cierra la sesión; un caso de error por función (excepción del repo → retorna lista vacía o relanza limpiamente)
- [X] T015 [P] [US5] Verificar SoC: ejecutar `grep -rn "from ic.data" src/ic/presentation/` desde la raíz y confirmar 0 resultados; ejecutar `uv run pytest tests/test_ui_query_services.py -q` verde

**Checkpoint**: grep vacío + tests de T014 verdes + `uv run pytest tests/ -m "not integration" -q` sin regresiones.

---

## Phase 5: US7 — gateway.py dividido en módulos <300L (Priority: P2) [DT-037]

**Goal**: `infrastructure/llm/gateway.py` dividido en 4 archivos; ninguno supera 300 líneas; la interfaz pública no cambia.

**Independent Test**: `wc -l src/ic/infrastructure/llm/gateway*.py` → todos <300; `uv run pytest tests/test_gateway_robustez.py tests/test_llm.py tests/test_cost_tracker.py -q` verde.

- [X] T016 [P] [US7] Crear `src/ic/infrastructure/llm/gateway_pricing.py` — mover `_PRICING`, `CallRecord`, `CostTracker` desde `gateway.py`; añadir `__all__` con los 3 exports
- [X] T017 [P] [US7] Crear `src/ic/infrastructure/llm/gateway_models.py` — mover `OllamaGatewayLLM` y `OpenRouterGatewayLLM` desde `gateway.py`; importar `CostTracker` desde `gateway_pricing`
- [X] T018 [P] [US7] Crear `src/ic/infrastructure/llm/gateway_errors.py` — mover `is_rate_limit_error`, `is_transient_network_error`, `is_empty_generation_error` y `ResilientGatewayLLM` desde `gateway.py`; importar `OllamaGatewayLLM` / `OpenRouterGatewayLLM` desde `gateway_models`
- [X] T019 [US7] Actualizar `src/ic/infrastructure/llm/gateway.py` — retener `build_llm`, `build_api_llm`, `build_resilient_api_llm`, `_provider_base_and_key` + añadir re-exports de `CostTracker`, `CallRecord`, `OllamaGatewayLLM`, `OpenRouterGatewayLLM`, `ResilientGatewayLLM` para compatibilidad de imports existentes; importar desde los 3 módulos nuevos
- [X] T020 [US7] Verificar refactor: `wc -l src/ic/infrastructure/llm/gateway*.py` → todos <300; `python -c "from ic.infrastructure.llm.gateway import build_llm, CostTracker, ResilientGatewayLLM"` sin error; `uv run pytest tests/test_gateway_robustez.py tests/test_llm.py tests/test_cost_tracker.py -q` verde

**Checkpoint**: 4 archivos, todos <300L, suite existente del gateway verde.

---

## Phase 6: US8 — generate_informe.py dividido en módulos <300L (Priority: P2) [DT-039]

**Goal**: `domain/use_cases/generate_informe.py` dividido en 4 archivos; API pública intacta.

**Independent Test**: `wc -l src/ic/domain/use_cases/generate_informe.py src/ic/domain/use_cases/_informe_*.py` → todos <300; `uv run pytest tests/test_generate_informe.py -q` verde.

- [X] T021 [P] [US8] Crear `src/ic/domain/use_cases/_informe_context.py` — mover `_PipelineContext`, `_setup_infra`, `_sweep_stale_web`, `_promote_cited_web` desde `generate_informe.py`; estas 4 unidades son cohesivas (setup + ciclo de vida del contexto)
- [X] T022 [P] [US8] Crear `src/ic/domain/use_cases/_informe_nodes_n0.py` — extraer la lógica del método `_run_n0` como función standalone `run_n0(ctx: _PipelineContext) -> None`; importar `_PipelineContext` desde `_informe_context`
- [X] T023 [P] [US8] Crear `src/ic/domain/use_cases/_informe_nodes_n2n3.py` — extraer la lógica de `_run_n2` y `_run_n3` como funciones standalone `run_n2(ctx)` y `run_n3(ctx) -> InformeResult`; importar lo necesario desde `_informe_context`
- [X] T024 [US8] Actualizar `src/ic/domain/use_cases/generate_informe.py` — convertir `GenerateInforme` en shell con métodos delegadores de 1 línea: `def _run_n0(self, ctx): run_n0(ctx)` etc.; `InformeParams` e `InformeResult` permanecen aquí; eliminar código ya movido
- [X] T025 [US8] Verificar refactor: `wc -l src/ic/domain/use_cases/generate_informe.py src/ic/domain/use_cases/_informe_*.py` → todos <300; `from ic.domain.use_cases.generate_informe import GenerateInforme, InformeParams, InformeResult` sin error; `uv run pytest tests/test_generate_informe.py -q` verde

**Checkpoint**: 4 archivos, todos <300L, suite del generate_informe verde.

---

## Phase 7: US9 — Cobertura domain/ ≥80% (Priority: P2)

**Goal**: `pytest --cov=ic.domain` reporta TOTAL ≥80%.

**Independent Test**: `uv run pytest --cov=ic.domain --cov-report=term-missing tests/ -m "not integration" -q` → línea TOTAL ≥80%.

- [X] T026 [US9] Medir línea base de cobertura: `uv run pytest --cov=ic.domain --cov-report=term-missing tests/ -m "not integration" -q`; anotar los 5 módulos con menor cobertura del reporte
- [X] T027 [P] [US9] Crear `tests/test_coverage_domain_batch1.py` — agregar tests unitarios para el módulo de dominio con menor cobertura identificado en T026 (happy path + al menos 1 caso de error); usar `_FakeSession` y mocks del patrón del proyecto (sin BD real)
- [X] T028 [P] [US9] Crear `tests/test_coverage_domain_batch2.py` — agregar tests unitarios para el 2° módulo con menor cobertura identificado en T026 (mismo criterio que T027)
- [X] T029 [US9] Verificar cobertura: `uv run pytest --cov=ic.domain --cov-report=term tests/ -m "not integration" -q` → TOTAL ≥80%; si no alcanza, agregar tests adicionales en un 3er archivo hasta superar el umbral

**Checkpoint**: TOTAL ≥80% en el reporte de cobertura; suite completa verde.

---

## Phase 8: US1 — Pipeline E2E completo (Priority: P1)

**Goal**: Tests de integración que corren el pipeline N0→N1→N2 completo contra BD y LLM reales y verifican checkpoints.

**Independent Test**: `uv run pytest tests/integration/test_pipeline_e2e.py -m integration -v` — los 4 tests (TC-001 a TC-004) pasan o se saltean limpiamente si BD/LLM no están disponibles.

- [X] T030 Crear `tests/integration/__init__.py`, `tests/integration/seed/__init__.py` (archivos vacíos para hacer los directorios paquetes Python)
- [X] T031 Crear `tests/integration/conftest.py` con: (a) función `check_bd_available()` que intenta conectar a PostgreSQL en localhost:5434 y retorna bool; (b) función `check_llm_available()` que intenta `GET http://127.0.0.1:11434/api/tags` y retorna bool; (c) fixture `integration_prereqs` con `scope="session"` que llama a ambas y hace `pytest.skip` con mensaje accionable si alguna falla; (d) registro del marker `integration` via `pytest_configure`
- [X] T032 Crear `tests/integration/seed/sector_fixture.py` con: función `seed_integration_fixture(db)` que inserta empresa de prueba + competidores bajo `run_key = "__test__alpina_ic:3020"`; función `teardown_integration_fixture(db)` que elimina todos los registros con `run_key LIKE '__test__%'`; fixture pytest `integration_seed` con `scope="session"` que llama a seed en setup y teardown en finalizer
- [X] T033 [P] [US1] Crear `tests/integration/test_pipeline_e2e.py` con 4 tests marcados `@pytest.mark.integration` que dependen de `integration_prereqs` e `integration_seed`: TC-001 `test_informe_piloto_contiene_todos_caps` (US1/AC1), TC-002 `test_checkpoints_persistidos_en_bd` (US1/AC2), TC-003 `test_cap22_en_posicion_correcta` (US1/AC3), TC-004 `test_segunda_corrida_sin_excepcion` (US1/AC4)

**Checkpoint**: `uv run pytest tests/integration/test_pipeline_e2e.py -m integration -v` con BD + LLM activos → 4 PASSED.

---

## Phase 9: US2 — Cache sectorial evita re-invocar LLM (Priority: P1)

**Goal**: Test de integración que verifica que la segunda corrida del mismo sector no llama al LLM para Cap 2.1.

**Independent Test**: `uv run pytest tests/integration/test_sector_cache.py -m integration -v` — los 3 tests (TC-005 a TC-007) pasan.

- [X] T034 [P] [US2] Crear `tests/integration/test_sector_cache.py` con 3 tests `@pytest.mark.integration`: TC-005 `test_segunda_empresa_mismo_sector_no_invoca_llm_cap21` instala spy sobre `OpenRouterGatewayLLM._generate` antes de la segunda corrida y verifica `call_count == 0` para Cap 2.1 (US2/AC1); TC-006 `test_textos_cap21_identicos_entre_empresas_mismo_sector` (US2/AC2); TC-007 `test_cache_invalido_regenera_si_retrieval_insuficiente` (US2/AC3) — usa checkpoints sembrados con `retrieval_suficiente=False`

**Checkpoint**: `uv run pytest tests/integration/test_sector_cache.py -m integration -v` → 3 PASSED.

---

## Phase 10: US3 — Sub-módulos Cap 2.1 concurrencia (Priority: P2)

**Goal**: Tests unitarios (sin BD real) que verifican que `Generate21Startups` puede correr en `ThreadPoolExecutor` sin errores de sesión.

**Independent Test**: `uv run pytest tests/integration/test_concurrencia.py -v` (sin `-m integration` — son tests unitarios que viven en el directorio de integración pero no requieren infra).

- [X] T035 [P] [US3] Crear `tests/integration/test_concurrencia.py` con 2 tests SIN marker `integration`: TC-008 `test_db_factory_sesiones_independientes` — instancia `Generate21Startups` con una fake `db_factory` que retorna un nuevo mock con ID único por llamada; ejecuta 3 instancias en `ThreadPoolExecutor(max_workers=3)`; verifica que se crearon exactamente 3 sesiones distintas (US3/AC3); TC-009 `test_10_ejecuciones_sin_error_de_sesion` — repite TC-008 10 veces en loop; verifica que ninguna lanzó `DetachedInstanceError`, `InvalidRequestError` ni `SQLAlchemyError` (US3/AC1, SC-004)

**Checkpoint**: `uv run pytest tests/integration/test_concurrencia.py -v` → 2 PASSED (sin necesidad de BD).

---

## Phase 11: US4 — Limpieza de artefactos huérfanos (Priority: P3)

**Goal**: Repositorio sin archivos vacíos, directorios sin documentar, ni metadatos Windows sin gitignore.

**Independent Test**: `git status` no muestra el archivo `1`; `ls documentos_sectoriales/FuentesExternas/README.md` existe; `grep "Zone.Identifier" .gitignore` devuelve resultado.

- [X] T036 [P] [US4] Eliminar archivo vacío de la raíz: `git rm 1` — el archivo `1` es un artefacto de debug de 0 bytes sin contenido útil
- [X] T037 [P] [US4] Añadir `*.Zone.Identifier` a `.gitignore` — estos archivos son metadatos de descarga de Windows (Edge/IE), no contienen datos; deben ignorarse globalmente
- [X] T038 [US4] Crear `documentos_sectoriales/FuentesExternas/README.md` documentando: origen de cada archivo CSV/xlsx (`DBCamaraComercio20250410.CSV` = Cámara de Comercio; `CatalogoVerticalesStartIAGICS.csv` = StartIA; `startia_clean.xlsx` = StartIA procesado), propósito (fuente de ingesta para `ingest_batch.py`, no indexados en pgvector directamente), estado (ingestado / pendiente), y proceso para añadir nuevos archivos

**Checkpoint**: `git status` sin archivo `1`; README existe; `.gitignore` cubre `*.Zone.Identifier`.

---

## Phase 12: Polish — Validación final

**Purpose**: Verificar que todos los cambios conviven sin regresiones; ejecutar el quickstart completo.

- [X] T039 Correr suite unitaria completa: `uv run pytest tests/ -m "not integration" -q` → verde sin regresiones
- [X] T040 [P] Correr ruff: `uv run ruff check src/ic/infrastructure/llm/ src/ic/domain/use_cases/ src/ic/presentation/app.py` → 0 errores
- [X] T041 [P] Validar SoC final: `grep -rn "from ic.data" src/ic/presentation/` → 0 resultados; `wc -l src/ic/infrastructure/llm/gateway*.py src/ic/domain/use_cases/generate_informe.py src/ic/domain/use_cases/_informe_*.py` → todos <300

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Sin dependencias — empezar aquí.
- **Phase 2 (Foundational)**: Depende de Phase 1 — bloquea Phase 3.
- **Phase 3 (US6)**: Depende de Phase 2 (tipo `float | None` en `CallRecord`).
- **Phase 4 (US5)**: Independiente de Phase 3 — puede correr en paralelo con Phase 3.
- **Phase 5 (US7)**: Depende de Phase 3 (el código de pricing ya es correcto antes de moverlo).
- **Phase 6 (US8)**: Independiente de Phases 3–5 — puede correr en paralelo.
- **Phase 7 (US9)**: Depende de Phases 5 y 6 (medir cobertura sobre el código ya refactorizado).
- **Phase 8 (US1)**: Independiente de Phases 3–7 (los tests de integración no dependen del refactor).
- **Phase 9 (US2)**: Depende de Phase 8 (reutiliza las fixtures de seed y conftest).
- **Phase 10 (US3)**: Independiente — puede correr en paralelo con Phase 8 o 9.
- **Phase 11 (US4)**: Independiente — puede correr en paralelo con cualquier fase.
- **Phase 12 (Polish)**: Depende de todas las fases anteriores.

### User Story Dependencies

- **US6 (DT-040)**: Requiere Phase 2 completa.
- **US5 (DT-038)**: Sin dependencias de otras US; puede correr desde Phase 1.
- **US7 (DT-037)**: Requiere US6 completa (el código de pricing debe estar correcto antes de moverlo).
- **US8 (DT-039)**: Sin dependencias de otras US.
- **US9 (cobertura)**: Requiere US7 y US8 completas (medir sobre código refactorizado).
- **US1 (E2E)**: Sin dependencias de US5–US9.
- **US2 (cache)**: Requiere conftest de US1 (T031, T032).
- **US3 (concurrencia)**: Sin dependencias.
- **US4 (limpieza)**: Sin dependencias.

---

## Parallel Opportunities

### Dentro de Phase 3 (US6) — tras T005 completado

```
T006 (añadir entradas _PRICING)
T007 (test :free sin entrada)
T008 (test gemini match exacto)
T009 (test gemini sufijo versión)
T010 (test gemma openrouter)
T011 (test desconocido → None)
```

### Phases 3 y 4 en paralelo (ambas P1)

```
Phase 3: US6 (DT-040) → T005→T006–T011
Phase 4: US5 (DT-038) → T012–T015
```

### Dentro de Phase 5 (US7) — tras T019 completado

```
T016 (gateway_pricing.py)
T017 (gateway_models.py)
T018 (gateway_errors.py)
```

### Dentro de Phase 6 (US8) — independientes entre sí

```
T021 (_informe_context.py)
T022 (_informe_nodes_n0.py)
T023 (_informe_nodes_n2n3.py)
```

### Phases 8, 10, 11 en paralelo

```
Phase 8: US1 (E2E tests)
Phase 10: US3 (concurrencia — no requiere BD)
Phase 11: US4 (limpieza repo)
```

---

## Implementation Strategy

### MVP inmediato (P1 primero)

1. Phase 1 (Setup) → Phase 2 (Foundational)
2. **US6 + US5 en paralelo** → saldar deuda P1 más crítica
3. Phase 8 + 9 → cobertura de integración E2E
4. **VALIDAR**: `uv run pytest tests/ -m "not integration" -q` + `uv run pytest -m integration -v`
5. Deuda P2 (US7, US8, US9) en sesión siguiente

### Incremento completo

1. Phases 1–4 → deuda P1 saldada
2. Phases 5–7 → deuda P2 saldada
3. Phases 8–11 → integración E2E + limpieza
4. Phase 12 → validación final

---

## Notes

- `[P]` = archivos distintos, sin dependencias incompletas — pueden correr en paralelo
- El `[Story]` conecta cada tarea con la historia de usuario para trazabilidad
- Los tests de integración (US1, US2) requieren `docker compose up -d` y Ollama en host
- Los tests de concurrencia (US3) son tests unitarios — no requieren BD ni `-m integration`
- Los refactors de DT-037 y DT-039 son comportamiento-neutro: si aparece un bug durante el refactor, documentarlo y corregirlo en commit separado (Chesterton's Fence)
- Verificar `ruff check` tras cada fase antes de marcar tareas como completas
