# Fase 31 — Audit Baseline Spec 006

**Fecha**: 2026-09-16
**Contexto**: Baseline diagnóstica previa a la ejecución de Spec 006 (Estabilización, Alineación Documental y Alcance IC).

## 1. Estado Inicial de Pruebas Unitarias
- Suite ejecutada: `uv run pytest -m "not slow and not integration"`
- Resultado: **5 failed, 701 passed, 2 skipped, 17 deselected** (Total 706 tests).
- Tests fallidos identificados:
  1. `tests/test_cost_tracker.py::test_build_llm_returns_ollama_gateway`: `AttributeError: 'Settings' object has no attribute 'ollama_model'`
  2. `tests/test_gateway_robustez.py::test_build_api_llm_synth_usa_gemini_y_max_tokens`: `AttributeError: 'Settings' object has no attribute 'gemini_synth_model'`
  3. `tests/test_gateway_robustez.py::test_provider_resolver_gemini_vs_openrouter`: Parámetros invertidos en `_provider_base_and_key`
  4. `tests/test_fase15_resilience.py::test_build_resilient_api_llm_skips_unconfigured_tiers`: Argumento posicional `fallback` faltante
  5. `tests/test_gateway_robustez.py::test_build_resilient_anexa_el_fallback`: Argumento `tiers` inesperado

## 2. Estado Inicial de Linter (Ruff)
- Comando: `uv run ruff check`
- Resultado: **8 errores de formato E501 (Line too long > 100 chars)** en `scripts/`:
  - `scripts/backfill_entidad_sectores.py:5`
  - `scripts/build_emis_index.py:8`
  - `scripts/seed_empresas_colombia.py:11`
  - `scripts/seed_empresas_colombia.py:51`
  - `scripts/seed_informes_manuales.py:4`
  - `scripts/seed_informes_manuales.py:88`
  - `scripts/seed_informes_manuales.py:96`
  - `scripts/seed_startia.py:5`

## 3. Estado de Archivos >300 Líneas (Violación Constitucional SoC)
- `src/ic/presentation/app.py`: **585 líneas**
- `src/ic/domain/use_cases/generate_benchmarking.py`: **520 líneas**
- `src/ic/domain/use_cases/generate_n1.py`: **499 líneas**
- `src/ic/data/repositories/_entidad_queries.py`: **383 líneas**

## 4. Decisiones de Producto Ratificadas
1. **Radar Chart**: Eliminación definitiva del módulo `radar_chart.py` y simplificación de visualización en Cap 2 a fichas de prosa + tabla matricial comparativa.
2. **Modelos & Routing (ADR-017)**: Google Gemini ARI directa (`gemini-2.5-flash`) como primario de alta capacidad (15 RPM / 1500 RPD free tier en AI Studio), OpenRouter free como backup, Ollama `nomic-embed-text` local para embeddings.
3. **Flujo HITL**: Doble instancia de validación humana en UI Streamlit (pre-aprobación y filtrado de competidores clave antes de N1/N2 + panel de auditoría post-generación).
