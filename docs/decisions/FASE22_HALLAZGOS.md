# FASE 22 — Hallazgos: Evidencia y Retrieval (Sprint A)

> Estado: **Sprint A — código cerrado y commiteado (A1/A2); validación E2E (A3) pendiente**
> de que termine la indexación EMIS de fondo. Este documento se completa con los números del
> harness y del E2E cuando A3 se ejecute (≥2 sectores completos: ya disponibles 3020 y 2510).

## 1. Objetivo

Que el corpus EMIS enriquecido se traduzca en **fuentes diversas y trazables** en el informe.
La prueba A/B post-ingesta del sector 3020 (`FASE21_HALLAZGOS.md §5.2`) mostró que enriquecer
el corpus **mejora mucho el contenido** (14 fichas de competidor, radar real, 1→16 tablas)
pero **no la citación** (Referencias planas en 3, fuentes EMIS no citadas, cita huérfana). El
cuello de botella era **retrieval + citación, no corpus**.

## 2. Cambios por tarea (1 commit atómico cada uno)

### T22.A1 (DT-049) — Diversidad de retrieval — commit `4c342c4`

Causa raíz (verificada en código): `PGVectorStore.search()` ordenaba por score puro (MMR
desactivado, `rag_mmr_lambda=1.0`), con cap `rag_max_chunks_per_doc=4` y `rag_top_k=10`; el
informe compilado sectorial monopolizaba los chunks de mayor score → `chunks_usados` abarcaba
~2-3 documentos → `build_references_section` (fiel: 1 ref/doc) emitía solo 3 referencias.

- `shared/config.py`: `rag_max_chunks_per_doc` 4→2; `rag_mmr_lambda` 1.0→**0.7** (MMR
  reactivado — su reversión en Fase 14 fue por corpus mono-documento, condición superada por
  el corpus EMIS multi-doc); nuevo `rag_min_distinct_docs=5`.
- `infrastructure/retrieval/pgvector_store.py`: pool base ampliado (`k*3`) +
  `_enforce_doc_diversity()` — sustituye chunks de documentos sobre-representados por chunks
  de documentos no representados del pool, **protegiendo las reservas** (mira desde el final),
  sin bajar de `top_k` ni introducir candidatos bajo umbral. Clave de documento alineada con
  `build_references_section` (`documento_id` → `fuente_url`).
- Tests mockeados (`tests/test_fase22_diversity.py`, 5): backfill a ≥5 docs, corpus mono-doc,
  no-bajo-umbral, web por URL, método puro protege reservas. Ajuste de aislamiento en
  `tests/test_fase13_sectorial.py` (`rag_min_distinct_docs=0`).

### T22.A2 (DT-052) — La citación sigue al corpus + huérfanas — commit `e364a52`

Nota de diseño: las cadenas de síntesis (05/06/07) son "sin citación inline" **por diseño**;
sus chunks igual llegan a Referencias vía `chunks_usados`. Por tanto el déficit de fuentes es
consecuencia directa de la diversidad de retrieval (A1). A2 cubre las huérfanas y el contrato.

- `infrastructure/citation/apa_formatter.py`: nuevo `strip_orphan_citations(texto, refs)` que
  **suprime** las citas `(Autor, año)` sin referencia que las respalde (nunca inventa la fuente
  — RN-001); refactor del regex compartido con `find_orphan_citations`.
- `domain/use_cases/generate_informe.py`: sanea cada capítulo antes del ensamblado; expone
  `n_huerfanas_suprimidas` en el panel de fiabilidad; la detección residual debe dar 0.
- `domain/chains/chain_03_benchmarking.py`: prompt endurecido a **una sola fuente por cita**
  (evita la huérfana multi-entidad `(Alpina, Carvajal Empaques, 2019)` del A/B).
- Tests (`tests/test_apa_formatter_v2.py`, +6): supresión de huérfanas, cita multi-entidad,
  contrato `chunks_usados`→Referencias, saneamiento sin huérfanas residuales.

## 3. Decisiones de diseño

- **Reactivar MMR (λ 0.7)** es un ajuste de la palanca documentada de ADR-014 para la nueva
  realidad del corpus (multi-doc), no una re-litigación del ADR.
- **Garantía determinista de diversidad** (`rag_min_distinct_docs`) por encima de confiar solo
  en MMR + cap: satisface el criterio de aceptación "≥5 docs distintos cuando existen" de forma
  testeable, sin depender del azar del ranking.
- **Supresión de huérfanas, no invención**: ante una cita sin respaldo, se elimina la cita
  (RN-001). No se fabrica una referencia.

## 4. Estado de la deuda técnica

- **DT-049** (breadth/diversidad de retrieval): código Sprint A commiteado (A1). Validación de
  no-regresión de precisión y "≥5 docs distintos" con el harness → §5 (pendiente).
- **DT-052** (citación no sigue al corpus): código Sprint A commiteado (A2). Validación de
  "≥8 referencias, 0 huérfanas, fuentes EMIS presentes" en E2E → §5 (pendiente).

## 5. Validación (PENDIENTE — tras indexación EMIS)

### 5.1 Harness de retrieval (antes/después) — `scripts/eval_retrieval.py`

<!-- Correr con la BD estable (indexación terminada):
     uv run python scripts/eval_retrieval.py --mode filtered
     uv run python scripts/eval_retrieval.py --mode filtered --mmr-lambda 1.0   # contraste A/B
     Medir: nº de documentos distintos por consulta, precision, contamination, hit-rate.
     Criterio: ≥5 docs distintos cuando existen; sin regresión de precisión vs baseline F14. -->
_Pendiente._

### 5.2 E2E sobre sectores completos (≥2) + anti-mezcla — T22.A3

Sectores completos confirmados en BD (2026-07-27): **3020 Alimentos (14 docs)**,
**2510 Automóviles (12 docs)**, 2010 Bienes de capital (11). Procedimiento:

```bash
# 3020 (dentro del corpus food):
uv run python scripts/run_pilot.py --empresa "Alpina S.A.S."
# 2510 (automotriz colombiana; confirmar que chain_02 resuelve su GICS a 2510):
uv run python scripts/run_pilot.py --empresa "<empresa automotriz colombiana>"
```

Criterios de aceptación por informe:
- Referencias 3 → **≥8 fuentes distintas**; **0 huérfanas**; fuentes EMIS del sector presentes.
- **Anti-mezcla**: los chunks *sectoriales* citados pertenecen al `sector_gics` de la empresa
  (los globales `es_global=true` están exentos por ADR-012/018); ningún sector específico ajeno
  aparece citado.

_Pendiente de ejecutar (esperando fin de la indexación EMIS, por decisión del usuario)._

## 6. Métricas de cierre

_Pendiente (se completa al cerrar Sprint A tras A3)._
