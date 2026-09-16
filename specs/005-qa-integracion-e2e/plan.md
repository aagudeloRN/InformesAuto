# Implementation Plan: QA e Integración E2E + Deuda Estructural

**Branch**: `spec-driven-experiment` | **Date**: 2026-09-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-qa-integracion-e2e/spec.md`

---

## Summary

Cuatro frentes en paralelo: (A) saldar deuda P1 — DT-040 (Gemini pricing en BD) y DT-038 (SoC presentation→domain); (B) saldar deuda P2 — DT-037 (gateway.py <300L) y DT-039 (generate_informe.py <300L); (C) cobertura domain/ hasta 80%; (D) tests de integración E2E + limpieza de artefactos. Los frentes A y D son los más urgentes por tener valor inmediato en producción y en confianza del sistema respectivamente.

**Número de archivos nuevos o modificados**: ~18–22.

---

## Technical Context

**Language/Version**: Python 3.11+ (mismo que el proyecto)

**Primary Dependencies**: pytest, monkeypatch (stdlib), SQLAlchemy (ya en el proyecto), LLM wrapper existente en `infrastructure/`

**Storage**: PostgreSQL 16 en `localhost:5434`, schema `informes_ic`

**Testing**: pytest con markers; `conftest.py` por nivel; fixtures de scope `session` para seed/teardown

**Target Platform**: WSL2 local; tests de integración NO corren en CI sin infraestructura

**Constraints**:
- Tests de integración marcados `@pytest.mark.integration`; `pytest tests/` sin flags no los ejecuta
- Todos los refactors son comportamiento-neutro: cero cambio de lógica, solo reorganización
- La interfaz pública de `gateway.py` y `generate_informe.py` NO cambia
- `app.py` no puede importar nada de `data/` directamente (FR-012)

**Hallazgos de código (audit 2026-09-15)**:
- `infrastructure/llm/gateway.py` — 566 líneas. 3 clases de modelo (`OllamaGatewayLLM` ~90L, `OpenRouterGatewayLLM` ~150L, `ResilientGatewayLLM` ~100L); helpers de errores (~60L); funciones de construcción `build_llm/build_api_llm/build_resilient_api_llm` (~80L); pricing+`CostTracker` (~90L).
- `domain/use_cases/generate_informe.py` — 590 líneas. 2 dataclasses (`InformeParams`, `InformeResult`), 1 dataclass privada `_PipelineContext`, clase `GenerateInforme` con 6 métodos (`_setup_infra` ~65L, `_sweep_stale_web` ~13L, `_promote_cited_web` ~21L, `_run_n0` ~80L, `_run_n2` ~110L, `_run_n3` ~140L).
- `presentation/app.py` — 594 líneas. 3 imports directos de `data/`: (1) `SessionLocal+EmpresaRepository` en `_render_repositorio` (carga empresas para asociación de docs); (2) `SessionLocal+DocumentoRepository` en `_render_repositorio` (lista docs indexados); (3) `SessionLocal+InformeRepository` en `_render_historial` (paginación de informes).
- `_PRICING` en `gateway.py` — no tiene ninguna entrada `gemini-*`. `add_call` usa `.get(modelo, (0.0, 0.0))` → Gemini siempre registra $0.

---

## Constitution Check

### I. Separación Estricta de Capas (SoC) ✅ (con corrección en DT-038)

DT-038 es precisamente la corrección de la violación existente. Tras el fix, `app.py` solo importa de `domain/`. Los refactors de DT-037 y DT-039 mantienen las capas intactas — son reorganizaciones internas dentro de su capa. Los tests viven en `tests/integration/` y usan las APIs de repositorio del dominio, nunca SQL crudo.

### II. Agnosticismo de Dependencias ✅

El refactor de `gateway.py` mantiene el wrapper como única interfaz hacia LangChain. Los sub-módulos del refactor siguen dentro de `infrastructure/llm/`. El spy de US2 se instala sobre el método del wrapper, no sobre LangChain directamente.

### III. Integridad del Dato — Sin Alucinación ✅

DT-040 corrige un dato de negocio incorrecto (`cost_usd=0.0`). El fix no inventa precios — usa los precios públicos de Google AI Studio documentados en `research.md`. Los fixtures de test usan `run_key` prefijado `__test__`; el teardown los elimina.

### IV. Seguridad y Configuración — Sin Credenciales ni Hardcode ✅

Los precios Gemini van en `_PRICING` (constante en código de infraestructura — es datos de configuración, no credenciales). Los identifiers de modelo usados como claves deben coincidir con lo que el settings resuelve, no hardcodearse en código de negocio.

### V. Calidad: Tests y Cobertura ✅

US9 lleva la cobertura de `domain/` de 69% a ≥80%. Los refactors (DT-037, DT-039) no reducen cobertura porque los tests existentes ya testean el comportamiento, no la organización de archivos.

### VI. Cambios Atómicos ✅

Cada frente produce commits atómicos y compilables. El orden de implementación respeta las dependencias: DT-040 (un archivo, ~10 líneas) → DT-038 (nuevo use case + `app.py`) → DT-037 (refactor gateway) → DT-039 (refactor generate_informe) → coverage → tests de integración → limpieza.

---

## Project Structure

### Documentation (this feature)

```text
specs/005-qa-integracion-e2e/
├── plan.md              ← este archivo
├── research.md          ← decisiones técnicas (actualizado 2026-09-15)
├── data-model.md        ← entidades de testing + deuda
├── quickstart.md        ← cómo correr los tests y validar los fixes
├── contracts/
│   └── integration-test-contract.md
└── tasks.md             ← generado por /speckit-tasks
```

### Source Code (cambios en repositorio)

```text
src/ic/
├── infrastructure/llm/
│   ├── gateway.py               ← MODIFICADO: re-export público + ~80L propias (<300)
│   ├── gateway_pricing.py       ← NUEVO: _PRICING, CallRecord, CostTracker (~90L)
│   ├── gateway_models.py        ← NUEVO: OllamaGatewayLLM, OpenRouterGatewayLLM (~260L)
│   └── gateway_errors.py        ← NUEVO: helpers de error + ResilientGatewayLLM (~130L)
├── domain/
│   ├── use_cases/
│   │   ├── generate_informe.py       ← MODIFICADO: shell + InformeParams/Result (<300L)
│   │   ├── _informe_context.py       ← NUEVO: _PipelineContext + _setup_infra + helpers (~160L)
│   │   ├── _informe_nodes_n0.py      ← NUEVO: lógica de _run_n0 (~90L)
│   │   ├── _informe_nodes_n2n3.py    ← NUEVO: lógica de _run_n2 + _run_n3 (~260L)
│   │   └── ui_query_services.py      ← NUEVO: wrappers para 3 repos que app.py necesita (~60L)
│   └── (resto sin cambios)
└── presentation/
    └── app.py                   ← MODIFICADO: 3 imports de data/ → domain/ui_query_services

tests/
├── integration/                 ← NUEVO directorio
│   ├── __init__.py
│   ├── conftest.py              ← prerequisite checks (BD+LLM), marker, fixtures de seed
│   ├── seed/
│   │   ├── __init__.py
│   │   └── sector_fixture.py   ← insert/teardown de IntegrationFixture
│   ├── test_pipeline_e2e.py    ← US1: pipeline completo N0→N1→N2
│   ├── test_sector_cache.py    ← US2: cache hit evita re-invocar LLM
│   └── test_concurrencia.py    ← US3: Generate21Startups en ThreadPoolExecutor
├── test_ui_query_services.py   ← NUEVO: tests unitarios de DT-038
└── (archivos existentes sin cambios)

documentos_sectoriales/
└── FuentesExternas/
    └── README.md                ← NUEVO: documenta propósito de CSVs

pyproject.toml                   ← MODIFICADO: marker `integration` + addopts
.gitignore                       ← MODIFICADO: añadir *.Zone.Identifier
```

---

## Implementation Order

Respeta las dependencias entre cambios. Cada paso debe compilar y pasar `pytest tests/` antes del siguiente.

### Paso 1 — DT-040: Gemini pricing (P1, ~30 min)

**Archivo**: `src/ic/infrastructure/llm/gateway.py` (o `gateway_pricing.py` si DT-037 ya fue)

- Añadir entradas a `_PRICING` para modelos Gemini con precios reales (ver `research.md` Decisión 6).
- Cambiar la lógica de fallback en `CostTracker.add_call`: si el modelo no está en `_PRICING`, retornar `None` y loggear advertencia (no `0.0` silencioso).
- **Test**: `tests/test_cost_tracker.py` ya existe → añadir casos: `test_gemini_model_pricing_nonzero`, `test_unknown_model_logs_warning_not_zero`.

### Paso 2 — DT-038: SoC presentation→domain (P1, ~1h)

**Nuevo archivo**: `src/ic/domain/use_cases/ui_query_services.py`

Expone 3 funciones puras (cada una abre y cierra su propia sesión):
```python
def list_empresas_conocidas() -> list[tuple[str, str]]: ...
def list_documentos_indexados() -> list[DocumentoRow]: ...
def list_informes_recientes(limit: int, offset: int, empresa_filter: str | None) -> list[InformeRow]: ...
```

**Modificación**: `src/ic/presentation/app.py` — reemplazar los 3 bloques de `from ic.data.*` con imports de `ic.domain.use_cases.ui_query_services`.

**Test**: `tests/test_ui_query_services.py` — fake session usando `_FakeSession` del patrón del proyecto; verifica que las funciones retornan el tipo correcto y cierran la sesión.

### Paso 3 — DT-037: Refactor gateway.py (P2, ~1.5h)

Extraer en orden (sin romper imports en cada paso):

1. `gateway_pricing.py`: `_PRICING`, `CallRecord`, `CostTracker`
2. `gateway_models.py`: `OllamaGatewayLLM`, `OpenRouterGatewayLLM`
3. `gateway_errors.py`: `is_rate_limit_error`, `is_transient_network_error`, `is_empty_generation_error`, `ResilientGatewayLLM`
4. `gateway.py`: retiene `build_llm`, `build_api_llm`, `build_resilient_api_llm`, `_provider_base_and_key` + re-exports de las 4 entidades más usadas (`CostTracker`, `CallRecord`, `OllamaGatewayLLM`, `OpenRouterGatewayLLM`) para compatibilidad de imports existentes.

**Verificación**: `wc -l src/ic/infrastructure/llm/*.py` — todos <300. `grep -r "from ic.infrastructure.llm.gateway import" src/` — todos los imports siguen resueltos.

### Paso 4 — DT-039: Refactor generate_informe.py (P2, ~1.5h)

Extraer en orden:

1. `_informe_context.py`: `_PipelineContext` + `_setup_infra` + `_sweep_stale_web` + `_promote_cited_web` — son un bloque cohesivo (setup + ciclo de vida de contexto).
2. `_informe_nodes_n0.py`: función standalone `_run_n0(ctx)` — extraída del método homónimo de `GenerateInforme`.
3. `_informe_nodes_n2n3.py`: funciones standalone `_run_n2(ctx)` y `_run_n3(ctx)`.
4. `generate_informe.py`: retiene `InformeParams`, `InformeResult`, `GenerateInforme` con sus métodos convertidos en delegaciones de 1 línea.

**Verificación**: `wc -l src/ic/domain/use_cases/generate_informe.py src/ic/domain/use_cases/_informe_*.py` — todos <300. Los tests `tests/test_generate_informe.py` siguen pasando sin modificación.

### Paso 5 — Cobertura domain/ ≥80% (P2, ~2h)

1. Ejecutar `uv run pytest --cov=ic.domain --cov-report=term-missing tests/ -m "not integration"` para obtener línea base.
2. Identificar los 5 módulos con menor cobertura.
3. Añadir tests en archivos `tests/test_<módulo>_coverage.py` para cada uno, cubriendo happy path y al menos un caso de error.
4. Repetir medición hasta ≥80%.

### Paso 6 — Tests de integración (US1–US3, ~2h)

1. `pyproject.toml`: añadir marker `integration` + `addopts = "-m 'not integration'"`.
2. `tests/integration/conftest.py`: `check_bd_available()`, `check_llm_available()`, fixture `integration_seed` con `scope="session"`.
3. `tests/integration/seed/sector_fixture.py`: seed + teardown usando `CheckpointRepository` y `EntidadRepository`.
4. `tests/integration/test_pipeline_e2e.py`: 4 tests (TC-001 a TC-004), US1.
5. `tests/integration/test_sector_cache.py`: 3 tests (TC-005 a TC-007), US2 con spy sobre `OpenRouterGatewayLLM._generate`.
6. `tests/integration/test_concurrencia.py`: 2 tests (TC-008 a TC-009), US3 con fake `db_factory`.

### Paso 7 — Limpieza de artefactos (US4, ~15 min)

1. `git rm 1` — eliminar archivo vacío de la raíz.
2. `echo "*.Zone.Identifier" >> .gitignore`.
3. Crear `documentos_sectoriales/FuentesExternas/README.md` (ver `research.md` Decisión 5 para contenido).

---

## Complexity Tracking

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Imports circulares en refactor DT-037 | Alto | Extraer de adentro hacia afuera; verificar con `python -c "import ic.infrastructure.llm.gateway"` tras cada archivo |
| `_PipelineContext` referencia métodos de `GenerateInforme` en DT-039 | Medio | Convertir métodos a funciones standalone antes de mover el contexto |
| El precio Gemini en `_PRICING` no coincide con el model string del `.env` | Medio | Verificar el string exacto en `settings.gemini_*` y el log de invocaciones; documentar en `research.md` |
| `add_call` con `cost_usd=None` puede romper código que suma costos | Bajo | Buscar todos los usos de `.costo_usd` con grep antes del cambio; ajustar sumadores si es necesario |
