# ADR-005: Diseño de la capa de retrieval

**Estado:** Aceptado | **Fecha:** 2026-06-22
**Decisores:** aagudelo
**Relacionado con:** ADR-001 (RAG propio), ADR-002 (routing local-primero), ADR-003 (fuentes doble vía)

## Contexto

Fase 2 construye la capa de recuperación de información que alimenta los tres prompts
del piloto. Las decisiones de diseño en esta capa tienen impacto directo en el costo
por informe, la velocidad de generación y la mantenibilidad del sistema.

Las restricciones relevantes:
- ADR-001: el motor de retrieval es RAG propio — no langchain-postgres, no Weaviate.
- ADR-002: Ollama en el host, sin dockerizar; acceso HTTP directo.
- ADR-003: doble vía de ingesta (automática web + manual PDF); mismo índice vectorial.
- CLAUDE.md Tier 1: todo acceso externo pasa por wrapper en `infrastructure/`; sin
  nombres de modelo hardcodeados en código.

## Decisiones

### D1: Embedder via httpx directo a Ollama (no OllamaEmbeddings de LangChain)

**Alternativa rechazada:** `OllamaEmbeddings` de `langchain-community`.

**Razón:** El wrapper de LangChain añade estado interno, reintentos implícitos y
configuración que se superpone con la del propio sistema (ADR-002 exige un único punto
de control de errores y logging). httpx directo sobre `/api/embeddings` da control
total: timeout, manejo de errores HTTP, logging con structlog, sin dependencia de
comportamiento interno de langchain.

**Consecuencia:** El mismo patrón aplica al LLM gateway de Fase 3: httpx directo
a `/api/generate` (Ollama) y a la API del proveedor externo — no `OllamaLLM` ni
`ChatOpenAI` de langchain como capa de transporte.

### D2: PGVectorStore escribe al ORM propio (no a las tablas de langchain-postgres)

**Alternativa rechazada:** `PGVector` store de `langchain-postgres`, que crea su
propio schema de tablas (`langchain_pg_collection`, `langchain_pg_embedding`).

**Razón:** El proyecto necesita metadata estructurada en los embeddings: `empresa_id`,
`documento_id`, `fuente_tipo`, `fuente_url`, `chunk_index`. El schema de langchain-postgres
es genérico y usa JSONB para toda la metadata — no permite FKs, constraints de tipo,
ni queries con filtros eficientes sobre esas columnas. Nuestro ORM
(`embeddings_vectoriales`) tiene el schema exacto que el dominio necesita.

**Consecuencia:** `langchain-postgres` puede eliminarse de `pyproject.toml` en
Fase 3 si no se usa para nada más. Por ahora se mantiene para evitar un uv sync
destructivo antes de confirmar que ninguna otra parte del sistema lo use.

### D3: Búsqueda coseno con operador pgvector `<=>` via SQL literal

**Alternativa rechazada:** `func.cosine_distance()` de SQLAlchemy-pgvector.

**Razón:** El operador `<=>` es directo, legible, y el comportamiento de
`func.cosine_distance()` depende de cómo SQLAlchemy traduce la función para el
dialecto `pgvector`. El SQL literal es explícito:

```sql
SELECT id, 1 - (embedding <=> CAST(:vec AS vector)) AS score
FROM informes_ic.embeddings_vectoriales
ORDER BY embedding <=> CAST(:vec AS vector)
LIMIT :fetch_k
```

`1 - distancia` convierte distancia coseno (menor = más similar) en similitud (mayor
= más similar), alineado con `RAG_SIMILARITY_THRESHOLD=0.7` que se interpreta como
"similitud ≥ 0.7".

**Lección aprendida (Hallazgo #2):** La raw SQL debe usar el nombre calificado con
schema (`informes_ic.embeddings_vectoriales`) — nunca el nombre corto. Se obtiene
con `EmbeddingVectorial.__table__.fullname`.

### D4: Ingesta on-demand (no pre-indexada) para fuentes web del piloto

**Contexto:** Para el Prompt-03 (Benchmarking), se necesitan fichas de ~14 competidores.

**Decisión:** La ingesta ocurre en la misma ejecución que la generación del capítulo.
No hay un job de indexación previo separado.

**Razón:** En el piloto, el número de competidores es pequeño (~14) y los textos son
cortos (~100–300 tokens por resultado de búsqueda). El tiempo de embed on-demand
(< 1 s/texto) no afecta perceptiblemente el tiempo total de generación. Mantener una
tarea de pre-indexación separada añadiría estado que gestionar (¿cuándo está
actualizado el índice?) sin beneficio real en este volumen.

**Consecuencia para Fase 4+:** Los PDFs manuales (EMIS, informes sectoriales) sí
tienen pre-indexación separada via `scripts/ingest_pdf.py`, porque son documentos
grandes (> 50 páginas) que no se quiere re-ingestar en cada generación. La distinción
es: **fuentes web = on-demand; PDFs locales = pre-indexados**.

### D5: Estrategia de fallback para búsqueda web (Tavily → DDG)

**Decisión:** `WebConnector` intenta Tavily si `TAVILY_API_KEY` está configurado;
si está vacío, usa DDG (`ddgs` package). No hay mezcla simultánea de fuentes.

**Razón:** Tavily provee snippets + content estructurado y tiene SLA. DDG es gratuito
pero puede tener rate limiting. Para el piloto, DDG es suficiente. El switch es
transparente al caller: misma interfaz `search() -> list[WebResult]`.

**Nota operativa:** El paquete `duckduckgo-search` fue renombrado a `ddgs` — usar
siempre `from ddgs import DDGS`. Ver Hallazgo #1 en `FASE2_HALLAZGOS.md`.

### D6: Extracción de CIIU por regex sobre resultados web

**Contexto:** Prompt-01 necesita el código CIIU de la empresa desde el RUES.

**Decisión:** `WebConnector.extract_ciiu()` aplica regex `r'CIIU[:\s]*(\d{4,6})'`
sobre el título y snippet de los resultados de búsqueda. No hay scrape directo de
rues.org.co.

**Razón:** rues.org.co bloquea scraping programático (CAPTCHA, bot detection). Una
búsqueda web de `{empresa} RUES CIIU` frecuentemente incluye el código en el snippet
indexado por el buscador. Si el regex no encuentra nada, el caller registra "No
disponible" — cumple la política de datos ausentes de ADR-002.

## Consecuencias globales

1. La capa de retrieval es completamente independiente de langchain para su ejecución
   (usa langchain solo para `RecursiveCharacterTextSplitter` en `chunker.py`).
2. El `PGVectorStore` es el único punto de entrada para ingest + search desde el
   dominio — no hay acceso directo al repo ni al embedder desde capas superiores.
3. El `EmbeddingRepository` puede recibir filtros adicionales en el futuro
   (`documento_id`, rango de fechas) sin cambiar la interfaz de `PGVectorStore`.

## Referencias

- ADR-001: Motor de retrieval (RAG propio + pgvector)
- ADR-002: Routing de modelos
- ADR-003: Estrategia de fuentes
- `docs/decisions/FASE2_HALLAZGOS.md`: hallazgos técnicos de implementación
