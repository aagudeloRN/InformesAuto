# ADR-014 — Caché de retrieval y keep_alive de lote para el embedder

**Fecha:** 2026-07-22
**Estado:** Aprobado
**Fase:** 15 (T15.1, T15.2)
**Relacionado con:** ADR-006 (presupuesto/VRAM), ADR-013 (persistencia web solo-citado)

---

## Contexto

Fase 14 identificó dos palancas de optimización:

1. **Latencia de embedding**: `nomic-embed-text` con `keep_alive:0` recarga el modelo en
   cada llamada (~1300 ms/consulta). El SQL puro es ~15 ms. En un harness de 25 consultas
   o una re-ingesta del corpus, el modelo se recarga decenas de veces (costo: tiempo × N).

2. **Re-consulta de fuentes externas**: web y OpenAlex se consultan en cada corrida desde
   cero, gastando créditos Tavily y añadiendo latencia de red, aunque la misma query se
   haya ejecutado días antes con el mismo resultado.

---

## Decisiones

### 1. keep_alive de lote (`Embedder.batch_mode()`)

Se introduce un **context manager explícito** que activa un keep_alive positivo durante
el bloque y descarga el modelo al salir:

```python
with embedder.batch_mode():
    # keep_alive = EMBEDDER_BATCH_KEEP_ALIVE (default "5m")
    ...
# Al salir: llamada de descarga con keep_alive=0 (best-effort)
```

**Parametrización en `.env`** (nunca hardcodeada en código):
- `EMBEDDER_KEEP_ALIVE=0` — default seguro (política ADR-006: liberar VRAM inmediatamente)
- `EMBEDDER_BATCH_KEEP_ALIVE=5m` — tiempo de retención en modo lote

**Reconciliación con ADR-006:** el lote es *explícito y acotado*. El modo normal del
sistema sigue siendo `keep_alive:0`. La descarga al salir del bloque es best-effort
(fallo silencioso si Ollama no responde), lo que no compromete la corrección (Ollama
descarga el modelo por inactividad si no llegan más peticiones).

**Uso**: re-ingesta de corpus, harness de evaluación (`--warm`), futuro batch N1.
**No usar** en el path normal de una consulta individual de retrieval.

### 2. Caché de retrieval web/OpenAlex

Se introduce la tabla `informes_ic.retrieval_cache` con ciclo de vida TTL:

```
connector  │ query_hash   │ payload (JSONB) │ expires_at
-----------│--------------│-----------------│-----------
"web"      │ sha256(...)  │ [WebResult...]  │ now + TTL
"openalex" │ sha256(...)  │ [WebResult...]  │ now + TTL
```

**Clave de caché**: `sha256(connector + ":" + str(max_results) + ":" + query)`.
Incluye `max_results` para distinguir búsquedas con distinto tamaño de resultado.

**TTL**: configurable en `.env` como `RETRIEVAL_CACHE_TTL_HOURS=168` (7 días por defecto).

**Wrappers inyectables**: `CachedWebConnector` y `CachedOpenAlexConnector` envuelven los
connectors reales. `force_ddg=True` en `CachedWebConnector` bypasa la caché (test/debug).

**Interacción con ADR-013**: la caché guarda la *búsqueda* (lista de `WebResult`); la
persistencia en pgvector (ADR-013) gestiona los *chunks* ya ingestados. Son ortogonales.

---

## Consecuencias

### Positivas
- Re-ingesta y harness 10–50× más rápidos con `batch_mode()` (estimación; requiere
  medición con Ollama activo — ver `FASE15_HALLAZGOS.md` §2).
- Búsquedas web/OpenAlex repetidas (misma empresa o query frecuente) son instantáneas.
- Sin cambios en el comportamiento funcional del sistema.

### Negativas / limitaciones
- `batch_mode()` no está cablerrado en el pipeline E2E todavía (pendiente Fase 16).
- La caché no está cablerrada en el pipeline E2E todavía (pendiente Fase 16).
- TTL de 7 días puede devolver resultados desactualizados para sectores muy volátiles.
  Si se necesita frescura, reducir `RETRIEVAL_CACHE_TTL_HOURS` o llamar con `force_ddg=True`.
- La tabla `retrieval_cache` crece indefinidamente; en producción añadir un job de limpieza
  de entradas expiradas (no bloqueante — un `DELETE WHERE expires_at < now()` semanal).

---

## Estado de implementación

| Componente | Archivo | Estado |
|-----------|---------|--------|
| `Embedder.batch_mode()` | `infrastructure/retrieval/embedder.py` | ✅ implementado |
| `EMBEDDER_KEEP_ALIVE` / `EMBEDDER_BATCH_KEEP_ALIVE` | `shared/config.py` | ✅ |
| `--warm` en harness | `scripts/eval_retrieval.py` | ✅ |
| `RetrievalCache` modelo ORM | `data/models/retrieval_cache.py` | ✅ |
| `RetrievalCacheRepository` | `data/repositories/retrieval_cache_repo.py` | ✅ |
| `CachedWebConnector` / `CachedOpenAlexConnector` | `infrastructure/sources/cached_connector.py` | ✅ |
| Cablerrado en pipeline E2E | `generate_n1.py` / `generate_informe.py` | ⬜ pendiente |
