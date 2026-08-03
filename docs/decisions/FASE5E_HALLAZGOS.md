# Hallazgos Fase 5E — Cap 5 Convergencia + Cap 6 Accionables + Resumen Ejecutivo

## Resumen

Fase 5E cierra el ciclo analítico del DAG de capítulos, añadiendo los tres
niveles de síntesis que faltaban:

- **Cap 5 Convergencia** (N2, tier synth): cruza Caps 2/3/4 + PDF territorial.
- **Cap 6 Accionables** (N2, tier free): 6 accionables estratégicos cruzados.
- **Resumen Ejecutivo** (N3, tier synth): síntesis C-Level del informe completo.
- **Ingesta automática** del PDF de convergencia local antes de Cap 5.

---

## Decisiones de diseño

### Cap 5 — dos queries RAG diferenciadas

Cap 5 realiza dos búsquedas separadas en pgvector:
1. `"{sector} {empresa} tendencias ecosistema benchmarking estrategia"` — recupera
   outputs de Caps 2/3/4 ya indexados.
2. `"{sector} {empresa} sostenibilidad transformación digital desarrollo económico Medellín"`
   — recupera chunks del PDF de convergencia territorial.

Ambas queries alimentan variables distintas del chain (`retrieval_caps_anteriores` y
`retrieval_convergencia_territorial`), lo que permite al LLM distinguir el origen de
cada fuente.

La deduplicación por `fuente_url` evita que el mismo chunk cuente doble en el
total de `n_chunks_usados` ni en la lista `chunks_usados`.

### Cap 6 — sin web_connector

Cap 6 no realiza búsquedas web nuevas. Depende enteramente del contenido ya
indexado en pgvector por los capítulos N1 y Cap 5. Esto reduce el tiempo de
ejecución y el costo (Caps N1 ya agotan las búsquedas relevantes). El constructor
solo recibe `chain` y `store`.

`_MIN_CHUNKS = 6` (mayor que N1 = 3) asegura que haya suficiente contexto cruzado
antes de generar los accionables.

### Resumen Ejecutivo — síntesis directa sin retrieval

El Resumen Ejecutivo (N3) no hace retrieval. Recibe directamente los textos
generados de todos los capítulos como `cap_textos: dict[str, str]`. Se omiten
automáticamente las entradas con texto vacío o whitespace.

Constructor mínimo: solo `chain`. Siempre `retrieval_suficiente = True`.

### PDF auto-ingest en run_pilot.py

El script detecta `InformeConvergenciaLocal2026V3RvADAA.pdf` en la raíz del
proyecto. Si existe, llama a `ingest_pdf()` de `scripts/ingest_pdf.py` antes de
Cap 5. La función tiene detección de duplicados por SHA-256, por lo que en
ejecuciones sucesivas el ingest es un no-op rápido (retorna 0 chunks).

Si el PDF no existe, Cap 5 continúa con RAG exclusivamente sobre web. La
política de datos ausentes (RN-001) cubre el caso de retrieval < 5 chunks.

### `api_llm_synth` en el pipeline

Se añade un tercer tier LLM al pipeline:
- `api_llm` (free) — Caps 3, 4, 6
- `api_llm_synth` (synth) — Caps 5, Resumen Ejecutivo
- `llm` (local Ollama) — Cap 1 fallback, GICS

---

## Archivos añadidos / modificados

| Tipo | Archivo |
|------|---------|
| Nuevo | `src/ic/domain/chains/chain_06_convergencia.py` |
| Nuevo | `src/ic/domain/chains/chain_07_accionables.py` |
| Nuevo | `src/ic/domain/chains/chain_08_resumen_ejecutivo.py` |
| Nuevo | `src/ic/domain/use_cases/generate_convergencia.py` |
| Nuevo | `src/ic/domain/use_cases/generate_accionables.py` |
| Nuevo | `src/ic/domain/use_cases/generate_resumen_ejecutivo.py` |
| Nuevo | `tests/test_convergencia.py` (9 tests) |
| Nuevo | `tests/test_accionables.py` (7 tests) |
| Nuevo | `tests/test_resumen_ejecutivo.py` (6 tests) |
| Modificado | `src/ic/shared/types.py` (+3 DTOs, +3 campos en InformePiloto) |
| Modificado | `src/ic/domain/assembler.py` (+Cap 5, Cap 6, Resumen; -placeholder) |
| Modificado | `scripts/run_pilot.py` (TOTAL_PASOS 7→10; +3 pasos; +api_llm_synth) |

---

## Correctivo de estabilidad — crasheos OOM (post-implementación)

> Ver decisión completa en `docs/architecture/ADR-007-gestion-memoria-wsl2-tests.md`.

Durante la ejecución de tests al finalizar Fase 5E se produjeron **dos crasheos por agotamiento
de RAM** en el entorno WSL2 (8 GB):

### Crash 1 — OpenBLAS multithreading en pytest

`numpy`/`langchain-community` lanzan un pool de hilos OpenBLAS al importarse. Sin la variable
`OPENBLAS_NUM_THREADS` fijada, el número de hilos iguala las CPUs lógicas del host Windows
(8–16), multiplicando el consumo de RAM durante la suite.

**Fix aplicado:** `OPENBLAS_NUM_THREADS=1` + `OMP_NUM_THREADS=1` en `[tool.pytest.ini_options]`
vía plugin `pytest-env` (dev dependency). Ambas variables ahora se inyectan antes de cualquier
import del código bajo test.

### Crash 2 — Compilador Rust (hatchling) con Ollama cargado

Al ejecutar `uv add --dev pytest-env` con `qwen3:8b` en RAM (~4 GB), el compilador de Rust
lanzado por hatchling agotó la memoria restante.

**Fix aplicado:** `keep_alive: 0` ya estaba en embedder y gateway (ADR-002, Fase 5C).
El crash fue aislado. Procedimiento operativo documentado en ADR-007 D3: verificar RAM libre
(`free -m`) antes de operaciones de compilación.

### Corrección adicional

`test_pilot_end_to_end_noel` no tenía `@pytest.mark.slow` a pesar de llamar al embedder Ollama
real. Añadido en esta sesión. La suite rápida (`-m "not slow"`) ahora excluye correctamente los
8 tests de integración con servicios externos.

---

## Métricas de calidad

- Tests antes de Fase 5E: 64 passed, 2 skipped
- Tests después Fase 5E (commit d1f8866): 86 passed, 2 skipped (+22 nuevos)
- Tests suite rápida (post correctivo 0.5.5): 78 passed, 2 skipped, 8 deselected (slow)
- Cobertura domain/: mantenida >80%

---

## Próxima fase: 5F (opcional)

- Párrafos introductorios por capítulo (N3, tier free)
- Parallelización de N1 caps (asyncio o ThreadPoolExecutor)
- Tracking de costo real por LLM call en el resumen de ejecución
