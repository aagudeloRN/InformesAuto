# Handoff — próxima sesión (arranque en chat limpio)

> Estado al cierre 2026-09-17. Rama `007-hitl-curacion-reconciliacion-entidades` / `spec-driven-experiment` (Spec 007 completado).
> Copia el bloque "PROMPT DE ARRANQUE" de abajo en un chat nuevo.

## Dónde quedamos
- **Spec 007 (Curación Interactiva HITL y Reconciliación de Entidades por NIT) COMPLETADO**:
  - **US1 — Reconciliación por NIT (`DT-050b`)**:
    - Módulo `_entidad_reconciliation.py` y métodos `list_duplicados_por_nit()` / `merge_entidades_por_nit()` en `EntidadRepository`.
    - Caso de uso determinista `ReconcileEntidades` (< 250L) en `src/ic/domain/use_cases/reconcile_entidades.py`.
    - Script ejecutable `scripts/reconciliar_entidades_nit.py` con soporte `--dry-run` y `--execute` y migración DDL idempotente de `aliases JSONB`.
  - **US2 — Panel Interactivo HITL Pre-Generación**:
    - Módulo Streamlit `src/ic/presentation/views/view_hitl.py` (< 250L) con selector multi-tier y edición en vivo.
    - Integración de dos pasos en `view_generar.py`.
    - Inyección de `competidores_curados` en `InformeParams` respetado en `cargar_kb_competidores_ancla`.
  - **US3 — Auditoría Post-Generación**:
    - Vista de historial `view_historial.py` actualizada con el desglose de competidores utilizados.
  - **Regla < 300 Líneas (Constitución I)**: 100% de los archivos en `src/` estrictamente `< 300L` (máximo 297L).
  - **Calidad y Cobertura**: Linter `ruff check .` con 0 errores; suite completa rápida `pytest` verde (706 passed).

---

## PROMPT DE ARRANQUE (copiar en chat limpio)

```
ROL: Claude Code / Antigravity, ingeniero senior de InformesAuto.
Proyecto en /home/aagudelo/Test/InformesAuto. Localhost/dev (WSL2).

CONTEXTO (sesión previa 2026-09-17, Spec 007 completado):
- Spec 007 (Curación Interactiva HITL y Reconciliación por NIT) cerrado con 0 errores de ruff y 706 tests verdes:
  * Script CLI scripts/reconciliar_entidades_nit.py (--dry-run / --execute) y uso de caso ReconcileEntidades.
  * Interfaz de curación previa HITL en Streamlit (view_hitl.py) e integración con InformeParams.
  * Historial actualizado con competidores anclados por tier.
  * Todos los archivos de src/ estrictamente < 300 líneas.

SIGUIENTE PASO:
- Arrancar Spec 008 (Opción B: Ingesta Masiva Paralela de PDFs y Paralelización Multi-Worker).
```
