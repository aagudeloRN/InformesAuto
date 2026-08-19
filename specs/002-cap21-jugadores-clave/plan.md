# Implementation Plan: Cap 2.1 — Jugadores Clave Modular

**Branch**: `002-cap21-jugadores-clave` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-cap21-jugadores-clave/spec.md`

---

## Summary

Modularizar la sección 2.1 (Jugadores Clave) del Cap 2 en tres sub-módulos independientes con fuentes primarias distintas: Referentes Globales (LLM→web por candidato), Referentes Regionales (EMIS primary + web complement) y Startups/Disruptores (StartIA local + web internacional). Cada sub-módulo tiene su propio use case, chain LLM especializada y checkpoint, lo que permite visibilidad parcial y control granular de calidad. El orquestador coordina los tres, deduplica y ensambla la sección completa que alimenta al Cap 2.2.

---

## Technical Context

**Language/Version**: Python 3.12 (gestión vía `uv`)

**Primary Dependencies**: LangChain (via `infrastructure/llm/gateway`), SQLAlchemy + pgvector (via `data/repositories/`), Tavily WebConnector (via `infrastructure/sources/`)

**Storage**: PostgreSQL/pgvector esquema `informes_ic` — tablas `entidades`, `entidad_atributos`, `embeddings`, `documentos`; checkpoints en `checkpoint_capitulos`.

**Testing**: pytest + `_FakeSession` para unit tests sin DB; `@pytest.mark.db` para integración.

**Target Platform**: Linux server (WSL2 dev / Docker prod)

**Project Type**: Pipeline de generación de informes — use cases del dominio dentro de la arquitectura SoC existente.

**Performance Goals**: Cada sub-módulo ≤3 minutos desde inicio hasta checkpoint persistido (SC-001). Los tres sub-módulos pueden correr en paralelo vía `ThreadPoolExecutor` existente.

**Constraints**:
- Archivos ≤300 líneas (Constitution I)
- Sin credenciales ni modelos hardcodeados (Constitution IV)
- Sin inventar datos; ausencia si retrieval insuficiente (Constitution III)
- Wrappers para toda librería externa (Constitution II)

**Scale/Scope**: 3 use cases nuevos + 3 chains nuevas + 1 orquestador + extensión de 2 métodos existentes + 4 tipos nuevos en `shared/types.py`.

---

## Constitution Check

*GATE verificado antes y después del diseño.*

| Principio | Evaluación | Acción |
|-----------|-----------|--------|
| **I. SoC — ≤300 líneas** | ✅ PASS | Cada use case ~150–200 líneas; cada chain ~80–120 líneas; tipos en shared/types.py |
| **I. SoC — capas** | ✅ PASS | Chains en `domain/chains/`, use cases en `domain/use_cases/`, tipos en `shared/`, filtro SQL en `data/repositories/` |
| **II. Agnosticismo** | ✅ PASS | LangChain solo en chains (domain/chains/), no en use cases. WebConnector y Store son wrappers existentes. |
| **III. Integridad/Sin alucinación** | ✅ PASS | FR-011/FR-013 obligan ausencia; chunks_usados obligatorio en todos los tipos de retorno |
| **IV. Sin hardcode** | ✅ PASS | `max_empresas` en constructor (no hardcodeado); sector GICS resuelto en N0; modelos en .env |
| **V. Tests 80% domain/** | ✅ PASS | 3 archivos de test nuevos con `_FakeSession`; mínimo 5 tests por use case |
| **VI. Cambios atómicos** | ✅ PASS | Cada US es entregable independiente con sus tests; sin TODOs que rompan ejecución |

**Constitution Check post-diseño**: sin violaciones. Los cambios a `embedding_repo.py` y `pgvector_store.py` son aditivos (parámetro opcional con default que preserva invariante total).

---

## Project Structure

### Documentation (this feature)

```text
specs/002-cap21-jugadores-clave/
├── plan.md              ← este archivo
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── use_case_contracts.md
├── checklists/
│   └── requirements.md
└── tasks.md             ← generado por /speckit-tasks
```

### Source Code

```text
src/ic/
├── domain/
│   ├── use_cases/
│   │   ├── generate_21_globales.py     [NUEVO ~180 líneas]
│   │   ├── generate_21_regionales.py   [NUEVO ~150 líneas]
│   │   ├── generate_21_startups.py     [NUEVO ~160 líneas]
│   │   └── generate_21_jugadores.py    [NUEVO ~120 líneas] ← orquestador
│   └── chains/
│       ├── chain_cap2_21_globales.py   [NUEVO ~80 líneas]
│       ├── chain_cap2_21_regionales.py [NUEVO ~80 líneas]
│       └── chain_cap2_21_startups.py   [NUEVO ~80 líneas]
├── data/
│   └── repositories/
│       └── embedding_repo.py           [MODIFICADO +10 líneas]
├── infrastructure/
│   └── retrieval/
│       └── pgvector_store.py           [MODIFICADO +5 líneas]
└── shared/
    ├── types.py                        [MODIFICADO +4 dataclasses ~40 líneas]
    └── checkpoint_serde.py             [MODIFICADO +4 clases en _REGISTRY]

tests/
├── test_generate_21_globales.py        [NUEVO ~120 líneas]
├── test_generate_21_regionales.py      [NUEVO ~100 líneas]
├── test_generate_21_startups.py        [NUEVO ~110 líneas]
├── test_generate_21_jugadores.py       [NUEVO ~80 líneas]
└── test_embedding_repo.py              [MODIFICADO +1 test fuente_tipo_filter]
```

**Archivos existentes con integración post-implementación** (no se tocan en este feature):

- `generate_benchmarking.py` — actualmente genera 2.1 inline; en una segunda iteración se refactoriza para llamar a `generate_21_jugadores`. Se mantiene invariante hasta que los 3 sub-módulos estén validados.
- `generate_n1.py` — sin cambios; `generate_benchmarking` es el punto de integración.

**Decisión de integración**: los sub-módulos 2.1 se desarrollan como módulos autónomos primero (con sus propios entry points de testing). La integración con `generate_benchmarking.py` es una tarea posterior (Phase 4) que no bloquea la validación de calidad de cada sub-módulo.

---

## Fases de Implementación

### Phase 1 — Infraestructura base (prerequisito de las 3 US)

Parámetro `fuente_tipo_filter` en `embedding_repo` + `pgvector_store`. Tipos `Cap21*` en `shared/types.py`. Registro en `checkpoint_serde.py`.

**Archivos**: `embedding_repo.py`, `pgvector_store.py`, `shared/types.py`, `checkpoint_serde.py`
**Tests**: test de regresión en `test_embedding_repo.py` (filtro opcional no rompe callers)

### Phase 2 — US1: Referentes Globales (P1)

`generate_21_globales.py` + `chain_cap2_21_globales.py` + `test_generate_21_globales.py`.

**Punto de parada**: `uv run pytest tests/test_generate_21_globales.py -v` → 100% verde.

### Phase 3 — US2: Referentes Regionales (P2)

`generate_21_regionales.py` + `chain_cap2_21_regionales.py` + `test_generate_21_regionales.py`.

**Punto de parada**: `uv run pytest tests/test_generate_21_regionales.py -v` → 100% verde.

### Phase 4 — US3: Startups y Disruptores (P3)

`generate_21_startups.py` + `chain_cap2_21_startups.py` + `test_generate_21_startups.py`.

**Punto de parada**: `uv run pytest tests/test_generate_21_startups.py -v` → 100% verde.

### Phase 5 — Orquestador + integración

`generate_21_jugadores.py` + `test_generate_21_jugadores.py`.
Integración en `generate_benchmarking.py` (reemplaza generación inline de 2.1 por llamada al orquestador).
Regresión completa: `uv run pytest` → 0 fallos.

### Phase 6 — Polish

Lint (`ruff`) + format (`black`) + validación de escenarios del `quickstart.md`.

---

## Complexity Tracking

*(Sin violaciones de constitution — tabla vacía)*

---

## Decisiones clave y referencias cruzadas

| Decisión | Archivo | Referencia |
|----------|---------|-----------|
| Reusar `chain_02c_pares_globales` para candidatos globales | `generate_21_globales.py` | research.md D3 |
| Añadir `fuente_tipo_filter` a `search_similar` | `embedding_repo.py` | research.md D2, contracts/ |
| StartIA vía `list_locales_by_sector(segmento="startup")` | `generate_21_startups.py` | research.md D1 |
| Checkpoint keys `cap2_21_*` | `generate_21_jugadores.py` | research.md D6 |
| Deduplicación cross-tier en orquestador | `generate_21_jugadores.py` | research.md D7 |
| Integración con `generate_benchmarking.py` diferida a Phase 5 | — | research.md D5 |
