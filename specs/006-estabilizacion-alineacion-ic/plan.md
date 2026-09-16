# Implementation Plan: 006    Estabilización, Alineación Documental y Definición de Alcance de Inteligencia Competitiva

**Branch**: `006-estabilizacion-alineacion-ic` | **Date**: 2026-09-16 | **Spec**: [spec.md](spec.md) | **Tasks**: [tasks.md](tasks.md)

*Input**: Feature specification from `/specs/006-estabilizacion-alineacion-ic/spec.md`

## Summary

Ejecutar la estabilización técnica inmediata del sistema (reparación de 5 tests unitarios rotos y 8 errores de linter ruff), sanear y sincronizar toda la documentación viva del proyecto con el estado real (Post Spec 005), saldar la deuda técnica estructural reduciendo los 4 archivos que superan las 300 líneas a módulos cohesivos (<300L), y consolidar el alcance y robustez del informe de inteligencia competitiva (cobertura Cap 2, reconciliación de entidades y flujo HITL en UI).

## Technical Context

**Language/Version**: Python 3.12+ gestionado con `uv`
**Primary Dependencies**: LangChain (LCEL), Pydantic v2 (pydantic-settings), SQLAlchemy 2.0 (async/sync), Streamlit (UI), python-docx (rendering), httpx (Ollama & OpenRouter API client), spacy (NER)
**Storage**: PostgreSQL 16 con extensión `pgvector` (schema `informes_ic` en puerto 5434)
**AI / Inference**: Ollama en host (`nomic-embed-text` local en :11434), Google Gemini ARI directa (`gemini-2.5-flash`), OpenRouter (free tiers y fallback)
**Testing**: `pytest` (markers: `not slow`, `not integration`, `slow`, `integration`), `ruff` (linter y formatter con límite 100 caracteres)
**Target Platform**: Linux WSL2 (Ubuntu) / Servidor Docker on-premise (`docker-compose.server.yml`)

## Proposed Architectural Changes

### 1. Gateway & Settings Alignment (US1)
- Corregir el mapeo de atributos en `src/ic/infrastructure/llm/gateway.py`:
  - `settings.lm_local_analytic_model` en lugar de `settings.ollama_model`.
  - `settings.llm_api_synth_model` en lugar de `settings.gemini_synth_model`.
- Alinear firmas en `_provider_base_and_key(provider, settings, model)` y llamadas en tests.
- Formatear líneas >100 caracteres en `scripts/`.

### 2. Documentation Architecture Sync (US2)
- Actualizar `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `ARQUITECTURA.md`, `REGLAS_NEGOCIO.md` y `PROXIMA_SESION.md`.
- Redactar `ADR-016` (Modelo de KB de Entidades y Membresías GICS) y `ADR-017` (Multi-Provider Resilient LLM Gateway).
- Sincronizar catálogo de prompts asegurando cumplimiento de tono propositivo (DT-UI03).

### 3. Structural SoC Refactoring (<300 Lines) (US3)
- Dividir `src/ic/presentation/app.py` (585L) en `src/ic/presentation/views/` (`view_generate.py`, `view_history.py`, `view_audit.py`).
- Dividir `src/ic/domain/use_cases/generate_benchmarking.py` (520L) extrayendo formateo y web enrichment.
- Dividir `src/ic/domain/use_cases/generate_n1.py` (499L) separando orquestación de sub-módulos y alias exclusions.
- Dividir `src/ic/data/repositories/_entidad_queries.py` (383L) separando entity lookup de membership filtering.

### 4. Product Scope & HITL Workflow (US4)
- Formalizar subsecciones 2.1 a 2.5 de Cap 2 frente a `RUBRICA_CALIDAD.md`.
- Reconciliación de entidades EMIS/NER por NIT (`DT-050b`).
- Pre-aprobación y edición humana de competidores en Streamlit antes de N1/N2.

## Verification Plan

### Automated Tests
- `uv run ruff check`: 0 errores.
- `uv run pytest -m "not slow and not integration"`: >= 706 unit tests passing (100% verde).
- `uv run pytest -m "integration"`: suite de integración E2E pasando.
- Script de conteo de líneas: 0 archivos >300L en `src/ic/`.

### Manual & Qualitative Verification
- Generación de informe completo para caso de prueba (Noel SAS o Erco Energía).
- Evaluación del informe `.docx` contra la rúbrica de calidad ejecutiva (`RUBRICA_CALIDAD.md` >= 11/15 por capítulo).
