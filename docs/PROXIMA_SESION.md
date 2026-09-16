# Handoff ? pr?xima sesi?n (arranque en chat limpio)

> Estado al cierre 2026-09-16. Rama `006-estabilizacion-alineacion-ic` / `spec-driven-experiment` (Spec 006 completado).
> Copia el bloque "PROMPT DE ARRANQUE" de abajo en un chat nuevo.

## D?nde quedamos
- **Spec 006 (Estabilizaci?n, Alineaci?n de Inteligencia Competitiva y Deuda Estructural) COMPLETADO**:
  - **Decisi?n 1 (Visuales Cap 2)**: Eliminaci?n definitiva de `radar_chart.py`, tests de radar y scripts de extracci?n. El cap?tulo 2 se estandariza en prosa estructurada con mini-fichas y matriz comparativa tabular enriquecida.
  - **Decisi?n 2 (Gateway & LLM Tiers - ADR-017)**: Google Gemini API free tier (`gemini-2.5-flash`: 15 RPM / 1M TPM / 1500 RPD) como tier primario y anal?tico de s?ntesis + fallback resiliente a OpenRouter free tier + embeddings locales Ollama (`bge-m3`).
  - **Decisi?n 3 (HITL Curation)**: Soporte de validaci?n de competidores previo a redacci?n final para descartar empresas no pertinentes.
  - **ADR-016 y ADR-017**: Creados y documentados formalmente en `docs/architecture/`.
  - **Higiene T?cnica y Regla < 300 L?neas (Constituci?n I)**:
    - `src/ic/domain/use_cases/generate_benchmarking.py` (291L) + `_benchmarking_matrix.py` (125L).
    - `src/ic/data/repositories/_entidad_queries.py` (255L) + `_entidad_locales.py` (137L).
    - `src/ic/domain/use_cases/generate_n1.py` (217L) + `_n1_cap2_helpers.py` (190L) + `_n1_chapter_builders.py` (136L).
    - `src/ic/shared/constants/ciiu_gics.py` (175L) + `_ciiu_tables.py` (172L).
    - `src/ic/presentation/app.py` (35L) + `views/` (`view_generar.py`, `view_historial.py`, `view_repositorio.py`, `view_services.py`).
  - **Calidad y Tests**: 100% de los archivos de `src/` estrictamente `< 300 l?neas`. Linter `uv run ruff check .` con 0 errores. Suite de tests unitarios pasando (698 passed, 0 errors).

---

## PROMPT DE ARRANQUE (copiar en chat limpio)

```
ROL: Claude Code / Antigravity, ingeniero senior de InformesAuto.
Proyecto en /home/aagudelo/Test/InformesAuto. Localhost/dev (WSL2).

CONTEXTO (sesi?n previa 2026-09-16, Spec 006 completado):
- Spec 006 (Estabilizaci?n, Alineaci?n de Inteligencia Competitiva y Refactorizaci?n <300L) cerrado:
  * Eliminaci?n completa de radar chart; estandarizaci?n en prosa y tabla matricial.
  * ADR-016 (Modelo KB Entidades y Membres?as GICS) y ADR-017 (Gateway Multi-Provider Resiliente) documentados.
  * Todos los m?dulos de src/ estrictamente < 300 l?neas (Constitution I).
  * UI Streamlit modularizada en src/ic/presentation/views/.
  * 0 errores de ruff, suite completa de tests unitarios verde (698 passed).

SIGUIENTES PASOS:
1. Reconciliaci?n de entidades EMIS-NER por NIT (DT-050b) / enriquecimiento avanzado del KB.
2. Ingesta por lotes optimizada de documentos sectoriales.
```
