# Research: 008 — Ingesta Masiva Paralela de PDFs e Infraestructura de Evidencia

**Date**: 2026-09-17

---

## Decisión 1 — Modelo de Concurrencia

**Decision**: `ThreadPoolExecutor` (hilos del SO)

**Rationale**: Las llamadas a Ollama (embeddings) son HTTP — puro I/O. El GIL de Python se libera durante operaciones de I/O, permitiendo que múltiples threads avancen en paralelo. Los threads comparten memoria (sin serialización de args), son más livianos que procesos y no requieren cambios en `PdfIngestor`. El parseo de PDF (CPU) es rápido comparado con el embedding (I/O), por lo que el bottleneck es la red a Ollama.

**Alternatives considered**: `ProcessPoolExecutor` (evita GIL completamente pero requiere serialización y más RAM), `asyncio` + `httpx` async (requeriría reescribir `PdfIngestor` completo).

---

## Decisión 2 — Thread-safety de PdfIngestor

**Decision**: `PdfIngestor` es thread-safe sin modificaciones porque abre una `SessionLocal()` propia dentro de cada llamada a `ingest_batched()` (verificado en `pdf_ingestor.py:119,151,197,237`). Cada thread instancia su propio `PdfIngestor(settings)`.

**Rationale**: El objeto `Settings` es inmutable (Pydantic BaseSettings); compartirlo entre threads es seguro. La sesión de BD se crea y cierra dentro de cada context manager; no hay estado compartido mutable.

---

## Decisión 3 — Deduplicación de Chunks

**Decision**: Mantener `chunk_sha256` como clave de idempotencia (ya implementado). No añadir constraint `(documento_id, chunk_index)`.

**Nota (verificada en código)**: no es un constraint de BD sino una consulta previa en `pdf_ingestor.py:57`, no atómica; `AutoEnrich` guarda `chunk_sha256` y omite repetidos (FR-013, T025–T028).

**Rationale**: SHA-256 del texto detecta duplicados cross-documento (más robusto). Añadir un segundo constraint requeriría una migración DDL sobre la BD compartida (`ALTER TABLE embeddings_vectoriales ADD CONSTRAINT ...`), con riesgo de lock en prod. El comportamiento existente ya satisface SC-002.

---

## Decisión 4 — Umbral de Enriquecimiento

**Decision**: Usar `settings.rag_sector_reserve_threshold` (0.5) como umbral de activación del enriquecimiento.

**Rationale**: Es el umbral más permisivo del sistema, ya usado para sectores secundarios. Si el retrieval supera 0.5, hay suficiente evidencia; por debajo, el enriquecimiento aporta valor. No se introduce nueva variable de configuración (Q3 clarification).

---

## Decisión 5 — Integración de AutoEnrich en el Pipeline

**Decision**: Punto de integración en `_n1_chapter_builders.py` (o el helper de retrieval de cada capítulo), no en `pgvector_store.py` directamente.

**Rationale**: `pgvector_store.py` es infraestructura pura; no debe conocer lógica de dominio. `AutoEnrich` es un caso de uso de dominio que orquesta retrieval + enrichment + re-retrieval. Integrar en la capa de domain/use_cases mantiene la separación de capas (Constitución I — SoC).

**Alternatives considered**: Hook en `pgvector_store.py` (viola SoC), middleware de retrieval transparente (más complejo, requiere patrón Decorator).

---

## Decisión 6 — OpenAlex Polite Pool

**Decision**: Usar `settings.openalex_email` (ya en `Settings` y usado por `OpenAlexConnector` existente). Sin cambios en la configuración.

**Rationale**: `OpenAlexConnector.__init__` ya lee `settings.openalex_email` y lo pone en el header `User-Agent`. La infraestructura ya existe; `EnrichmentConnector` simplemente instancia `OpenAlexConnector(settings)`.

---

## Decisión 7 — Trazabilidad del enriquecimiento y embedder obligatorio

**Decision**: `try_enrich` devuelve un `EventoEnriquecimiento`; los eventos se guardan en `historial_informes.metricas_fiabilidad` (JSONB existente, clave `enriquecimiento`). `AutoEnrich` exige `embedder` (sin `None`).

**Rationale**: El spec (US2/AC4) y la constitución III piden historial completo. La columna JSONB ya existe, así que no hay migración. `ctx.embedder` siempre se construye con `Embedder(s)` (`_informe_context.py:144`) y el único llamador lo pasa; el vector de ceros `[0.0] * 768` era código muerto que, de activarse, contaminaría el índice compartido.

**Alternatives considered**: guarda en `try_enrich` que devuelve evento "fallido" si falta el embedder (innecesaria con embedder obligatorio); tabla nueva de eventos (requiere migración en BD compartida, desproporcionado).
