# Tasks: 006 ? Estabilizaci?n, Alineaci?n Documental y Definici?n de Alcance de Inteligencia Competitiva

**Branch**: `006-estabilizacion-alineacion-ic`
**Spec**: [/specs/006-estabilizacion-alineacion-ic/spec.md](spec.md)
**Plan**: [/specs/006-estabilizacion-alineacion-ic/plan.md](plan.md)
**Fecha**: 2026-09-16
**Estado**: COMPLETADO (Convergencia Validada)

---

## Phase 1: Setup & Baseline

**Purpose**: Verificaci?n inicial de linter, tests y medici?n de l?neas.

- [x] T001 Registrar medici?n baseline de tests failing (5), errores de linter (8) y archivos >300L en `docs/decisions/FASE31_006_AUDIT_BASELINE.md`
- [x] T002 [P] Verificar configuraci?n local de `ruff` y `pytest` sobre `006-estabilizacion-alineacion-ic`

---

## Phase 2: User Story 1 ? Higiene T?cnica y Estabilizaci?n Inmediata (Priority: P1)

Objetivo: Reparar todos los tests unitarios fallidos y errores de linter dejados por Spec 005.

- [x] T003 [US1] Refactorizar `model=settings.llm_local_analytic_model` en `build_llm(s)` de `src/ic/infrastructure/llm/gateway.py` (eliminar `settings.ollama_model`).
- [x] T004 [US1] Corregir la firma y orden de par?metros en `_provider_base_and_key` en `ic.infrastructure.llm.gateway` y alinearlos con `tests/test_gateway_robustez.py`.
- [x] T005 [US1] Corregir el acceso a `llm_api_synth_model` en `build_api_llm(s, tier="synth")` de `src/ic/infrastructure/llm/gateway.py` (eliminar `settings.gemini_synth_model`).
- [x] T006 [US1] Alinear los argumentos de `build_resilient_api_llm` (`fallback`, tiers) entre `gateway.py`, test_fase15_resilience.py y test_gateway_robustez.py.
- [x] T007 [US1] Formatear y ajustar l?neas de comentarios/constantes en los 5 scripts de `scripts/` (`backfill_entidad_sectores.py`, `build_emis_index.py`, `seed_empresas_colombia.py`, `seed_informes_manuales.py`, `seed_startia.py`) para cumplir E501 (<= 100 chars).
- [x] T008 [US1] Ejecutar y validar que `uv run ruff check` devuelve 0 errores y `uv run pytest -m "not slow and not integration"` devuelve >= 698 passed (100% verde).

Checkpoint US1: Suite diagn?stica y codebase 100% en verde.

---

## Phase 3: User Story 2 ? Saneamiento y Alineaci?n Documental Completa (Priority: P1)

Objetivo: Sincronizar toda la documentaci?n del repositorio al estado real del proyecto.

- [x] T009 [US2] Actualizar `README.md`: estado actual post Spec 005/Spec 006, m?tricas reales de tests (698+ passed), routing de modelos GICS/Cap 2 (ADR-010), y flujos de ejecuci?n.
- [x] T010 [US2] Actualizar `CHANGELOG.md`: agregar versiones detallando los hitos de Fases 10?31 y Specs 001?006.
- [x] T011 [US2] Actualizar `docs/architecture/ROADMAP.md` y `docs/PROXIMA_SESION.md`: consolidar el cierre de Specs 001?006.
- [x] T012 [US2] Formalizar la arquitectura modular actual (GenerateInforme, Gateway, ui_query_services, modelo de entidades y membres?as sectoriales).
- [x] T013 [US2] Crear `docs/architecture/ADR-016-modelo-kb-entidades-membresias-gics.md`: formalizar el modelo relacional de entidades, aliases y membres?as sectoriales.
- [x] T014 [US2] Crear `docs/architecture/ADR-017-gateway-multi-provider-resiliente.md`: documentar la integraci?n directa Google Gemini API, OpenRouter y Ollama host.
- [x] T015 [US2] Actualizar `docs/PROXIMA_SESION.md` con el estado real sincronizado.

Checkpoint US2: Documentaci?n 100% consistente y trazable.

---

## Phase 4: User Story 3 ? Deuda T?cnica Estructural SoC (<300 L?neas) (Priority: P2)

Objetivo: Modularizar todos los archivos que violan el l?mite constitucional.

- [x] T019 [US3] Modularizar `app.py` (35L) extrayendo las vistas a subm?dulos en `src/ic/presentation/views/` (`view_generar.py`, `view_historial.py`, `view_repositorio.py`, `view_services.py`).
- [x] T020 [US3] Verificar app.py y vistas refactorizadas con tests de presentaci?n y linter.
- [x] T021 [US3] Modularizar `src/ic/domain/use_cases/generate_benchmarking.py` (291L) extrayendo helpers y cache sectorial a `_benchmarking_matrix.py` (125L).
- [x] T022 [US3] Modularizar `src/ic/domain/use_cases/generate_n1.py` (217L) separando la orquestaci?n en `_n1_cap2_helpers.py` (190L) y `_n1_chapter_builders.py` (136L).
- [x] T023 [US3] Modularizar `src/ic/data/repositories/_entidad_queries.py` (255L) extrayendo las consultas de jugadores locales a `_entidad_locales.py` (137L).
- [x] T024 [US3] Modularizar `src/ic/shared/constants/ciiu_gics.py` (175L) extrayendo tablas est?ticas a `_ciiu_tables.py` (172L).
- [x] T025 [US3] Correr la suite completa de tests para garantizar 0 regresiones.
- [x] T026 [US3] Verificar que ni un solo archivo en `src/` exceda las 300 l?neas (M?ximo archivo actual: 297L).

Checkpoint US3: Cumplimiento 100% de la Constituci?n y SoC. Cero archivos >300L.

---

## Phase 5: User Story 4 ? Decisiones de Negocio y Alcance de Inteligencia Competitiva

Objetivo: Asegurar el alcance del informe frente a decisiones estrat?gicas validadas con el usuario.

- [x] T027 [US4] Decisi?n 1: Eliminar totalmente `radar_chart.py`, tests de radar y scripts de hitrate. Estandarizar Cap?tulo 2 en prosa con mini-fichas y tabla matricial comparativa en `.docx`.
- [x] T028 [US4] Decisi?n 2: Implementar Gateway multi-tier Gemini 2.5 Flash Free + OpenRouter fallback con pol?tica de costes acotados (ADR-017).
- [x] T029 [US4] Decisi?n 3: Integrar soporte de validaci?n/curaci?n humana previa de competidores en Streamlit UI para descartar entidades irrelevantes.
