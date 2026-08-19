# Implementation Plan: Multi-sector Benchmarking — DT-UI04f

**Branch**: `spec-driven-experiment` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-multisector-benchmark/spec.md`

## Summary

Ampliar el repositorio de entidades del KB para que `list_competidores_by_sector`
y `list_ficha_atributos_by_sector` acepten una lista de sectores GICS (en lugar
de uno solo) y excluyan la empresa focal también por aliases registrados. El
caller (`generate_n1.py`) pasa la lista ya disponible en `sectores_ancla_local`.
`list_locales_by_sector` ya es multi-sector (DT-UI04b); no se toca.

## Technical Context

**Language/Version**: Python 3.11 (uv)

**Primary Dependencies**: SQLAlchemy 2.x (ORM + `text()`), PostgreSQL 15 con
extensión pgvector; pytest para tests; ruff + black para linting.

**Storage**: PostgreSQL, schema `informes_ic`. Tablas afectadas: `entidades`,
`entidad_atributos`. `entidad_sectores` no se toca en esta feature.

**Testing**: pytest con `_FakeSession` (tests unitarios sin BD) y marcador `@pytest.mark.db` (integración).

**Target Platform**: Linux server (WSL2 en dev); Docker Compose en producción (192.168.0.99).

**Project Type**: Servicio de backend Python (librería de dominio + capa de datos).

**Performance Goals**: Una búsqueda multi-sector (N sectores) debe completarse
en tiempo similar a una búsqueda mono-sector; sin N round-trips adicionales.

**Constraints**:
- Schema-aware: todas las queries prefijan con `informes_ic`.
- Backward compat: `str` debe funcionar sin cambios en los callers existentes.
- `entidad_repo.py` ya tiene 527 líneas (pre-existing); no extraer en este PR.
- No hardcodear códigos GICS ni nombres de modelos LLM.

**Scale/Scope**: KB de ~100k entidades; búsquedas retornan ≤100 candidatos
antes del re-rank por solape de producto.

## Constitution Check

*Evaluado contra `.specify/memory/constitution.md` v1.0.0 (ratificada 2026-08-18).*

| Principio | Estado |
|-----------|--------|
| **I. SoC** — cambios solo en capas `data/` y `domain/`; `presentation/` intacta | ✅ |
| **I. SoC** — `entidad_repo.py` 527 líneas (pre-existing, no introducido por esta feature) | ⚠️ DEUDA PRE-EXISTENTE — ticket de refactor pendiente; no bloquea este PR |
| **II. Agnosticismo de dependencias** — no se añaden librerías externas nuevas; SQLAlchemy ya tiene wrapper | ✅ |
| **III. Integridad del dato** — no toca la lógica de retrieval ni de citación APA | ✅ |
| **III. Integridad del dato** — dedup por `entidad_id` garantiza que un competidor no aparece dos veces | ✅ |
| **IV. Sin credenciales ni hardcode** — no se introducen códigos GICS, modelos ni secrets hardcodeados | ✅ |
| **IV. Sin credenciales ni hardcode** — queries schema-aware (`informes_ic`); código sin magic strings de sector | ✅ |
| **V. Tests** — nuevos tests unitarios (`_FakeSession`) + regresión de tests existentes sin modificación | ✅ |
| **V. Tests** — cobertura de los 4 nuevos casos: multisector, alias, backward-compat, fichas | ✅ |
| **VI. Cambio atómico** — modificación puntual en 2 archivos; PR completo y ejecutable sin dependencias pendientes | ✅ |
| **VI. No destructivo** — backward compat garantizada: `str` se normaliza internamente a lista | ✅ |
| **Infraestructura** — schema `informes_ic` respetado; Ollama y puertos no afectados | ✅ |

**Veredicto**: APROBADO con 1 advertencia pre-existente documentada. La feature puede proceder.
| Commits Conventional | ✅ — `feat(kb): multi-sector globales + exclusión por alias` |

## Project Structure

### Documentation (this feature)

```text
specs/001-multisector-benchmark/
├── plan.md              # Este archivo
├── research.md          # Decisiones de diseño
├── data-model.md        # Entidades y firmas de métodos
├── quickstart.md        # Guía de validación
├── contracts/
│   └── entidad_repo_contracts.md
└── tasks.md             # Generado por /speckit-tasks
```

### Source Code (repositorio raíz)

```text
src/ic/data/repositories/
└── entidad_repo.py          # Cambio principal: firmas + SQL + dedup + alias exclusion

src/ic/domain/use_cases/
└── generate_n1.py           # Ajustar 3 llamadas para pasar lista de sectores

tests/
├── test_kb_entidades.py     # Nuevos tests: multisector_competidores, alias_exclusion
└── test_dt064_fichas.py     # Nuevo test: list_ficha_atributos multisector
```

**Structure Decision**: Modificación puntual de archivos existentes en sus
capas correctas (data + domain). No se crean módulos nuevos en este PR.

## Implementation Steps

### Paso 1 — `list_competidores_by_sector` en `entidad_repo.py`

**Archivo**: `src/ic/data/repositories/entidad_repo.py` (línea 298)

Cambios:
1. Renombrar parámetro `sector_gics: str` → `sectores_gics: str | Sequence[str]`.
2. Normalización interna:
   ```python
   if isinstance(sectores_gics, str):
       sectores = [sectores_gics] if sectores_gics else []
   else:
       sectores = [s for s in sectores_gics if s]
   if not sectores:
       return []
   ```
3. SQL: cambiar `WHERE e.sector_gics = :sector` → `WHERE e.sector_gics = ANY(:sectores)`.
4. Añadir `e.aliases` al SELECT (necesario para exclusión por alias).
5. Deduplicación post-fetch por `_clave_exclusion(nombre)` (conservar primero = mejor rank).
6. Exclusión extendida: además de `_clave_exclusion(r.nombre)`, chequear cada elemento
   de `r.aliases` (JSONB deserializado) contra `norm_excl`.

### Paso 2 — `list_ficha_atributos_by_sector` en `entidad_repo.py`

**Archivo**: `src/ic/data/repositories/entidad_repo.py` (línea 205)

Cambios:
1. Renombrar `sector_gics: str` → `sectores_gics: str | Sequence[str]`.
2. Normalización idéntica al Paso 1.
3. SQL: `WHERE e.sector_gics = :sector` → `WHERE e.sector_gics = ANY(:sectores)`.
4. Sin cambios en lógica de priorización de campos ni dedup (ya correcto).

### Paso 3 — `generate_n1.py`: pasar lista de sectores

**Archivo**: `src/ic/domain/use_cases/generate_n1.py`

Cambios (tres puntos de llamada):
- **Línea 100** (`_descubrir_globales`): `list_competidores_by_sector(g_code, ...)` →
  `list_competidores_by_sector(sectores, ...)` donde `sectores = sectores_ancla_local(g_code, ciiu_ancla)`.
- **Línea 198** (`_fn_cap2`): idem.
- **Línea 225** (`_fn_cap2`): `list_ficha_atributos_by_sector(g_code, nombres_ficha)` →
  `list_ficha_atributos_by_sector(sectores, nombres_ficha)`.

  `sectores` ya existe en scope (línea 80): `sectores_local = sectores_ancla_local(g_code, ciiu_ancla)`.
  Para globales se usa la misma lista; renombrar o extraer variable explícita `sectores_globales`.

### Paso 4 — Tests nuevos

**Archivo**: `tests/test_kb_entidades.py`

Tests a añadir:
1. `test_list_competidores_multisector_une_candidatos`: `FakeSession` con entidades
   en sectores `"1040"` y `"1050"`; verificar que ambas aparecen, sin duplicados.
2. `test_list_competidores_excluye_por_alias`: entidad con alias `"Compañía de Galletas NOEL"`;
   `exclude_nombre="NOEL SAS"` → entidad no aparece.
3. `test_list_competidores_multisector_sector_vacio_no_consulta`: lista vacía → `[]`, sin SQL.

**Archivo**: `tests/test_dt064_fichas.py`

Tests a añadir:
1. `test_fichas_multisector`: `FakeSession` con competidores en 2 sectores →
   `list_ficha_atributos_by_sector(["3020", "3030"], nombres)` retorna fichas de ambos.

## Complexity Tracking

| Elemento | Nota |
|----------|------|
| `entidad_repo.py` > 300 líneas | Pre-existing. No se extrae en este PR. Ticket de refactor pendiente. |
