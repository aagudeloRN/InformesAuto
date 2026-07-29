# FASE 22 — Hallazgos: Evidencia y Retrieval (Sprint A)

> Estado: **Sprint A — CERRADO y validado (A1/A2/A3).** Harness A/B + E2E en 2 sectores
> completos (3020 Alpina, 2510 Sofasa) ejecutados 2026-07-29 sobre el corpus EMIS indexado
> (§5/§6). Los 6 criterios de aceptación quedan demostrados; deuda nueva DT-054/055 (§9) → F23/B.

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

## 5. Validación — T22.A3 (ejecutada 2026-07-29, corpus EMIS indexado)

### 5.1 Harness de retrieval (antes/después) — `scripts/eval_retrieval.py`

Gold set de 25 consultas (una por sector GICS). Snapshots en `docs/decisions/`:
`fase22_baseline.json` (MMR λ=0.7, el config vigente), `fase22_nomm.json` (contraste λ=1.0),
comparados contra `fase14_baseline.json`.

| métrica                | F14 baseline | **F22 (MMR 0.7)** | F22 (sin MMR, λ=1.0) |
|------------------------|:-----------:|:-----------------:|:--------------------:|
| context precision      | 1.0000      | **1.0000**        | 1.0000               |
| cross-sector contam.   | 0.0000      | **0.0000**        | 0.0000               |
| hit-rate sectorial     | 1.0000      | **1.0000**        | 1.0000               |
| chunks correctos (avg) | 3.2000      | **3.7600**        | 4.0400               |
| score medio sectorial  | 0.7636      | **0.7604**        | 0.7602               |

- **Sin regresión** (criterio 5): precisión 1.0 y contaminación 0.0 se mantienen tras reactivar
  MMR y bajar el cap por doc; `avg_correct` sube de 3.2 → **3.76** sobre el corpus enriquecido.
- MMR (λ=0.7) rinde ligeramente menos `avg_correct` que sin MMR (3.76 vs 4.04) porque **cambia
  relevancia por diversidad** — su beneficio real (más documentos distintos citados) se mide en
  el E2E (§5.2), no en el conteo de gold por sector. El harness no mide diversidad de documentos.

### 5.2 E2E sobre 2 sectores completos + anti-mezcla — T22.A3

Dos corridas `run_pilot.py` con Ollama libre (una a la vez, VRAM WSL 8GB):
**Alpina S.A.S. → GICS 3020** y **Sofasa S.A. → GICS 2510** (chain_02 resolvió 2510 en runtime;
la SQL de retrieval usó `sector='2510'`). Métricas de `historial_informes.metricas_fiabilidad`
+ log anti-mezcla + inspección `python-docx`:

| criterio                       | Alpina (3020)        | Sofasa (2510)             |
|--------------------------------|----------------------|---------------------------|
| n_fuentes_total (antes 3)      | **8** ✅             | **14** ✅                 |
| n_citas_huerfanas              | **0** ✅             | **0** ✅                  |
| n_huerfanas_suprimidas         | 0                    | 0                         |
| caps OK                        | 7/7                  | 7/7                       |
| Cap 5 áreas (T22.6)            | **4** (5.1–5.4) ✅   | **4** (5.1–5.4) ✅        |
| Cap 6 cruza caps previos (T22.1)| **sí** (Cap 2/3/4/5)| **sí** (Tendencias/Converg.)|
| anti-mezcla `on/exento/ajeno`  | 1/7/0 (nivel doc)    | **17/33/0** (log, chunks) |
| EMIS del sector en Referencias | Informe sectorial 3020| Informe sectorial 2510 + "Automotor" |

- **Anti-mezcla (criterio 4): `ajeno=0` en ambos** — ningún chunk de un sector específico ajeno
  se citó; los globales (`es_global=true`) y la web quedan exentos por ADR-012/018. El histograma
  se emite por log en cada corrida (`generate_informe`, paso 10) vía `coherence.sector_histogram`.
- **T22.1**: Cap 6 de Alpina referencia hallazgos concretos ("el crecimiento del 27 % en volumen
  del segmento de café listo para beber" [Cap 3], "Nestlé y Danone… bebidas fortificadas" [Cap 2],
  "integración de sensores IoT" [Cap 5]); el de Sofasa referencia "El capítulo de Tendencias…",
  "El capítulo de Convergencia Territorial…".

## 6. Métricas de cierre (antes → después)

| indicador                         | antes (F21 A/B) | después (F22 A3)        |
|-----------------------------------|:---------------:|:-----------------------:|
| Referencias por informe           | 3               | **8 (Alpina) / 14 (Sofasa)** |
| chunks correctos (harness, avg)   | 3.2             | **3.76**                |
| citas huérfanas en `.docx`        | 1 (Alpina A/B)  | **0 / 0**               |
| anti-mezcla `ajeno` (sectorial)   | (no medido)     | **0 / 0**               |
| precisión / contaminación harness | 1.0 / 0.0       | **1.0 / 0.0** (sin regresión) |

**Los 6 criterios de aceptación del Sprint A quedan demostrados** con evidencia reproducible
(snapshots + 2 `.docx` en `output/fase22_alpina.docx` y `output/fase22_sofasa.docx`).

## 9. Hallazgos y deuda nueva (no bloquean el cierre de Sprint A)

- **DT-054 — EMIS individuales sub-citados.** El sector 3020 tiene 14 docs (13 EMIS individuales
  + 1 compilado) y 2510 análogo, pero las Referencias siguen dominadas por web + el compilado.
  Causa: (a) la **reserva sectorial estricta** filtra a `tipo_fuente='informe_compilado'`
  (`embedding_repo.search_similar`), así que los EMIS individuales (con `tipo_fuente` NULL) **nunca
  entran a la reserva garantizada**; (b) en el pool general compiten por score con la web y suelen
  perder. La diversidad en *conteo* subió (3→8/14) pero la *mezcla de fuentes* es web-pesada.
  Acción → **F23**: ampliar la reserva sectorial más allá del compilado (o dar boost de score a
  EMIS) y/o etiquetar `tipo_fuente` en la ingesta EMIS. La capacidad multi-sector (DT-053) sigue
  dormida (columna `sectores_adicionales` vacía).
- **DT-055 — Fuga de andamiaje del prompt en el intro del Cap 6 (Sofasa).** El párrafo
  introductorio de Accionables filtró meta-texto del modelo ("We need to produce a paragraph
  intro…", "Answer", "(In)"). El *cuerpo* de accionables quedó limpio y sí cruza capítulos (T22.1).
  Aislado a la cadena de párrafos intro N2; no ocurrió en Alpina. Acción → **Sprint B** (endurecer/
  sanear la salida del intro; posible `strip` de reasoning). No afecta anti-mezcla/refs/huérfanas.

## 10. Docs fallidos de la ingesta EMIS (A3-d, no bloqueante)

Los 5 errores de la ingesta (Deloitte Retail, CBRE Real Estate ×2, FDA Novel Drug, EY LatAm)
están **fuera** de 3020/2510/2010 → no afectan la validación. El log de ingesta
(`/tmp/ingest_emis_full.log`) ya no existe, por lo que el traceback exacto no se recuperó; los
PDF existen en disco (`documentos_sectoriales/FuentesEMIS/`) y no impiden nuevas ingestas.
**Decisión:** deuda de curación → **F23** (re-ingesta puntual con diagnóstico del PDF), no se
re-ingiere ahora por no aportar a los sectores validados.

## 7. Sprint B adelantado (código, mientras indexa el corpus EMIS)

Con Sprint A cerrado en código y la indexación EMIS de fondo (bloquea E2E/Ollama), se
adelantaron dos tareas de Sprint B **solo-código + tests mockeados**:

### T22.1 (Q1) — Coherencia: contexto de caps previos — commit `6e6e220`
Cap 6 (Accionables) pedía "cruzar hallazgos de capítulos anteriores" pero su prompt solo
recibía el retrieval RAG. Ahora recibe un resumen de Caps 2/3/4/5.
- `domain/coherence.py` (nuevo): `build_caps_summary()` (helper puro que recorta/etiqueta).
- `chain_07_accionables` + `generate_accionables`: variable `{hallazgos_caps_previos}` +
  instrucción de referenciar un hallazgo concreto (retrocompatible con default).
- `generate_informe`: `_run_n2` construye el resumen y lo pasa a Cap 6; `_run_n3` añade Cap 2.3
  Mercado al `cap_textos` del Resumen (chain_08 ya recibía los demás caps → esa mitad de Q1
  ya estaba resuelta). +6 tests.

### T22.6 (DT-047) — Fijar 4 áreas en Cap 5 — commit `71d67d2`
El Cap 5 generó 5.1–5.7 (avianca) en vez de las 4 áreas canónicas. La síntesis integraba los
3 ejes sin prohibir inventar áreas.
- `chain_06_convergencia`: prompt de síntesis endurecido a EXACTAMENTE 4 áreas (prohíbe 5.5+).
- `coherence.py::enforce_cap5_areas()`: elimina subsecciones `## 5.N` con N>4 (defensa en
  profundidad, RN-safe), aplicado en ambas rutas de `generate_convergencia`. +4 tests.

Suite tras Sprint B: **343 fast tests**, ruff 0.

## 8. Verificación multi-sector (DT-053) — 2026-07-27

**Pregunta:** ¿un informe EMIS puede servir a varios sectores/subsectores? **Sí, y el diseño
ya lo soporta** (Fase 18 T18.4):
- **Ingesta** (`pdf_ingestor.py`): la columna CSV `sectores_adicionales` se guarda como
  `metadatos["sectores"] = [sector_primario] + adicionales`.
- **Retrieval** (`embedding_repo.search_similar`, rama sectorial no-estricta):
  `sector_gics = :sector OR jsonb_exists(sectores, :sector)` → el doc aflora en todos sus sectores.

**Pero hay 3 salvedades** (→ DT-053; no bloquean lo hecho hoy):
1. **Datos:** la columna `sectores_adicionales` está **vacía en las 250 filas** del CSV → hoy
   ningún doc está multi-etiquetado (capacidad dormida). Requiere un pase de curación.
2. **Idempotencia:** el batch salta por título los docs ya ingeridos, así que re-etiquetar un
   doc existente NO surte efecto sin borrar/re-ingerir ese doc (o un update path).
3. **Medición:** el harness (`retrieval_metrics.py`) y el anti-mezcla de A3 leen solo
   `sector_gics` (primario); con docs multi-sector marcarían "contaminación" falsa. Al poblar
   `sectores`, deben honrar el array. Hoy, con la columna vacía, el chequeo por `sector_gics`
   es correcto.

Esto refuerza el objetivo de la base documental (reducir dependencia de la búsqueda web,
ADR-001/003) sin duplicar PDFs: un mismo informe transversal se cita en todos los sectores a
los que aplica, y la web sigue como complemento.
