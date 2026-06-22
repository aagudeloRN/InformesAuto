# Hallazgos de Fase 2 — Retrieval Layer

**Fecha:** 2026-06-22
**Fase:** 2 — Retrieval (conectores web + chunking + embeddings + pgvector store)

Registro de decisiones operativas y hallazgos imprevistos durante la ejecución de
Fase 2 que afectan fases siguientes.

---

## 1. Paquete `duckduckgo-search` renombrado a `ddgs`

**Hallazgo:** Al instalar `duckduckgo-search>=6.0` se instaló la versión 8.1.1, que
incluye este warning en tiempo de ejecución:

```
RuntimeWarning: This package (`duckduckgo_search`) has been renamed to `ddgs`!
Use `pip install ddgs` instead.
```

Además, en la versión 8.x el uso del context manager `with DDGS() as ddgs:` retorna
0 resultados sin lanzar excepción. El patrón correcto es `DDGS().text()` directamente
— pero la causa raíz es que el paquete está obsoleto.

**Decisión tomada:** Migrar de `duckduckgo-search` a `ddgs>=0.1` en `pyproject.toml`.
La versión instalada fue `ddgs==9.14.4`. El import pasa de
`from duckduckgo_search import DDGS` a `from ddgs import DDGS`. La API `DDGS().text()`
es idéntica en ambos paquetes.

**Impacto en Fase 3+:** Si se actualiza `ddgs` entre fases, verificar que la API
`.text()` siga siendo compatible. El paquete trae `primp`, `fake-useragent` y
soporte HTTP/2 como nuevas dependencias.

---

## 2. Raw SQL en `EmbeddingRepository` debe usar nombre calificado con schema

**Hallazgo:** La query de búsqueda coseno en `search_similar()` usaba:

```sql
FROM embeddings_vectoriales
```

Esto funcionaba cuando el test corría en aislamiento (`uv run pytest tests/test_retrieval.py`)
pero fallaba con `relation "embeddings_vectoriales" does not exist` al correr la suite
completa (`uv run pytest tests/`).

**Causa raíz:** El evento `@event.listens_for(engine, "connect")` que ejecuta
`SET search_path TO informes_ic, public` solo se dispara cuando se crea una **nueva**
conexión de BBDD. No se dispara cuando una conexión existente es sacada del pool. Al
correr la suite completa, `test_database.py` crea conexiones que luego son reutilizadas
por `test_retrieval.py` — pero esas conexiones están en un estado de pool donde el
`search_path` puede no estar activo en la transacción activa del `Session`.

Los inserts del ORM no sufren este problema porque SQLAlchemy genera nombres
calificados automáticamente (`informes_ic.embeddings_vectoriales`).

**Fix aplicado:**

```python
table = EmbeddingVectorial.__table__.fullname  # retorna "informes_ic.embeddings_vectoriales"
sql = text(f"SELECT ... FROM {table} ...")
```

Usar `__table__.fullname` lee el schema desde la metadata del modelo — no es un
string hardcodeado y es inmune al `search_path`.

**Regla derivada:** Toda raw SQL (texto literal con `sqlalchemy.text()`) en este
proyecto debe usar nombres de tabla calificados con schema. Usar `Model.__table__.fullname`
para obtenerlos. Aplicar en Fase 3+ si se escriben más queries literales.

---

## 3. `langchain-text-splitters` ya viene como sub-dependencia de `langchain`

**Hallazgo:** Al agregar `langchain-text-splitters>=0.3` a `pyproject.toml` y correr
`uv sync`, `uv` reportó que el paquete ya estaba instalado (era sub-dep de
`langchain>=0.3`). No hubo descarga adicional.

**Decisión tomada:** Se mantuvo la declaración explícita en `pyproject.toml` para
que la dependencia sea visible y versionada explícitamente — evita que un bump de
`langchain` cambie la versión de `langchain-text-splitters` sin que quede registrado.

---

## 4. Embedder via httpx directo a Ollama funciona correctamente

**Verificado:** `POST {OLLAMA_BASE_URL}/api/embeddings` con body
`{"model": "<LLM_LOCAL_EMBED_MODEL>", "prompt": "<text>"}` retorna
`{"embedding": [768 floats]}` en ≤1 s para textos cortos con `nomic-embed-text:latest`.

**Confirmado:** No se necesita `OllamaEmbeddings` de `langchain-community`. El
acceso HTTP directo es más simple, sin estado implícito del framework, y permite
control total del timeout y del manejo de errores HTTP.

**Impacto en Fase 3 (LLM Gateway):** El mismo patrón — httpx directo a Ollama
`/api/generate` o `/api/chat` — aplica para el wrapper de generación. No mezclar
con `OllamaLLM` de langchain a menos que haya una razón explícita.

---

## 5. Ingesta on-demand confirmada como patrón correcto para el piloto

**Verificado en test:** `PGVectorStore.ingest()` recibe textos web ya extraídos,
los chunkea, los embeds y los persiste en `embeddings_vectoriales` en una sola
llamada. La búsqueda posterior recupera los chunks correctos.

**Detalle del chunking con textos cortos:** En el piloto, las fichas de competidores
son textos de ~80–200 tokens. Con `chunk_size=500` (por defecto), cada texto produce
1 chunk. Para PDFs o artículos largos (Fase 4+), el splitter producirá N chunks.
El `chunk_index` en la BD registra la posición del chunk dentro de la ingesta — útil
para reconstruir el orden del documento fuente.

---

## 6. Vector de 768 dims confirmado en BD

El test `test_embedder_returns_correct_dimensions` confirma que el modelo
`nomic-embed-text:latest` produce exactamente 768 dimensiones, alineado con la
columna `VECTOR(768)` en `embeddings_vectoriales`. Si se cambia el modelo de
embeddings en el futuro, hay que:
1. Actualizar `_EMBED_DIM` en `src/ic/data/models/embedding_vectorial.py`
2. Re-crear la tabla (ya que el tipo `VECTOR(N)` no es alterable en pgvector)
3. Re-ingestar todos los documentos existentes

---

## Métricas de Fase 2

| Métrica | Valor |
|---------|-------|
| Archivos creados | 8 |
| Líneas de código | ~370 |
| Tests nuevos | 9 |
| Tests totales pasando | 13/13 |
| Tiempo embed (nomic-embed-text, texto ~100 tokens) | < 1 s |
| Dependencias nuevas | `ddgs==9.14.4`, `langchain-text-splitters>=0.3` |
