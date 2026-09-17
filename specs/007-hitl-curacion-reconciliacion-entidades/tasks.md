# Tasks: 007 — Curación Interactiva HITL y Reconciliación de Entidades por NIT

**Branch**: `007-hitl-curacion-reconciliacion-entidades`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Fecha**: 2026-09-16

---

## Phase 1: Setup & Data Layer (US1 — Reconciliación de Entidades por NIT)

**Purpose**: Implementar el caso de uso y repositorio para reconciliar entidades duplicadas por NIT.

- [x] T001 [US1] Crear métodos de fusión en repositorio (`merge_entidades_por_nit`) en `src/ic/data/repositories/entidad_repo.py` y `_entidad_reconciliation.py`.
- [x] T002 [US1] Implementar el caso de uso `ReconcileEntidades` en `src/ic/domain/use_cases/reconcile_entidades.py` (< 250L).
- [x] T003 [US1] Crear script ejecutable `scripts/reconciliar_entidades_nit.py` con soporte para `--dry-run` y `--execute`.
- [x] T004 [US1] Crear tests unitarios en `tests/test_reconcile_entidades.py` validando fusión de atributos, aliases, deduplicación y preservación de estado.

Checkpoint US1: Reconciliación por NIT 100% testeada e idempotente.

---

## Phase 2: Domain Services & UI Query Services (US2 — Servicios para HITL)

**Purpose**: Exponer servicios de consulta y mutación de candidatos para la interfaz de usuario.

- [x] T005 [US2] Implementar `fetch_candidatos_competidores(empresa, sector, ciiu)` en `src/ic/domain/use_cases/ui_query_services.py`.
- [x] T006 [US2] Implementar `mark_entidad_descartada(entidad_id)` y `add_competidor_manual(...)` en `ui_query_services.py`.
- [x] T007 [US2] Crear tests unitarios en `tests/test_ui_query_services.py` para los nuevos endpoints de consulta/mutación.

Checkpoint US2: Servicios de dominio listos para consumo por la interfaz.

---

## Phase 3: Presentation Layer (US2 & US3 — UI Streamlit HITL)

**Purpose**: Implementar la vista interactiva de curación y conectar con el pipeline.

- [x] T008 [US2] Crear el módulo `src/ic/presentation/views/view_hitl.py` (< 250L) con panel multi-tier de curación (Globales, Regionales, Startups).
- [x] T009 [US2] Integrar el flujo de dos pasos en `src/ic/presentation/views/view_generar.py` (Paso 1: Resolución y curación; Paso 2: Ejecución).
- [x] T010 [US2] Actualizar `InformeParams` y `GenerateInforme` para recibir listas de competidores curados explícitos sin sobreescritura del KB.
- [x] T011 [US3] Actualizar `src/ic/presentation/views/view_historial.py` para mostrar desglose de competidores utilizados por informe.

Checkpoint US3: Experiencia interactiva HITL operativa y desacoplada en Streamlit.

---

## Phase 4: Verification, Invariants & Documentation

**Purpose**: Garantizar 0 regresiones, regla <300L y sincronización de documentación.

- [x] T012 [P] Ejecutar `uv run ruff check .` y garantizar 0 errores.
- [x] T013 [P] Ejecutar suite de pruebas completa `uv run pytest -m "not slow and not integration"` y validar 100% passed.
- [x] T014 [P] Verificar que ningún archivo en `src/` supere las 300 líneas.
- [x] T015 [P] Actualizar `docs/PROXIMA_SESION.md` y `CHANGELOG.md` documentando la finalización del Spec 007 y preparando el arranque del Spec 008 (Opción B: Ingesta Paralela).

---

## Phase 5: Convergence

- [x] T016 [US1/CA5] CRITICAL: Crear script de migración DDL `scripts/migrations/007_add_aliases_column.sql` con `ALTER TABLE ic.entidades ADD COLUMN IF NOT EXISTS aliases TEXT[] DEFAULT '{}'` — sin esta migración `_entidad_reconciliation.py` falla en runtime al leer la columna `aliases` (missing)
- [x] T017 [US1/CA2] Actualizar `_select_canonical_entity` en `src/ic/domain/use_cases/reconcile_entidades.py` para usar cantidad de atributos (n_atributos del repo) como 2° criterio en lugar de `n_menciones`, alineando con Q4-Clarification 2026-09-17 (contradicts)
- [x] T018 [US2/T007] Crear `tests/test_ui_query_services.py` con tests unitarios para `fetch_candidatos_competidores` (retorna dict con claves globales/regionales/startups), `add_competidor_manual` (retorna dict con id/nombre/tier) y comportamiento session-only de descartes — T007 marcado done pero el archivo no existe (missing)
- [x] T019 [US3/CA2] Agregar sección de feedback rápido en `src/ic/presentation/views/view_historial.py`: botones "Relevante" / "Con observaciones" por informe, con campo opcional de texto, persistiendo calificación en `historial_informe.metricas_fiabilidad` o tabla de auditoría (missing)
- [x] T020 [Q2-Clarification] Añadir docstring explícito a `mark_entidad_descartada` en `ui_query_services.py` aclarando que es utilidad de curación manual (no HITL-session); y verificar que `view_hitl.py` no la invoque en el flujo de descarte por checkbox (contradicts)
