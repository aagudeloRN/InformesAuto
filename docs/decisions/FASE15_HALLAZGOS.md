# FASE 15 — Hallazgos: Resiliencia y Costo

**Fecha:** 2026-07-22 · **Branch:** `feature/fase15-resiliencia-costo`

---

## 1. Objetivo

Reducir latencia y costo del pipeline y hacerlo resiliente a rate-limits, usando el
harness de evaluación (T14.1) como árbitro de evidencia. Se construye sobre las
decisiones cerradas de Fase 14 (ADR-013 persistencia web, MMR desactivado, chunk 1000/200).

---

## 2. T15.1 — Estrategia de embedding en lote

### Diagnóstico (de Fase 14)

El embedding con `nomic-embed-text` domina el **~99% de la latencia** (~1300 ms por
consulta embed+SQL vs 15 ms SQL puro). Causa: `keep_alive: 0` recarga el modelo
completo en cada llamada. En un harness de 25 consultas esto supone ~32.5 s de carga
de modelo vs ~375 ms de SQL puro.

### Solución implementada

**`Embedder.batch_mode()`**: context manager que activa un `keep_alive` positivo durante
el bloque y descarga el modelo al salir (`keep_alive: 0`).

```python
with embedder.batch_mode():
    # nomic-embed-text permanece en VRAM durante el bloque
    resultados = harness.run_all_queries(embedder)
# Al salir: keep_alive:0 → descarga de VRAM (ADR-006 cumplido)
```

Parámetros en `.env` (nunca hardcodeados):
- `EMBEDDER_KEEP_ALIVE=0` — default seguro (política ADR-006)
- `EMBEDDER_BATCH_KEEP_ALIVE=5m` — tiempo de lote

El harness acepta `--warm` para medir la diferencia:
```bash
uv run python scripts/eval_retrieval.py --bench              # cold (default)
uv run python scripts/eval_retrieval.py --bench --warm       # warm (batch_mode)
```

### Reducción de latencia esperada (estimación teórica)

| Modo | 1ª consulta | 2ª–25ª consulta | Total 25 consultas |
|------|------------|-----------------|---------------------|
| Cold (default, keep_alive:0) | ~1300 ms | ~1300 ms cada una | ~32.5 s |
| **Warm (batch_mode, 5m)** | ~1300 ms | **~15–30 ms** (SQL puro) | **~1.7–2.0 s** |

> **Nota (Fase 16):** La medición real con `--bench --warm` no pudo ejecutarse en la sesión
> de Fase 16 (Ollama y modelos no disponibles). Los números anteriores siguen siendo
> estimaciones teóricas. Para obtener datos reales, ejecutar con Ollama activo:
> ```bash
> uv run python scripts/eval_retrieval.py --bench              # cold
> uv run python scripts/eval_retrieval.py --bench --warm       # warm
> ```
> y actualizar esta tabla con los resultados.

La reducción es estructuralmente segura: el modelo se descarga al salir del bloque.

**Reconciliación con ADR-006:** el lote es *explícito y acotado* (un context manager
nombrado), no el default del sistema. `keep_alive:0` sigue siendo el comportamiento
fuera del bloque.

---

## 3. T15.2 — Caché de retrieval web/OpenAlex

### Problema

Cada corrida del pipeline llamaba a `WebConnector.search()` y `OpenAlexConnector.search()`
desde cero, gastando créditos Tavily y añadiendo ~500–2000 ms de latencia de red. Con la
persistencia web "solo lo citado" (ADR-013), tiene aún más sentido cachear la *búsqueda*
(no el chunk: eso lo gestiona ADR-013).

### Solución implementada

**`CachedWebConnector` / `CachedOpenAlexConnector`**: wrappers inyectables que:
1. Calculan `sha256(connector:max_results:query)` como clave.
2. Consultan `retrieval_cache` (esquema `informes_ic`): si hay entrada fresca (no expirada), devuelven el payload sin llamar a la red.
3. En miss: llaman al connector real y almacenan la respuesta con TTL.

```
informes_ic.retrieval_cache
├── id (UUID)
├── connector ("web" | "openalex")
├── query_hash (SHA-256, UNIQUE + INDEX)
├── query (TEXT)
├── payload (JSONB)
├── created_at
└── expires_at
```

`ensure_retrieval_cache_table(engine)` crea la tabla si no existe (idempotente).
`RETRIEVAL_CACHE_TTL_HOURS=168` (7 días) en `.env`.

`force_ddg=True` bypasa la caché (no consulta ni guarda) — útil en tests y debugging.

---

## 4. T15.3 — Resiliencia free-tier (DT-021)

### Problema original

OpenRouter puede indicar rate-limit de dos formas:
1. **HTTP 429** (sí dispara `raise_for_status`) — detectado por tenacity.
2. **HTTP 200 + `{"error": {...}}` en el body** con texto `"ResourceExhausted 32/32"` — **no** dispara `raise_for_status`. El gateway generaba `RuntimeError` genérico y tenacity reintentaba el **mismo** modelo indefinidamente.

Resultado: ante rate-limit persistente del tier free, el pipeline abortaba en lugar de caer a un tier alternativo.

### Solución implementada

**`is_rate_limit_error(exc)`**: detector de rate-limit (HTTP 429 + patrones "rate limit",
"resourceexhausted", "quota", "too many requests" en el texto del error).

**`ResilientChatModel`**: wrapper `BaseChatModel` con lista ordenada de tiers:
```
free → free_alt → synth → paid
```
- Ante rate-limit del tier actual: log de warning + caída al siguiente.
- Ante error no-rate-limit (5xx, timeout): propagación inmediata (no se intenta fallback).
- Si todos los tiers lanzan rate-limit: re-raise del último error.

**`build_resilient_api_llm(settings, tiers=None)`**: construye el modelo resiliente;
omite silenciosamente los tiers sin modelo configurado en `.env`.

**Timeouts por tier** en `.env`:
- `LLM_API_TIMEOUT_FREE=180`
- `LLM_API_TIMEOUT_FREE_ALT=180`
- `LLM_API_TIMEOUT_SYNTH=180`
- `LLM_API_TIMEOUT_PAID=120`

### Verificación de resiliencia

Test `test_resilient_falls_to_second_tier_on_rate_limit`: simula 429 en tier 1 → el
modelo cae a tier 2 y devuelve contenido (no aborta). Cascada de 3 tiers también probada.

---

## 5. T15.4 — Gate de latencia/calidad

**`scripts/eval_gate.py`**: compara un snapshot del harness contra un presupuesto
configurable. Exit≠0 ante cualquier violación.

**`docs/decisions/fase15_budget.json`** (presupuesto de referencia):
```json
{
  "max_latency_ms": 3000,
  "max_latency_sql_ms": 50,
  "max_cost_usd": 0.0,
  "min_precision": 0.95,
  "max_contamination": 0.05,
  "min_hit_rate": 0.95
}
```

El snapshot de Fase 14 (`fase14_final_filtered.json`, SQL ~15 ms, precision 1.0) pasa
el gate correctamente. El gate detecta regresiones inyectadas en todos los campos.

Uso en CI / pre-merge:
```bash
uv run python scripts/eval_retrieval.py --bench-sql --save /tmp/snap.json
uv run python scripts/eval_gate.py --snapshot /tmp/snap.json
```

---

## 6. T15.5 — Higiene

- **`/api/generate` vs `/api/chat`:** confirmado que el pipeline usa `/api/embeddings`
  (embedder) y `/api/chat` (OllamaGatewayLLM), **nunca** `/api/generate` (API generate
  de Ollama, más antigua). No hay deuda aquí.
- **`purge_unused_web_backlog(limit_ids=[])`**: acepta lista de IDs para restringir la
  purga a chunks concretos en tests, sin afectar el estado global de la BD.
- **ADR-006 y keep_alive**: reconciliado. `batch_mode()` descarga el modelo al salir
  → el lote es explícito y acotado. El default del sistema sigue siendo `keep_alive:0`.

---

## 7. Retos encontrados

1. **Pydantic valida `tiers: list[OpenRouterGatewayLLM]` estrictamente**: los mocks no
   pasan la validación. Solución: anotar como `list[Any]` con comentario de tipo real.
2. **`Base.metadata.create_all(engine)` arrastra FK en SQLite**: para los tests de caché
   no se puede usar la BD en memoria con el Base compartido (otras tablas tienen FK no
   resolubles en SQLite). Solución: mocks directos del repositorio en lugar de BD en
   memoria.
3. **Clasificador Bash intermitente**: el proceso de revisión de seguridad de bash estuvo
   caído durante parte de la sesión. Se compensó con lectura directa de archivos.

---

## 8. Recomendaciones / follow-ups

- **T15.1 medición real**: correr `--bench --warm` con Ollama activo y añadir la tabla
  antes/después a este documento. Los números actuales son estimados teóricos.
- **Cablear `CachedConnector` en el pipeline**: `generate_n1.py` y `generate_informe.py`
  construyen `WebConnector` y `OpenAlexConnector` directos. Para activar la caché en
  producción, reemplazarlos por `CachedWebConnector`/`CachedOpenAlexConnector` (se
  necesita la sesión de BD en el contexto del pipeline — ya disponible como `SessionLocal`).
- **Cablear `ResilientChatModel`**: `generate_informe._setup_infra` construye los tiers
  individualmente. Reemplazar con `build_resilient_api_llm(settings, tracker)` para
  activar el fallback automático en el pipeline E2E.
- **Métricas de hit-rate de caché**: añadir contador de hits/misses en `CachedConnector`
  y emitirlos en el log de informe para medir el ahorro real en producción.
- **Fase 16**: DT-019 (radar con datos reales del LLM) + DT-024 (estilo Normal del .docx).
