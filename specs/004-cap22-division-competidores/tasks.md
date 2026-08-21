# Tasks: Cap 2.2 — División de Competidores (Grupos Estratégicos)

**Input**: Design documents from `specs/004-cap22-division-competidores/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/markdown-output.md ✅

**Tests**: Incluidos — SC-006 requiere ≥80% cobertura en `domain/`; constitución exige tests en el mismo PR.

**Organization**: Tareas agrupadas por user story para implementación y prueba independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias de tareas incompletas)
- **[Story]**: User story a la que pertenece la tarea
- Rutas de archivos exactas en cada descripción

---

## Phase 1: Setup

**Purpose**: Verificar la estructura existente y confirmar que no se necesitan dependencias nuevas.

- [x] T001 Confirm no new dependencies needed: verify `langchain-core`, `sqlalchemy`, `pytest` are already in `pyproject.toml` and that `CheckpointRepository`, `Cap21Jugadores`, and `DescripcionEmpresa` are importable from their existing modules

**Checkpoint**: Sin dependencias nuevas — Cap 2.2 reutiliza el stack existente al 100%.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tipos de dominio y assembler puro que TODAS las user stories necesitan antes de comenzar.

**⚠️ CRITICAL**: Ninguna user story puede implementarse hasta que esta fase esté completa.

- [x] T002 Add `CuadranteKey` enum to `src/ic/shared/types.py` with four values: `masivo_tradicional`, `masivo_innovador`, `nicho_tradicional`, `nicho_innovador` (use `str, Enum` mixin for JSON serialization)
- [x] T003 [P] Add `ClasificacionCompetidor` dataclass to `src/ic/shared/types.py` with fields: `nombre: str`, `cuadrante: CuadranteKey`, `dato_no_disponible: bool = False`
- [x] T004 [P] Add `Cap22Division` dataclass to `src/ic/shared/types.py` with fields: `texto: str`, `clasificaciones: list[ClasificacionCompetidor]`, `n_empresas_procesadas: int`, `retrieval_suficiente: bool`, `warnings_nombres_ajenos: list[str] = field(default_factory=list)`
- [x] T005 Add `cap_22_division: "Cap22Division | None" = None` field to `InformePiloto` dataclass in `src/ic/shared/types.py` (insert after `cap_benchmarking` field; backward-compatible default)
- [x] T006 Create `src/ic/domain/kb/seccion22_assembler.py` with pure function `assemble_seccion_22(cap22_llm_output: dict, closed_list: list[str]) -> str` that: (a) validates all closed_list names appear in cuadrantes, (b) raises `CoverageError` if any name is missing, (c) renders the 2×2 markdown table per `contracts/markdown-output.md`, (d) puts `(ninguno)` in empty quadrants, (e) appends the `### Síntesis de Presión Competitiva` section with two `####` sub-headings
- [x] T007 [P] Create `docs/prompts/prompt-02b-division-competidores.md` documenting the system prompt structure for Cap 2.2: role, task description, closed-list injection pattern, JSON output schema `{cuadrantes, intro, sintesis_incumbente, sintesis_entrante}`, and grounding rules

**Checkpoint**: Tipos compilables + assembler puro testeable sin LLM — user stories pueden comenzar en paralelo.

---

## Phase 3: US1 + US2 — Clasificación Exhaustiva + Lista Cerrada (Priority: P1) 🎯 MVP

**Goal**: Generar la sección 2.2 completa clasificando exhaustivamente los competidores de 2.1 en la matriz 2×2, garantizando que ningún nombre ajeno entre en el output.

**Independent Test**: `pytest tests/test_generate_22_division.py -k "exhaustiva or cerrada or cuadrante_vacio"` — 3 escenarios con fixtures de Cap 2.1 y stubs del LLM; sin BD real.

### Tests para US1 + US2

> **Escribir primero — deben FALLAR antes de la implementación**

- [x] T008 [P] [US1] In `tests/test_generate_22_division.py`, write `test_clasificacion_exhaustiva`: fixture `Cap21Jugadores` with 5 companies (2 globales, 1 regional, 2 startups); fake LLM stub returns valid JSON with all 5 classified; assert `len(cap22.clasificaciones) == 5`, `cap22.retrieval_suficiente == True`, and sum of companies across all quadrants equals 5
- [x] T009 [P] [US2] In `tests/test_generate_22_division.py`, write `test_lista_cerrada_nombre_ajeno`: same 5-company fixture; fake LLM stub adds `"EmpresaZ"` (not in fixture) to a quadrant; assert `"EmpresaZ"` not in `cap22.texto` and `"EmpresaZ" in cap22.warnings_nombres_ajenos` and `len(cap22.clasificaciones) == 5`
- [x] T010 [P] [US1] In `tests/test_generate_22_division.py`, write `test_cuadrante_vacio_muestra_ninguno`: fake LLM assigns all 5 companies to `masivo_tradicional`; assert `cap22.texto` contains exactly 3 occurrences of `(ninguno)` and no quadrant row is missing from the table

### Implementation para US1 + US2

- [x] T011 Create `src/ic/domain/chains/chain_cap2_22_division.py` with function `build_chain_cap2_22_division(llm: object) -> Runnable` using LCEL (`ChatPromptTemplate | llm | StrOutputParser`); system prompt injects `{closed_list_str}` (enumerated company names), `{fichas_context}` (ficha attributes from Cap 2.1), `{empresa_sector}` (from Cap 1), and optional `{feedback}`; human prompt requests JSON output with schema `{cuadrantes, intro, sintesis_incumbente, sintesis_entrante}`; model name NEVER hardcoded
- [x] T012 Create `src/ic/domain/use_cases/generate_22_division.py` with class `Generate22Division` that receives `llm`, `checkpoint_repo: CheckpointRepository` in `__init__`; implement helper `_build_closed_list(cap21: Cap21Jugadores) -> list[str]` that concatenates `globales.candidatos + regionales.empresas_emis + startups.locales + startups.internacionales` (handling None sub-objects)
- [x] T013 [US2] In `src/ic/domain/use_cases/generate_22_division.py`, implement `_validate_closed_list(cuadrantes: dict[str, list[str]], closed_list: list[str]) -> tuple[dict[str, list[str]], list[str]]` that returns (filtered_cuadrantes_with_intruders_removed, warnings_list); an "intruder" is any name in the LLM output not present in closed_list (case-insensitive comparison)
- [x] T014 [US1] In `src/ic/domain/use_cases/generate_22_division.py`, implement `_parse_llm_json(raw: str) -> dict | None` with retry-safe parsing: extract JSON from raw string (strip markdown fences if present), return parsed dict or `None` if malformed; implement main `__call__(self, run_key, cap21, empresa, feedback=None) -> Cap22Division` that: (a) calls chain, (b) calls `_parse_llm_json` with up to 2 retries, (c) calls `_validate_closed_list`, (d) builds `fichas_context` from Cap 2.1 attribute fields for use in prompt
- [x] T015 [US1] In `src/ic/domain/use_cases/generate_22_division.py`, inside `__call__`, after validation: call `assemble_seccion_22(validated_output, closed_list)` from `seccion22_assembler`; build `list[ClasificacionCompetidor]` from the validated cuadrantes dict; call `self._checkpoint_repo.save_capitulo(run_key, "cap_2_2", dataclasses.asdict(cap22_result))`; return `Cap22Division` instance

**Checkpoint**: `pytest tests/test_generate_22_division.py -k "exhaustiva or cerrada or cuadrante_vacio"` — los 3 tests deben pasar. US1 + US2 completamente funcionales con fixtures.

---

## Phase 4: US3 — Regeneración Idempotente con Feedback (Priority: P2)

**Goal**: El módulo acepta retroalimentación textual y regenera Cap 2.2 sin alterar los checkpoints de Cap 1 ni Cap 2.1 en BD.

**Independent Test**: `pytest tests/test_generate_22_division.py -k "regeneracion"` — verifica idempotencia de checkpoints usando `FakeCheckpointRepo`.

### Test para US3

- [x] T016 [P] [US3] In `tests/test_generate_22_division.py`, write `test_regeneracion_no_altera_cap1_ni_cap21`: use a `FakeCheckpointRepo` that tracks calls; pre-populate with `cap_1` and `cap_2_1` payloads; call `generate_22.__call__(run_key, cap21, empresa)` then call again with `feedback="más énfasis en entrantes"`; assert that `FakeCheckpointRepo.saved["cap_1"]` and `FakeCheckpointRepo.saved["cap_2_1"]` are unchanged and only `cap_2_2` was upserted

### Implementation para US3

- [x] T017 [US3] In `src/ic/domain/use_cases/generate_22_division.py`, update `__call__` signature to accept `feedback: str | None = None` and pass it to the chain invocation as `{feedback}` template variable; when `feedback is None`, template variable resolves to empty string (no change to prompt structure, just enables the regeneration path)

**Checkpoint**: `pytest tests/test_generate_22_division.py -k "regeneracion"` — test pasa. Los checkpoints de Cap 1 y 2.1 son inmutables durante la ejecución de Cap 2.2.

---

## Phase 5: US4 — Ausencia de Datos en Cap 2.1 (Priority: P3)

**Goal**: Si Cap 2.1 está vacío o con retrieval insuficiente, el módulo devuelve un párrafo de ausencia estándar sin invocar al LLM.

**Independent Test**: `pytest tests/test_generate_22_division.py -k "vacio or malformado"` — 2 escenarios con stubs; LLM invocado 0 veces en el caso vacío, exactamente 2 veces en el caso malformado.

### Tests para US4

- [x] T018 [P] [US4] In `tests/test_generate_22_division.py`, write `test_cap21_vacio_devuelve_ausencia`: build `Cap21Jugadores` with `retrieval_suficiente=False` and empty sub-objects; assert `cap22.retrieval_suficiente == False`, `"## 2.2." in cap22.texto`, absence of the 2×2 table, and fake LLM stub call count is 0
- [x] T019 [P] [US4] In `tests/test_generate_22_division.py`, write `test_json_malformado_devuelve_ausencia`: fake LLM stub always returns `"no es json válido"`; assert fake LLM was called exactly 2 times (retry policy), `cap22.retrieval_suficiente == False`, and `"## 2.2." in cap22.texto`

### Implementation para US4

- [x] T020 [US4] In `src/ic/domain/use_cases/generate_22_division.py`, add guard at the top of `__call__`: if `cap21.retrieval_suficiente is False` or `_build_closed_list(cap21)` returns empty list, immediately return `Cap22Division(texto=ABSENT_PARAGRAPH, clasificaciones=[], n_empresas_procesadas=0, retrieval_suficiente=False)` without invoking the LLM; define `ABSENT_PARAGRAPH` as module-level constant with the standard absence text per `contracts/markdown-output.md`
- [x] T021 [US4] In `src/ic/domain/use_cases/generate_22_division.py`, implement the retry-on-JSON-failure path: if `_parse_llm_json` returns `None` after 2 attempts, log a warning and return `Cap22Division` with `retrieval_suficiente=False` and the `ABSENT_PARAGRAPH`; the retry counter MUST be encapsulated in `__call__` (not global state)

**Checkpoint**: `pytest tests/test_generate_22_division.py` — todos los 6+ tests pasan.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integración en el DAG, cobertura final, y validación E2E.

- [x] T022 Wire `Generate22Division` into `src/ic/domain/use_cases/generate_n1.py`: import the class; instantiate with the same `llm` and `checkpoint_repo` used by other N1 use cases; submit it to the existing `ThreadPoolExecutor` alongside `Generate21Jugadores`, ensuring the future result is stored and returned as part of the N1 batch output; attach the result to `InformePiloto.cap_22_division`
- [x] T023 [P] Verify test coverage: run `pytest tests/test_generate_22_division.py --cov=src/ic/domain/use_cases/generate_22_division --cov=src/ic/domain/kb/seccion22_assembler --cov-report=term-missing` and confirm ≥80% coverage on both modules; if below threshold, add targeted tests for uncovered branches
- [x] T024 [P] Run full quickstart.md validation: execute all 6 pytest scenarios from `specs/004-cap22-division-competidores/quickstart.md` and confirm all pass; document any failures as issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede comenzar inmediatamente.
- **Foundational (Phase 2)**: Depende de Phase 1 — **bloquea todas las user stories**.
- **US1+US2 (Phase 3)**: Depende de Phase 2. Tests (T008-T010) y chain (T011) son paralelos entre sí.
- **US3 (Phase 4)**: Depende de Phase 3 (necesita `__call__` implementado para extender con `feedback`).
- **US4 (Phase 5)**: Puede iniciarse en paralelo con US3 (Phase 4) si la firma de `__call__` de Phase 3 está completa — los guards de ausencia son independientes de la lógica de feedback.
- **Polish (Phase 6)**: Depende de que Phases 3-5 estén completos.

### User Story Dependencies

- **US1+US2 (P1)**: Sin dependencias entre stories — clasificación y grounding son la misma implementación.
- **US3 (P2)**: Puede iniciar cuando `__call__` existe (T014 completo); extiende el parámetro existente.
- **US4 (P3)**: Puede iniciar cuando la estructura de `__call__` existe (T012 completo); añade guards en los extremos del flujo.

### Within Each Phase

- T002 antes de T003 y T004 (enum requerido por los dataclasses).
- T003 y T004 en paralelo [P].
- T005 después de T002+T003+T004 (usa los tres tipos).
- T006 puede hacerse en paralelo con T005 (assembler es puro, no depende de `InformePiloto`).
- T011 y T008-T010 en paralelo dentro de Phase 3.
- T012 después de T011 (use_case importa la chain).
- T013 y T014 pueden hacerse en paralelo (distintas funciones helper en el mismo archivo).
- T015 después de T013+T014.

### Parallel Opportunities

- T003, T004, T007 — todos en paralelo en Phase 2.
- T008, T009, T010, T011 — todos en paralelo en Phase 3.
- T013, T014 — en paralelo dentro de Phase 3.
- T016 (test US3) y T018, T019 (tests US4) — en paralelo si Phase 3 está completa.
- T023, T024 — en paralelo en Phase 6.

---

## Parallel Example: Phase 3 (US1 + US2)

```bash
# Lanzar en paralelo tras completar Phase 2:
Task T008: "test_clasificacion_exhaustiva en tests/test_generate_22_division.py"
Task T009: "test_lista_cerrada_nombre_ajeno en tests/test_generate_22_division.py"
Task T010: "test_cuadrante_vacio_muestra_ninguno en tests/test_generate_22_division.py"
Task T011: "chain_cap2_22_division.py en src/ic/domain/chains/"

# Una vez T011 completo → T012 → T013+T014 en paralelo → T015
```

---

## Implementation Strategy

### MVP First (US1 + US2 — Phases 1-3)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T007)
3. Complete Phase 3: US1+US2 (T008-T015)
4. **STOP y VALIDA**: `pytest tests/test_generate_22_division.py -k "exhaustiva or cerrada or cuadrante_vacio"`
5. El módulo genera Cap 2.2 completo con grounding — valor principal entregado.

### Incremental Delivery

1. Phase 1+2 → Tipos y assembler listos
2. Phase 3 → MVP: clasificación + grounding funcionando
3. Phase 4 → Regeneración con feedback
4. Phase 5 → Protección ante datos ausentes
5. Phase 6 → Integración en DAG + cobertura confirmada

---

## Notes

- Tests en el mismo PR que el código — sin excepciones (constitución V).
- El stub del LLM en tests usa el patrón `_FakeLLM` o `MagicMock` existente en el proyecto — revisar `tests/test_generate_21_jugadores.py` para el patrón exacto.
- `_parse_llm_json` debe manejar markdown fences (````json ... ````) que algunos modelos de OpenRouter añaden alrededor del JSON.
- El nombre de checkpoint `"cap_2_2"` es la clave canónica — no usar variantes (`cap22`, `2_2`, etc.).
- `check-hardcoded-models.sh` bloqueará el commit si algún nombre de modelo se escapa al código — revisar antes de commitear.

---

## Phase 7: Convergence

- [X] T025 CRITICAL: Fix `_cap21_holder` never-populated bug in `src/ic/domain/use_cases/generate_n1.py` — `_Cap21Capture` is defined but never applied; wrap `jugadores_use_case` with `_Cap21Capture` before `GenerateBenchmarking` is instantiated inside `_fn_cap2`, so `_cap21_holder[0]` is populated and `if _cap21_holder:` executes; alternatively, after `_fn_cap2` returns reconstruct `Cap21Jugadores` from sub-module checkpoints (`cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups`) already saved by `Generate21Jugadores` per FR-011 (partial)
- [X] T026 [P] Add `test_error_red_propagado` in `tests/test_generate_22_division.py`: build a `_FakeChain` whose `invoke()` raises `RuntimeError("red")`; assert the exception propagates through `Generate22Division.__call__()` unhandled (no `Cap22Division` returned, no silent swallow) per FR-012 (missing)
- [X] T027 In `src/ic/domain/use_cases/generate_22_division.py`, update `_build_clasificaciones()` to accept the full `parsed_validated` dict and detect the string "Dato no disponible en fuentes consultadas" in `sintesis_incumbente` or `sintesis_entrante` per company name; set `dato_no_disponible=True` on the corresponding `ClasificacionCompetidor`; add a test `test_dato_no_disponible_marcado` per FR-006 / US2-AC3 (partial)
- [X] T028 [P] In `src/ic/domain/use_cases/generate_22_division.py`, add guard: if `len(closed_list) == 1`, generate normally but append a warning string (`"Solo 1 competidor en Cap 2.1; la segmentación 2×2 puede no ser representativa"`) to `Cap22Division.warnings_nombres_ajenos`; add test `test_un_competidor_genera_con_warning` per US4/AC2 (missing)
- [X] T029 [P] Extract Cap 2.2 wiring from `src/ic/domain/use_cases/generate_n1.py` into a helper function or dedicated module to bring `generate_n1.py` below 300 lines per Constitution I (partial) — move `_fn_cap2_with_22`, `_cap21_holder`, and `_Cap21Capture` logic to `src/ic/domain/use_cases/generate_n1_cap22.py`; update import in `generate_n1.py`

---

## Phase 8: Convergence

- [X] T030 In `src/ic/domain/assembler.py`, insert `informe.cap_22_division.texto` into `bench_blocks` after the section 2.1 content and before section 2.3 (Mercado): use `_insert_before_subheading(bench_blocks, parse_markdown(cap_22_division.texto), prefix="2.2")` when `informe.cap_22_division` is not None, then insert cap_mercado before `"2.3"` prefix (update existing `prefix="2.4"` to `prefix="2.3"` to reflect the renumbering); guard with `getattr(informe, "cap_22_division", None)` per FR-005, FR-011 (missing)
- [X] T031 [P] In `src/ic/domain/use_cases/generate_22_division.py`, replace `dataclasses.asdict(cap22)` with `serialize_cap(cap22)` (import from `ic.domain.checkpoint_serde`) at line 261; also add `Cap22Division` and `ClasificacionCompetidor` to `_REGISTRY` in `src/ic/domain/checkpoint_serde.py` with the correct nested deserialization for `clasificaciones` (list of `ClasificacionCompetidor` dicts, each with a `cuadrante` CuadranteKey field that deserializes from string) per FR-010 (partial)
- [X] T032 [P] In `src/ic/domain/use_cases/generate_n1_cap22.py`, add `--resume` check at the top of `_fn_cap2_with_22`: before calling `_reconstruct_cap21` and `Generate22Division`, call `ctx.checkpoint.get("cap_2_2")` — if a payload exists and can be deserialized via `deserialize_cap`, assign the result to `ctx.cap22_division` and return `cap` immediately (skipping regeneration); depends on T031 being complete so that the format is round-trip-safe per FR-010, FR-011 (missing)
