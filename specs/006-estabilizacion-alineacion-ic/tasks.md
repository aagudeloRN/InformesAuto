# Tasks: 006 — Estabilización, Alineación Documental y Definición de Alcance de Inteligencia Competitiva

**Branch**: `006-estabilizacion-alineacion-ic`
**Spec**: [/specs/006-estabilizacion-alineacion-ic/spec.md](spec.md)
**Plan**: [/specs/006-estabilizacion-alineacion-ic/plan.md](plan.md)
**Fecha**: 2026-09-16

---

## Phase 1: Setup & Baseline

**Purpose**: Verificación inicial de linter, tests y medición de líneas.

- [ ] T001 Registrar medición baseline de tests failing (5), errores de linter (8) y archivos >300L en `docs/decisions/FASE31_006_AUDIT_BASELINE.md`
- [ ] T002 [P]Verificar configuración local de `ruff` y `pytest` sobre `006-estabilizacion-alineacion-ic`

---

## Phase 2: User Story 1 — Higiene Técnica y Estabilización Inmediata (Priority: P1)

Objetivo: Reparar todos los tests unitarios fallidos y errores de linter dejados por Spec 005.

- [ ] T003 [US2] Refactorizar `model=settings.llm_local_analytic_model` en `build_llm(s)` de `src/ic/infrastructure/llm/gateway.py` (eliminar `settings.ollama_model`).
- [ ] T004 [US2] Corregir la firma y orden de parámetros en `_provider_base_and_key` en `ic.infrastructure.llm.gateway` y alinearlos con `tests/test_gateway_robustez.py`.
- [ ] T005 [US1] Corregir el acceso a `llm_api_synth_model` en `build_api_llm(s, tier="synth")` de `src/ic/infrastructure/llm/gateway.py` (eliminar `settings.gemini_synth_model`).
- [ ] T006 [US1] Alinear los argumentos de `build_resilient_api_llm` (`fallback`, tiers) entre `gateway.py`, test_fase15_resilience.py y test_gateway_robustez.py.
- [ ] T007 [USL Formatear y ajustar líneas de comentarios/constantes en los 5 scripts de `scripts/` (`backfill_entidad_sectores.py`, `build_emis_index.py`, `seed_empresas_colombia.py`, `seed_informes_manuales.py`, `seed_startia.py`) para cumplir E501 *<= 100 chars).
- [ ] T008 [US2] Ejecutar y validar que `uv run ruff check` devuelve 0 errores y `uv run pytest -m "not slow and not integration"` devuelve >= 706 passed (100% verde).

Checkpoint US1: Suite diagnóstica y codebase 100% en verde.

---

## Phase 3: User Story 2 — Saneamiento y Alineación Documental Completa (Priority: P1)

Objetivo: Sincronizar toda la documentación del repositorio al estado real del proyecto.

- [ ] T009 [US2] Actualizar `README.md`: estado actual post Spec 005/Spec 006, métricas reales de tests (710+ passed), routing de modelos GICS/Cap 2 (ADR-010), y flujos de ejecución.
- [ ] T010 [US2] Actualizar `CHANGELOG.md`: agregar versiones desde v0.9.1 (2026-07-07) hasta el estado actual, detallando los hitos de Fases 10–31 y Specs 001–005.
- [ ] T011 [US2] Actualizar `docs/architecture/ROADMAP.md`: consolidar el cierre de los Specs 001–005 y establecer la hoja de ruta hacia HITL, reconciliación de entidades y solidez sectorial.
- [ ] T012 [US2] Actualizar `docs/architecture/ARQUITECTURA.md`: describir la arquitectura modulárica actual (GenerateInforme en 5 submódulos, Gateway en 4 módulos, ui_query_services, modelo de entidades y membresías sectoriales).
- [ ] T013 [US2] Crear `docs/architecture/ADR-016-modelo-kb-entidades-membresias-gics.md`: formalizar el modelo relacional de entidades, aliases y membresías sectoriales.
- [ ] T014 [US2] Crear `docs/architecture/ADR-017-gateway-multi-provider-resiliente.md`: documentar la integración directa Google Gemini API, OpenRouter y Ollama host.
- [ ] T015 [US2] Actualizar `docs/business-rules/REGLAS_NEGOCIO.md`: alinear RN-003, RN-005 y RN-011/012.
- [ ] T016 [US2] Actualizar o archivar `README_CONTEXTO.md` como documento histórico de Fase 3 para evitar confusión.
- [ ] T017 [US2] Auditar y alinear prompts de `docs/prompts/` con `source_prompts/` y `src/ic/domain/chains/`, garantizando que se preserve el tono propositivo (RN-007 / DT-UI03).
- [ ] T018 [US2] Actualizar `docs/PROXIMA_SESION.md` con el estado real sincronizado.

Checkpoint UU2: Documentación 100% consistente y trazable.

---

## Phase 4: User Story 3 — Deuda Técnica Estructural SoC (<300 Líneas) (Priority: P2)

Objetivo: Modularizar los 4 archivos que violan el límite constitucional.

- [ ] T019 [US3] Modularizar `app.py` (585L) extrayendo las vistas a sub-módulos en `src/ic/presentation/views/` (`view_generate.py`, `view_history.py`) y dejando `app.py` < 300L.
- [ ] T020 [US3] Verificar app.py y vistas refactorizadas con tests de presentación.
- [ ] T021 [US3] Modularizar `src/ic/domain/use_cases/generate_benchmarking.py` (520L) extrayendo la lógica de enriquecimiento web y formateo de fichas a colaboradores <300L módulos.
- [ ] T022 [US2] Modularizar `src/ic/domain/use_cases/generate_n1.py` (499L) separando la orquestación de sub-módulos de los filtros de exclusión alias.
- [ ] T023 [US2] Modularizar `src/ic/data/repositories/_entidad_queries.py` (383L) dividiendo las queries de búsqueda por nombre/alias de las queries de membresías sectoriales.
- [ ] T024 [US3] Actualizar todos los imports en `domain/`, `data/` y `tests/` para los nuevos sub-módulos.
- [ ] T025 [US2] Correr la suite completa de tests para garantizar 0 regresiones.
- [ ] T026 [US3] Verificar que ni un solo archivo en `src/ic/` exceda las 300 líneas.

Checkpoint US3: Cumplimiento 100% de la Constitución y SoC. Cero archivos >300L.

---

## Phase 5: User Story 4 — Alineación y Robustez del Informe de Inteligencia Competitiva (Priority: P2)

Objetivo: Asegurar el alcance del informe frente al patrón Noel/Rúbrica, robustez de fuentes y HITL.

- [ ] T027 [US4] Auditar la integración de las 5 subsecciones de Cap 2 (2.1 Jugadores, 2.2 Grupos, 2.3 Mercado, 2.4 Módulos, 2.5 Brechas) frente a `docs/eval/RUBRICA_CALIDAD.md`.
- [ ] T028 [US4] Formalizar la decisión del elemento visual de Cap 2 (tabla matricial de competitividad enriquecida en `.docx` vs radar chart).
- [ ] T029 [US4] Diseñar la estrategia de enriquecimiento de fuentes para sectores fuera de Alimentos (disminuir párrafos de ausencia RN-001).
- [ ] T030 [US4] Definir e implementar el algoritmo de reconciliación de entidades EMIS/NER por NIT (DT-050b).
- [ ] T031 [US4] Implementar el panel de pre-aprobación y edición de competidores HITL en la UI (Streamlit) usando `ui_query_services.py`.
- [ ] T032 [US4] Conectar el flujo HITL con el pipeline de generación de informes (ADR-015).
- [ ] T033 [US4] Crear tests de integración para el flujo HITL de pre-aprobación.
- [ ] T034 [US4] Generar un informe robusto de prueba (caso Noel SAS o Erco Energía) y evaluarlo con la rúbrica de calidad (>= 11/15 por capítulo).
- [ ] T035 [US4] Cerrar y documentar la versión 1.0.0 del pipeline.

Checkpoint US4: Informes de Inteligencia Competitiva listos para uso ejecutivo con flujo HITL.
