# Hallazgos Técnicos — Fase 12

**Fecha:** 2026-07-21
**Rama:** feature/fase12-optimizacion-operacion
**Tests fast:** 168 passed, 2 skipped (6 nuevos)
**Ruff:** 0 errores

---

## Objetivos de la fase

1. **T12.1** — Extraer `_run_n1` a `generate_n1.py` (DT-004)
2. **T12.2** — CostTracker para Ollama: tiempo + tokens reales por respuesta (DT-010)
3. **T12.3** — Historial paginado + filtro por empresa en UI (DT-012)
4. **T12.4** — Exportar página actual del historial a CSV (bonus)

---

## H12-01 — Ollama devuelve tokens reales en `/api/chat` (no-stream)

**Hallazgo:** La respuesta de Ollama con `stream: false` incluye `prompt_eval_count`
(tokens de entrada) y `eval_count` (tokens de salida) además de `total_duration` en
nanosegundos. Esto permite registrar métricas reales sin estimar por tiempo.

**Decisión:** `OllamaGatewayLLM._generate()` ahora parsea los tres campos y los pasa a
`CostTracker.add_ollama_call(modelo, tiempo_s, tokens_in, tokens_out)`. Si un campo no está
presente (edge case), el valor por defecto es 0.

**Impacto:** `metricas_fiabilidad` JSONB en `HistorialInforme` ahora incluye
`tiempo_ollama_total_s` (suma de `total_duration/1e9` de todas las llamadas locales).
Sin cambio de esquema de BD — se almacena en el JSONB existente.

---

## H12-02 — Extracción de `_run_n1` sin import circular

**Problema:** `generate_n1.py` necesita el tipo `_PipelineContext` definido en
`generate_informe.py`. Un import directo crearía un ciclo.

**Solución:** `generate_n1.py` usa `TYPE_CHECKING` de `typing`:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext
```
En runtime Python no ejecuta el bloque `TYPE_CHECKING`, por lo que no hay ciclo.
Los type checkers (mypy/pyright) sí lo ven para validación estática.

**Resultado:** `generate_informe.py` bajó de 402 → 345 líneas. `generate_n1.py` = 67 líneas.

---

## H12-03 — Paginación con `st.session_state` y reset al cambiar filtro

**Problema:** Si el usuario filtra por empresa mientras está en página 3, la página 3
puede no tener resultados del filtro nuevo, dejando UI en blanco sin explicación.

**Solución:** Al detectar cambio de filtro (comparando `_hist_filtro_prev` en session_state),
se resetea `hist_page` a 1 automáticamente. Esto evita el estado inconsistente.

**Código clave:**
```python
if "hist_page" not in st.session_state or st.session_state.get("_hist_filtro_prev") != filtro:
    st.session_state["hist_page"] = 1
```

---

## H12-04 — `build_llm` recibe `cost_tracker` opcional (backwards-compatible)

`build_llm(settings, cost_tracker=None)` — el parámetro es opcional para no romper
llamadas existentes en tests y código externo que no pasa tracker.
`OllamaGatewayLLM.cost_tracker: CostTracker | None = None` requirió `model_config =
{"arbitrary_types_allowed": True}` (mismo patrón que `OpenRouterGatewayLLM`).

---

## Deuda técnica cerrada

| ID | Estado |
|----|--------|
| DT-004 | ✅ Cerrado — `generate_informe.py` 345 L; N1 en módulo propio |
| DT-010 | ✅ Cerrado — tokens + tiempo Ollama en `CallRecord.tiempo_ollama_s` |
| DT-012 | ✅ Cerrado — paginación PAGE_SIZE=10, filtro ILIKE, CSV export |

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/ic/domain/use_cases/generate_n1.py` | Creado — lógica N1 paralelo |
| `src/ic/domain/use_cases/generate_informe.py` | _run_n1 delegador + tiempo_ollama en métricas |
| `src/ic/infrastructure/llm/gateway.py` | CallRecord + CostTracker + OllamaGatewayLLM |
| `src/ic/data/repositories/informe_repo.py` | offset + empresa_filter en list_recientes |
| `src/ic/presentation/app.py` | Paginación + filtro + CSV en tab Historial |
| `tests/test_llm.py` | 4 nuevos tests CostTracker + OllamaGatewayLLM mock |
| `tests/test_informe_repo.py` | 2 nuevos tests offset + ILIKE |
