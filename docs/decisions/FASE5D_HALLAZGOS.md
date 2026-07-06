# Hallazgos Fase 5D

**Fecha:** 2026-07-06
**Contexto:** keep_alive:0 (fix OOM definitivo) + Cap 4 Ecosistema + pytest markers slow

---

## H5D-01 — `keep_alive: 0` como fix definitivo de OOM en WSL2/8GB

**Problema:** Ollama mantiene modelos cargados 5 minutos por defecto (`keep_alive=5m`).
Durante el pipeline E2E, `nomic-embed-text` (~500MB) y el LLM analítico (~5.2GB) coexisten
en VRAM cuando el embedder termina y el LLM aún no ha hecho su primer request. En 8GB de
VRAM este solapamiento agota la memoria y produce OOM o timeouts.

**Solución:** `"keep_alive": 0` en el body JSON de cada request a Ollama descarga el modelo
inmediatamente tras completar la inferencia. El siguiente request lo carga de nuevo (overhead
~2-4 segundos por load, aceptable). La solución aplica al embedder (`/api/embeddings`) y al
LLM (`/api/chat`), incluyendo el modo streaming. **No aplica a OpenRouter.**

**Verificación:** `curl -s http://127.0.0.1:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"test","keep_alive":0}' | jq '.embedding | length'` → `768`.

**Alternativa descartada:** `OLLAMA_KEEP_ALIVE=0` como variable de entorno global. Descartada
porque afecta a todos los procesos del sistema (incluidos usos interactivos de Ollama) y no
sigue el principio de control explícito por request.

---

## H5D-02 — Patrón N1 consolidado: chain_0N + GenerateX

El patrón chain_04/GenerateTendencias se demostró completamente replicable para Cap 4:

1. `chain_0N_nombre.py`: prompts del sistema + usuario, `build_chain_0N(llm) -> Runnable`, helpers
   de formateo reutilizados por re-exportación (no duplicados).
2. `generate_nombre.py`: `GenerateX` con `__init__(chain, store, web_connector)`, `execute()`
   con queries web → ingest → retrieval → check suficiencia → invoke chain → DTO.
3. El constructor de Cap 4 es más simple que el de Cap 3 (sin `openalex_connector`): para mapeo
   de actores del ecosistema, la web es suficiente fuente primaria.

**Implicación para Fase 5E:** Cap 5 Convergencia seguirá el mismo patrón pero recibirá los DTOs
de caps anteriores como input (retrieval cruzado en lugar de búsqueda nueva).

---

## H5D-03 — `@pytest.mark.slow` como separación práctica de velocidad de test

Los 7 tests marcados como `slow` (4 en `test_llm.py`, 3 en `test_retrieval.py`) tardan entre
10s y 90s cada uno cuando Ollama está disponible, y fallan con skip cuando no lo está. El marker
permite dos flujos de CI:

- **Rápido** (`pytest -m "not slow"`): 57+ tests en < 5 segundos; ejecutable sin servicios.
- **Completo** (`pytest`): 64 tests; requiere Ollama + PostgreSQL corriendo.

Los tests de ecosistema son todos mockeados y corren siempre en el flujo rápido.

---

## H5D-04 — Numeración chain vs. capítulo

La numeración de archivos chain no coincide con la numeración de capítulos del informe:

| Archivo chain | Capítulo en informe | Razón |
|--------------|---------------------|-------|
| `chain_01` | Cap 1 Descripción | coincide |
| `chain_02` | Clasificación GICS | no es capítulo del informe |
| `chain_03` | Cap 2 Benchmarking | desfase +1 |
| `chain_04` | Cap 3 Tendencial | desfase +1 |
| `chain_05` | Cap 4 Ecosistema | desfase +1 |

Esta discrepancia es intencional: la numeración de chains refleja el orden de implementación,
no la numeración final del documento. Las secciones internas del prompt (5.1, 5.2, 5.3) usan el
número del chain para evitar confusión con la numeración de capítulos.
