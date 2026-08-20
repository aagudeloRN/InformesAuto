# Implementation Plan: Cap 2.1 — Activar Sub-módulos Modulares y Numeración de Secciones

**Branch**: `003-cap21-activar-submodulos` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

## Summary

Activar el sistema modular de Cap 2.1 en el pipeline real de generación (`generate_n1.py`) y añadir numeración jerárquica (`2.1.1.` / `2.1.2.` / `2.1.3.`) a los encabezados de los tres sub-módulos. El trabajo comprende tres cambios distintos: (1) tres cambios de una línea en los `_HEADING` de los sub-módulos, (2) wiring de `Generate21Jugadores` en `_fn_cap2` con inyección de `engine` y `run_key` para habilitar el cache sectorial, y (3) un ajuste de thread-safety en `Generate21Startups` para que abra su propia sesión de BD cuando se invoca desde un pool de threads.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: SQLAlchemy (via wrapper), LangChain (via `InvokableChain` protocol), `concurrent.futures.ThreadPoolExecutor`

**Storage**: PostgreSQL schema `informes_ic` vía `CheckpointRepository`; BD compartida puerto 5434

**Testing**: `pytest`, mocks in-memory (`_FakeChain`, `_FakeStore`, `_FakeWebConnector`, `_FakeEntidadRepo`)

**Target Platform**: Pipeline N1 en `generate_n1.py` (`_fn_cap2`)

**Performance Goals**: Segunda corrida para el mismo sector debe completar 2.1 en < 10 s (cache hit); primera corrida sin tiempo límite adicional (misma latencia que el flujo monolítico anterior)

**Constraints**: Constitution I: archivos < 300 líneas; Constitution II: sin imports directos de librerías externas en `domain/`; thread-safety obligatoria (los sub-módulos corren en un `ThreadPoolExecutor`)

## Constitution Check

### I. Separación Estricta de Capas (SoC) — PASS

- Los tres sub-módulos viven en `domain/use_cases/` — correcto.
- Los chain builders viven en `domain/chains/` — correcto.
- El `engine` se importa desde `ic.data.database` de forma lazy (dentro del body de la función), exactamente igual al patrón ya vigente en `generate_informe.py` y `generate_n1.py`.
- `generate_n1.py` ya supera 300 líneas (LEGACY comment vigente del T043). Este PR no agrega líneas netas sustanciales (el wiring reemplaza comentarios y agrega ~25 líneas).

**Riesgo**: `generate_n1.py` actualmente tiene 550+ líneas (LEGACY). Este plan no empeora esa situación pero no la resuelve. El LEGACY comment de T043 lo documenta; el split queda pendiente de decisión humana.

### II. Agnosticismo de Dependencias — PASS

- Los sub-módulos ya usan `InvokableChain as Runnable` en lugar de importar LangChain directamente (T039/T041).
- El ajuste de thread-safety en `Generate21Startups` usa `SessionLocal` como factory (callable) — no importa SQLAlchemy directamente en domain, sino que recibe el factory inyectado desde `generate_n1.py` (la capa que ya importa `SessionLocal` de `ic.data.database`).

### III. Integridad del Dato — PASS

- Los sub-módulos ya implementan regla de ausencia y solo citan fragmentos recuperados.
- El cache sectorial reutiliza resultados previos sin modificarlos.

### IV. Seguridad y Configuración — PASS

- Sin nombres de modelo hardcodeados (los chains reciben el LLM del contexto).
- Sin credenciales en código.

### V. Calidad: Tests, Cobertura — REQUIRES ACTION

- Toda modificación de API (`Generate21Startups` constructor y `_HEADING`) debe tener test unitario en el mismo PR.
- Tests afectados por cambio de API: `tests/test_generate_21_startups.py` (si existe) y cualquier mock que construya `Generate21Startups`.

### VI. Cambios Atómicos — PASS

- Cada fase produce un estado compilable y runnable.

## Project Structure

### Documentation (this feature)

```text
specs/003-cap21-activar-submodulos/
├── plan.md              ← este archivo
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── checklists/
│   └── requirements.md
└── tasks.md             ← /speckit-tasks output (pendiente)
```

### Source Code (archivos tocados)

```text
src/ic/domain/use_cases/
├── generate_21_globales.py       # FR-002: _HEADING +numeración
├── generate_21_regionales.py     # FR-002: _HEADING +numeración
├── generate_21_startups.py       # FR-002: _HEADING +numeración; thread-safety db_factory
└── generate_n1.py                # FR-001/FR-003: wiring Generate21Jugadores + engine

tests/
├── test_generate_21_headings.py  # NUEVO: verifica _HEADING numerados en output
└── test_generate_n1_jugadores.py # NUEVO: verifica jugadores_use_case invocado en _fn_cap2
```

## Phase 0: Research

Todos los NEEDS CLARIFICATION resueltos durante `/speckit-specify`. Ver `research.md`.

## Phase 1: Design & Contracts

### Decisión de thread-safety — `Generate21Startups`

**Problema**: `Generate21Startups.execute()` llama `self._entidad_repo.list_locales_by_sector(...)`. Cuando el orquestador `Generate21Jugadores` ejecuta los tres sub-módulos en paralelo via `ThreadPoolExecutor`, cada llamada corre en su propio thread. La sesión SQLAlchemy inyectada en el constructor (creada en el bloque `with SessionLocal() as db_kb:` de `_fn_cap2`) ya está cerrada cuando el thread arranca.

**Solución elegida**: Modificar `Generate21Startups.__init__` para aceptar `db_factory: Callable[[], ContextManager] | None = None`. En `execute()`, si `db_factory` está presente, abrir una sesión fresca. El parámetro `entidad_repo` existente queda como alternativa (para tests que inyectan un fake). Backward-compatible: los tests existentes siguen pasando `entidad_repo=FakeRepo`.

```python
# generate_21_startups.py — API resultante (resumen)
class Generate21Startups:
    def __init__(
        self,
        chain_perfil: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        entidad_repo: EntidadRepository | None = None,
        db_factory: Callable | None = None,
        max_locales: int = 3,
        max_internacionales: int = 2,
    ): ...

    def execute(self, ...) -> Cap21Startups:
        if self._db_factory:
            with self._db_factory() as db:
                repo = EntidadRepository(db)
                filas_locales = repo.list_locales_by_sector(sectores_ancla, segmento="startup", ...)
        elif self._entidad_repo:
            filas_locales = self._entidad_repo.list_locales_by_sector(...)
        else:
            filas_locales = []
        ...
```

### Wiring en `generate_n1.py` — `_fn_cap2`

Dentro del cuerpo de `_fn_cap2`, después de construir `escalation_chain` y antes de instanciar `GenerateBenchmarking`, agregar:

```python
# Lazy imports (mismo patrón que el resto del archivo)
from ic.data.database import engine as db_engine
from ic.domain.chains.chain_02c_pares_globales import build_chain_pares_globales
from ic.domain.chains.chain_cap2_21_globales import build_chain_cap2_21_globales
from ic.domain.chains.chain_cap2_21_regionales import build_chain_cap2_21_regionales
from ic.domain.chains.chain_cap2_21_startups import build_chain_cap2_21_startups
from ic.domain.use_cases.generate_21_globales import Generate21Globales
from ic.domain.use_cases.generate_21_jugadores import Generate21Jugadores
from ic.domain.use_cases.generate_21_regionales import Generate21Regionales
from ic.domain.use_cases.generate_21_startups import Generate21Startups
from ic.data.database import SessionLocal

llm_21 = ctx.api_llm or ctx.llm
jugadores_use_case = Generate21Jugadores(
    gen_globales=Generate21Globales(
        chain_candidatos=build_chain_pares_globales(llm_21),
        chain_perfil=build_chain_cap2_21_globales(llm_21),
        store=store,
        web_connector=web,
    ),
    gen_regionales=Generate21Regionales(
        chain_perfil=build_chain_cap2_21_regionales(llm_21),
        store=store,
        web_connector=web,
    ),
    gen_startups=Generate21Startups(
        chain_perfil=build_chain_cap2_21_startups(llm_21),
        store=store,
        web_connector=web,
        db_factory=SessionLocal,
    ),
)
```

Y en `GenerateBenchmarking(...)`:
```python
cap = GenerateBenchmarking(
    ...,
    jugadores_use_case=jugadores_use_case,
    engine=db_engine,
    sub_gics=g_code,
).execute(...)
```

### Numeración de encabezados

| Archivo | Antes | Después |
|---------|-------|---------|
| `generate_21_globales.py:24` | `"### Referentes Globales"` | `"### 2.1.1. Referentes Globales"` |
| `generate_21_regionales.py:24` | `"### Referentes Regionales LatAm/Colombia"` | `"### 2.1.2. Referentes Regionales LatAm/Colombia"` |
| `generate_21_startups.py:24` | `"### Startups y Disruptores del sector"` | `"### 2.1.3. Startups y Disruptores del sector"` |

La referencia `_SECTION_LABEL` (usada en `build_absent_paragraph`) no cambia — el label de ausencia no lleva numeración.

### Sector cache — flujo resultante

```
generate_n1._fn_cap2
  → GenerateBenchmarking(jugadores_use_case, engine=db_engine, sub_gics=g_code)
    → execute(sector_gics_code=g_code)
      sector_run_key = f"sector_{g_code}_{g_code or 'any'}"
      cached_g, cached_r, cached_s = _load_sector_cache(db_engine, sector_run_key)
      jugadores_use_case.execute(cached_globales=cached_g, ..., engine=db_engine, run_key=sector_run_key)
        → [si no cacheado] gen_globales.execute() → checkpoint_hooks.save_cap(engine, run_key, "cap2_21_globales", ...)
        → [si no cacheado] gen_regionales.execute() → checkpoint_hooks.save_cap(...)
        → [si no cacheado] gen_startups.execute() → checkpoint_hooks.save_cap(...)
```

## Complexity Tracking

No hay violaciones de Constitution no justificadas. El archivo `generate_n1.py` ya supera 300 líneas (documentado en T043, pendiente decisión de split).
