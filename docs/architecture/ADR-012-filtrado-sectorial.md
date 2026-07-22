# ADR-012 — Filtrado sectorial en el retrieval y ciclo de vida del corpus

**Fecha:** 2026-07-22
**Estado:** Aprobado
**Fase:** 13

---

## Contexto

Ruta N aporta un corpus permanente de **25 informes sectoriales compilados** (uno por
grupo GICS, 2026). Antes de Fase 13, el índice pgvector era único y sin dimensión
sectorial: una consulta de "Materiales" podía recuperar chunks del informe de "Bancos"
(ruido cross-sector). Además, cada informe (~450 KB) genera cientos de chunks, con riesgo
de que **un solo documento monopolice** los slots de contexto.

El identificador sectorial canónico es el **código GICS numérico** (4 dígitos). El
`grupo_gics` producido por el LLM varía textualmente pero siempre incluye `"(GICS XXXX)"`.

---

## Decisión

### 1. Etiquetado de chunks por metadatos JSONB (no columna nueva)

El `sector_gics` (código) y `tipo_fuente="informe_compilado"` se propagan al campo
`metadatos` JSONB de cada `EmbeddingVectorial` en la ingesta. **No** se añade columna a
`embeddings_vectoriales`.

**Justificación:** pgvector 0.8+ filtra sobre JSONB en la cláusula `WHERE` con coste
despreciable a esta escala (25 docs, pocos miles de chunks) incluso con scan exacto. Un
índice parcial/GIN sobre `metadatos->>'sector_gics'` es opcional y se puede añadir si el
corpus crece. Evitar una migración de columna mantiene intacto el índice vectorial.

### 2. Filtrado en `search_similar` / `PGVectorStore.search`

Firma: `search(query, top_k, threshold, empresa_id, sector_gics=None, solo_activos=True)`.

- **Sector:** con `sector_gics`, se conservan los chunks de ese sector **más** las fuentes
  sin sector (web/académicas, `metadatos->>'sector_gics' IS NULL`); se excluyen los otros
  sectores (ruido).
- **Ciclo de vida:** `solo_activos=True` excluye chunks de documentos con `activo=False`,
  vía `LEFT JOIN documentos_locales`. Los chunks web (sin `documento_id`) siempre pasan
  (`d.activo IS NOT FALSE`).
- **Cap por documento:** tras recuperar, se limita a `rag_max_chunks_per_doc` (default 4)
  chunks por `documento_id`. Mitiga la monopolización sin implementar MMR completo
  (hallazgo de RepositorioRN, ver `docs/decisions/FASE13_HALLAZGOS.md`).
- **Reserva de cupos sectoriales** (refinamiento tras evaluación T13.7): con match de GICS,
  además de la búsqueda general se hace una búsqueda **estricta** (mismo GICS +
  `tipo_fuente=informe_compilado`) que reserva `rag_sector_reserve` (default 3) slots con
  **umbral relajado** `rag_sector_reserve_threshold` (default 0.5). Los reservados se
  anteponen y el resto rellena por score. **Motivo:** el backlog de chunks web sin sector
  (que puntúan alto) desplazaba a los chunks sectoriales (~0.68–0.78), incumpliendo el
  objetivo de la fase. El corpus sectorial es on-topic por construcción, por lo que un
  umbral menor es correcto para garantizar su presencia sin introducir ruido cross-sector.

### 3. Ciclo de vida por JOIN, no denormalizado

`activo` vive **solo** en `documentos_locales` (fuente única de verdad). Un toggle no
reescribe los chunks; el filtro se resuelve por JOIN en tiempo de consulta.

### 4. Extracción del código GICS

`extract_gics_code(grupo_gics)` (en `shared/constants/gics_groups.py`) aplica
`r"\(GICS (\d{4})\)"`. El pipeline deriva el código de `ctx.gics.grupo_gics` y lo pasa como
`sector_gics_code` a los use cases N1/N2, que lo reenvían a `search()`.

### 5. Estandarización de `fuente_tipo` y citación

- `pdf_ingestor` inserta `fuente_tipo="pdf"` (antes `"pdf_manual"`, que violaba el
  `CheckConstraint` de `embeddings_vectoriales` y no activaba el formato APA de informe).
- Los chunks de tipo `PDF_SECTORIAL` llevan `tipo_fuente="informe_compilado"`; el
  `apa_formatter` emite `"… [Informe compilado de múltiples fuentes]."` para reflejar que
  son compilaciones institucionales de múltiples fuentes.

### 6. Retiro del PDF hardcodeado (DT-017)

Se elimina `_run_pdf` de `generate_informe.py` (ingesta de un PDF fijo en cada corrida). El
corpus se ingesta **una vez** por el panel Repositorio o `scripts/ingest_batch.py`.

---

## Consecuencias

- **Positivas:** retrieval sectorialmente relevante; corpus gobernable (activar/desactivar
  sin borrar); citación APA fiel; menos acoplamiento (DT-017 saldado); diversidad de
  fuentes por el cap por documento.
- **Costo:** el JOIN a `documentos_locales` añade trabajo por consulta (marginal a esta
  escala). Si el corpus crece mucho, evaluar índice parcial/GIN e `hnsw.iterative_scan`.
- **Migración:** `ensure_documento_columns()` es idempotente (`ADD COLUMN IF NOT EXISTS`) y
  refresca el `CHECK` de `tipo` para admitir `PAPER_ACADEMICO`.

---

## Addendum Fase 14 (2026-07-22) — decisiones medidas sobre el retrieval

Evaluadas con el harness T14.1 (`scripts/eval_retrieval.py`). Detalle en `FASE14_HALLAZGOS.md`.

- **MMR completo:** portado (`infrastructure/retrieval/mmr.py`, parametrizable por
  `rag_mmr_lambda`) pero **desactivado por defecto (λ=1.0)**. Degrada el retrieval en este
  corpus: la evidencia sectorial está concentrada en un único documento por sector, y la
  penalización por documento repetido empuja esa evidencia hacia abajo. El **cap por documento**
  (§2) sigue siendo el mecanismo de diversidad. MMR queda como palanca para corpus futuros
  multi-documento por sector.
- **`chunk_size` 1000 / overlap 200** (antes 500/50): **retrieval-neutral** (precision 1.0,
  contaminación 0.0, hit 1.0 sin cambio) con ~57% de los chunks (998 vs 1746). Se adopta por
  eficiencia, no por calidad.
- **Índice parcial/GIN sobre `metadatos->>'sector_gics'`:** **no se añade.** La latencia SQL
  aislada del embedding es ~14–15 ms a esta escala (el embedding local domina el ~99% del
  tiempo). Se mantiene la recomendación de §2: índice opcional solo si el corpus crece.
- **Reserva de cupos (§2):** los cupos reservados usan orden por score puro (MMR no se aplica en
  la búsqueda estricta), garantizando que afloren los chunks sectoriales de mayor similitud.
