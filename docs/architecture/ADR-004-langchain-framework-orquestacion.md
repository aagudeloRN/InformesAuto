# ADR-004: LangChain como framework de orquestación LLM

**Estado:** Aceptado | **Fecha:** 2026-06-22  
**Decisores:** aagudelo  
**Reemplaza a:** —  
**Reemplazado por:** —

## Contexto

La fase de andamiaje (Fase 0) requería elegir el framework de orquestación LLM que
estructurará las cadenas de generación del DAG de capítulos, el pipeline de ingesta de
fuentes y el vector store de pgvector. Los candidatos evaluados fueron LangChain (≥0.3)
y LlamaIndex (≥0.11).

El entorno de desarrollo es un solo usuario, un informe a la vez, con prioridad en
velocidad de implementación del piloto sobre abstracción a largo plazo. El wrapper de
LLM que exige la Prime Directive (Dependency Agnosticism) significa que el dominio de la
aplicación no depende directamente del framework: un cambio futuro de framework está
acotado a la capa `infrastructure/`.

### Comparación evaluada

| Criterio | LangChain 0.3 | LlamaIndex 0.11 |
|----------|--------------|-----------------|
| Ya en pyproject.toml | Sí (`langchain`, `langchain-community`, `langchain-postgres`) | No (swap de 4 paquetes) |
| Soporte PGVector | `langchain-postgres` (battle-tested) | `llama-index-vector-stores-postgres` (menos maduro) |
| Soporte Ollama local | `langchain-community` OllamaLLM + OllamaEmbeddings | llama-index-llms-ollama (OK, pero menos ejemplos) |
| Cadenas para DAG de capítulos | LCEL chains (mapean directo a cap) | QueryEngine (orientado a Q&A, no a generación estructurada) |
| Loaders de fuentes (PDF, web, docx) | `langchain-community` document loaders completos | Readers equivalentes, menos documentados |
| Abstracción de ingesta | Chains manuales | IngestionPipeline (más limpio para pipelines puros de indexación) |
| Costo de migración si falla | Bajo (wrapper aísla) | Bajo (mismo argumento) |

### Ventaja de LlamaIndex no aprovechada

LlamaIndex hubiera sido mejor si el producto fuera un **sistema de Q&A sobre documentos**
(IngestionPipeline + QueryEngine). Nuestro producto es un **generador de secciones de informe
estructurado** donde el retrieval es un insumo, no el flujo principal. LCEL se ajusta mejor.

## Decisión

Se usa **LangChain ≥0.3** como framework de orquestación. Razones determinantes:

1. Ya instalado — cero costo de migración en dependencias.
2. `langchain-postgres` provee integración PGVector probada en producción.
3. LCEL (`chain = retriever | prompt | llm | parser`) mapea naturalmente al patrón
   de cada capítulo del DAG.
4. `langchain-community` cubre todas las fuentes automáticas del ADR-003 (Tavily,
   loaders web, PDF, OpenAlex via HTTP).
5. El wrapper en `infrastructure/llm/` (ADR-002) aísla al dominio del framework;
   reemplazarlo en el futuro está acotado a ese módulo.

## Consecuencias

**Positivas:**
- Sin cambios en `pyproject.toml` ni en `uv.lock`.
- Patrón de cadena LCEL disponible desde Fase 2 sin setup adicional.
- `langchain-postgres` gestiona la creación del índice HNSW en pgvector de forma
  transparente (o se puede desactivar para control manual).

**Negativas / riesgos:**
- LangChain tiene historial de breaking changes entre versiones menores; `uv.lock`
  fija las versiones exactas, lo que mitiga este riesgo.
- La abstracción de LCEL puede ser opaca al depurar; se compensa activando
  `verbose=True` y `structlog` en desarrollo.

## Referencias

- ADR-001: Motor de retrieval (RAG propio + pgvector)
- ADR-002: Routing de modelos (wrapper LLM único en `infrastructure/`)
- ADR-003: Estrategia de fuentes (doble vía: automática + manual)
