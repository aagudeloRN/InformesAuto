# ADR-010: Routing API-primero para GICS y Cap 2 por restricción de VRAM en WSL2

**Estado:** Aceptado | **Fecha:** 2026-07-07
**Decisores:** Equipo del sistema de informes de inteligencia competitiva
**Modifica:** ADR-002 (routing local-primero) — parcialmente, para N0/GICS y N1/Cap 2
**Reemplazado por:** —

## Contexto

ADR-002 estableció una estrategia "local-primero": el LLM generativo en Ollama tiene
prioridad, y OpenRouter se usa como escalado selectivo cuando el local no supera el
umbral de calidad.

Este diseño asumía (ADR-002, sección Contexto) que el entorno disponía de una GPU RTX
con 8 GB de VRAM dedicada, separada de la RAM principal del sistema.

El entorno real de desarrollo es **WSL2 en equipo corporativo Windows**: no hay GPU
dedicada con VRAM propia. Ollama usa RAM del sistema como VRAM. Con 9.7 GB de RAM total
y 8 GB disponibles para Ollama:

- `nomic-embed-text` requiere ~0.3 GB
- `qwen3:8b` requiere ~5.2 GB
- Overlap temporal durante la ingesta de PDF: **5.5 GB** simultáneos → OOM

Durante la generación de un informe completo, `_run_n1()` ejecuta Cap 2 (con `qwen3:8b`)
en paralelo con la ingesta del PDF de Convergencia (con `nomic-embed-text`), y también
concurre con uso del sistema operativo y otros procesos. El OOM es determinista y
reproducible.

## Decisión

Se invierte la prioridad de routing para **N0/GICS** y **N1/Cap 2 (Benchmarking)**:

- **Antes (ADR-002):** Ollama local → fallback API si no supera umbral de calidad
- **Ahora (ADR-010):** OpenRouter API free → fallback Ollama si no hay `OPENROUTER_API_KEY`

Implementación en `generate_informe.py`:
```python
# GICS — línea 145
ctx.gics = ClassifyGICS(chain=build_chain_02(ctx.api_llm or ctx.llm)).execute(...)

# Benchmarking — línea 170
GenerateBenchmarking(chain=build_chain_03(ctx.api_llm or ctx.llm), ...)
```

El patrón `api_llm or llm` garantiza compatibilidad total: sin `OPENROUTER_API_KEY`,
`api_llm` es `None` y se usa Ollama (comportamiento ADR-002).

Los embeddings (`nomic-embed-text`) permanecen **siempre en Ollama** — 0.3 GB no
representa ningún riesgo de OOM.

### Medidas complementarias

- `pdf_ingestor.py`: llama `_release_vram(ollama_url, llm_local_analytic_model)` al
  inicio de `ingest_batched()` para desalojar `qwen3:8b` incluso en flujos donde se
  invoca el ingestor directamente (script manual, pipeline).
- `embedder.py`: timeout 30 s → 60 s + reintento en `httpx.TimeoutException` para
  absorber latencia de carga del modelo cuando Ollama sí tiene que cargarlo.

## Consecuencias

### Positivas
- Elimina OOM determinista en WSL2 8 GB RAM.
- GICS y Cap 2 con modelos más grandes (Nemotron 120B+) producen mejor calidad
  que `qwen3:8b` local.
- Costo: $0 (tier free de OpenRouter).
- Retrocompatible: sin `OPENROUTER_API_KEY` el sistema funciona igual que antes.

### Negativas / costos asumidos
- GICS y Cap 2 dependen de disponibilidad de OpenRouter cuando la clave está
  configurada. Fallo de red → fallback a Ollama (aceptable).
- El principio "local-primero" de ADR-002 queda parcialmente invalidado para
  estos dos capítulos. Se acepta por la restricción de hardware del entorno de desarrollo.
- Si el entorno migra a una máquina con GPU VRAM dedicada, se recomienda revertir
  al patrón de ADR-002 cambiando solo `.env` (el código ya soporta ambos modos).

## Alternativas consideradas

- **Reducir `qwen3:8b` a un modelo más pequeño (3B-4B):** Reduce calidad analítica
  sin resolver el problema de raíz; descartado.
- **Swap en disco para Ollama:** Introduce latencia de swap (~10× más lento); descartado.
- **Serializar Cap 2 y el ingestor PDF (no paralelizar):** Evita el overlap pero
  aumenta el tiempo total; descartado porque la solución API es más limpia.
- **`_release_vram` antes de ingest (sin cambiar routing):** Mitiga pero no elimina
  el problema si hay otras cargas concurrentes; adoptado como medida complementaria,
  no como solución única.
