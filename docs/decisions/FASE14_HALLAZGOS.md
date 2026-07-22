# FASE 14 — Hallazgos: Calidad de Retrieval y Evaluación

**Fecha:** 2026-07-22 · **Branch:** `develop` (desde `62fe327`)

---

## 1. Objetivo

Elevar la calidad del retrieval RAG con **evidencia medible**, no por intuición. Se introduce
un harness de evaluación reproducible (T14.1) y cada cambio posterior (T14.2–T14.6) se justifica
con números antes/después. Se construye SOBRE ADR-012 (filtrado sectorial, reserva de cupos,
fallback por nombre): no se re-discute.

---

## 2. Harness de evaluación (T14.1) — la línea base

- **Gold set** (`tests/fixtures/gold_set.json`): 1 consulta por sector GICS del corpus (25
  consultas). Relevante = chunk con `metadatos.sector_gics == esperado` y
  `tipo_fuente=informe_compilado`.
- **Métricas puras** (`src/ic/domain/eval/retrieval_metrics.py`, sin I/O): context precision,
  cross-sector contamination, hit-rate sectorial, nº de chunks correctos, score medio sectorial.
- **Runner** (`scripts/eval_retrieval.py`): un comando, determinista (`nomic-embed-text` es
  estable), snapshots JSON versionados en `docs/decisions/fase14_*.json`. Modos `filtered`
  (producción, ADR-012) y `raw` (sin filtro, contraste), con `--mmr-lambda` y `--bench-sql`.

### Línea base (`fase14_baseline.json`, corpus con backlog web de 1202 chunks)

| Modo | precision | contaminación | hit-rate | chunks correctos (avg) | score medio |
|------|-----------|---------------|----------|------------------------|-------------|
| **filtered** (producción) | **1.000** | **0.000** | **1.000** | 3.20 | 0.7636 |
| raw (sin filtro) | 0.251 | 0.584 | 0.880 | 1.96 | 0.678 |

**Hallazgo central:** el path de producción (filtered, ADR-012) ya estaba **en el techo**
—precision 1.0, contaminación 0.0, hit 1.0—. La contaminación del modo raw (0.584) proviene de
chunks sectoriales de **otros** sectores (los informes Pulso puntúan alto en dominio), que el
filtro sectorial ya elimina. El backlog web **no** aparecía en el top-10 (puntúa por debajo de
los chunks sectoriales cross-sector), por lo que no contaminaba, solo ocupaba espacio.

---

## 3. MMR completo (T14.2) — **medido y revertido**

Se portó el reranking por diversidad de documento de RepositorioRN a
`infrastructure/retrieval/mmr.py` (parametrizable por `rag_mmr_lambda`, penaliza por
`documento_id`), reemplazando el cap simple como criterio primario de diversidad.

### A/B contra la línea base

| Modo | λ (MMR) | precision | contaminación | chunks correctos | score medio |
|------|---------|-----------|---------------|------------------|-------------|
| filtered | 1.0 (off) | 1.000 | 0.000 | 3.20 | 0.7636 |
| filtered | 0.7 (on) | 1.000 | 0.000 | **3.08** ↓ | 0.7640 |
| raw | 1.0 (off) | **0.251** | 0.584 | **1.96** | 0.678 |
| raw | 0.7 (on) | **0.153** ↓ | 0.576 | **0.92** ↓ | 0.684 |

**Decisión: MMR DESACTIVADO por defecto (`rag_mmr_lambda=1.0`).** En este corpus la evidencia
sectorial está **concentrada en un único documento por sector** (el informe Pulso). La
penalización por documento repetido de MMR empuja esa evidencia hacia abajo a favor de
diversidad cross-documento —que aquí equivale a ruido—, degradando precision y densidad de
evidencia correcta (raw: 1.96→0.92 chunks; filtered: 3.20→3.08). Se **conserva** la
implementación parametrizable y sus tests para corpus futuros con sectores multi-documento.

> Resultado negativo valioso: la evaluación evitó introducir un cambio que degradaba el
> retrieval y que "por intuición" parecía una mejora.

---

## 4. chunk_size 500→1000 / overlap 200 (T14.3) — **retrieval-neutral, se mantiene por eficiencia**

Re-ingesta idempotente del corpus (`scripts/ingest_batch.py`) con `chunk_size=1000/overlap=200`.

| chunk_size | chunks totales | precision | contaminación | hit | chunks correctos (avg) | score medio |
|------------|----------------|-----------|---------------|-----|------------------------|-------------|
| 500 / 50 (post-purga) | 1746 | 1.000 | 0.000 | 1.000 | 3.68 | 0.7617 |
| **1000 / 200** | **998** | 1.000 | 0.000 | 1.000 | 3.72 | 0.7574 |

**Resultado:** el cambio es **retrieval-neutral** —precision/contaminación/hit idénticos;
`chunks correctos` y score medio se mueven dentro del ruido (±0.04 y ∓0.004)—. No hay mejora
de calidad, pero tampoco degradación. **Decisión: mantener 1000/200** porque produce **~57% de
los chunks** (998 vs 1746) a igual calidad de retrieval: menos almacenamiento, menos embeddings
y alineación con RepositorioRN. La mejora medible del retrieval de la fase proviene de T14.5
(purga web), no del chunk_size. `nomic-embed-text` (768-dim) tolera bien el contexto de 1000.

---

## 5. Índice parcial/GIN (T14.4) — **medido, no se añade**

Latencia de `search_similar` **aislada del embedding** (`--bench-sql`, embebe una vez y
cronometra solo el SQL):

| Componente | Latencia media |
|------------|----------------|
| `search()` completo (embed + SQL) | ~1320–1508 ms |
| **SQL puro** (`search_similar`, filtro JSONB + MMR + hidratación) | **~14–15 ms** |

El embedding local (`nomic-embed-text` con `keep_alive:0`, que recarga el modelo en cada
llamada) domina el **~99%** del tiempo. El SQL con filtro JSONB sobre `metadatos->>'sector_gics'`
es de ~14 ms a esta escala (25 docs). **Decisión: no se añade índice** —no movería la aguja y
complicaría el esquema— coherente con ADR-012 §2 (índice opcional, solo si el corpus crece).

---

## 6. Persistencia web "solo lo citado" (T14.5, DT-020) — **mejora medible**

Rediseño del ciclo de vida web (enfoque *session ingest + purga*, ADR-013):

- Los chunks web se etiquetan con `session_id` de la corrida al ingestarse.
- Al ensamblar, `promote_cited_web` conserva solo los citados (∈ `chunks_usados`): les quita
  `session_id` y los marca `promoted=true`; borra el resto de la sesión.
- `sweep_stale_web_sessions` (al inicio de cada corrida) limpia huérfanos de crashes previos.
- `purge_unused_web_backlog` (única) borra el backlog legacy (sin `session_id` ni `promoted`).

### Purga del backlog histórico

| | total chunks | web |
|---|---|---|
| Antes | 4001 | 1202 |
| Después de la purga | 2799 | 0 |

### Efecto en el retrieval (filtered, producción)

| | chunks correctos (avg) | precision | contaminación |
|---|---|---|---|
| Antes de la purga | 3.20 | 1.000 | 0.000 |
| **Después de la purga** | **3.68** (+15%) | 1.000 | 0.000 |

**Mejora medible:** purgar el backlog web **liberó slots de contexto** que antes ocupaban
chunks web sin sector (puntuaban 0.80–0.83 pero no aportaban al sector); ahora afloran ~0.5
chunks sectoriales correctos más por consulta (3.20→3.68), manteniendo precision 1.0 y
contaminación 0.0. En modo raw las métricas no cambian (el web no competía en top-10),
confirmando que la purga elimina peso muerto sin afectar la calidad negativamente.

---

## 7. CIIU→GICS para acotar/validar la clasificación (T14.6, DT-023)

- `src/ic/shared/constants/ciiu_gics.py`: `ciiu_to_seccion` (CIIU numérico → Sección CIIU Rev.4
  por rangos de división) y `ciiu_to_gics_candidates` (Sección → códigos GICS candidatos vía
  `Comparacion_GICS_CIIU.csv`, con matching por solapamiento de tokens, robusto a variaciones
  de nombre como "Fideicomisos … de capital" vs "… — REITs").
- `ClassifyGICS` ahora, si se conoce el CIIU: (a) **acota** inyectando los candidatos como
  pista al prompt, y (b) **valida/corrige** —si el LLM no emitió código explícito y el nombre
  resuelto cae fuera de los candidatos, corrige al primer candidato; si emitió código explícito,
  lo respeta (solo registra)—. `chain_02_gics` endurecido para emitir "(GICS XXXX)". Se conserva
  el fallback por nombre de `extract_gics_code` (ADR-012 §4).
- Verificado con ≥5 CIIU reales (incl. **Comfama 8430 → Sección O → candidato 2020**).

---

## 7.bis Verificación E2E (Comfama, CIIU 8430)

Informe completo generado con el pipeline real (`run_pilot.py`, 247.5 s, $0, 2 referencias):

- **CIIU→GICS end-to-end:** el prompt endurecido hizo que el LLM emitiera código **explícito
  "(GICS 4030)"** (Seguros, coherente con la naturaleza de caja de compensación de Comfama). La
  validación detectó que 4030 ∉ candidatos del CIIU 8430 (`['2020']`) y —según la política
  conservadora— **respetó el código explícito del LLM** (solo lo registró). Comportamiento
  correcto: el CIIU es una guía, no una imposición.
- **Persistencia web:** `web` en BD = **0** antes y después del informe. El informe se sustentó
  en el corpus sectorial (referencias Ruta N); ningún chunk web fue citado, por lo que ninguno
  persistió y los chunks web de la corrida (etiquetados con `session_id`) se purgaron. Confirma
  que el conteo web **no crece** con búsquedas descartadas (DoD). El camino de *promoción* de
  web citada queda cubierto por el test slow `test_promote_cited_web_...`.

---

## 8. Retos encontrados y cómo se resolvieron

1. **El baseline ya era óptimo (filtered).** No había headroom en precision/contaminación; la
   evaluación sirvió para *confirmarlo con números* y para rechazar cambios que degradaban
   (MMR) o no aportaban (índice). La mejora medible vino de liberar slots vía la purga web.
2. **Bug de f-string en SQL JSONB.** En la concatenación implícita de literales solo el primero
   es f-string; el segmento con `{{...}}` quedaba literal → JSON inválido. Resuelto usando
   `jsonb_build_object('promoted','true')`.
3. **Confusión promovido/legacy.** Si al promover se quitaba `session_id` sin más, los chunks
   citados eran indistinguibles del backlog legacy y la purga los borraría. Resuelto marcando
   `promoted=true` en los promovidos; la purga solo toca los que no tienen ni `session_id` ni
   `promoted`.
4. **Matching de nombres GICS del CSV.** La contención literal fallaba en nombres divergentes;
   se cambió a solapamiento de tokens significativos (sin stopwords).
5. **Higiene de tests slow.** `test_purge_unused_web_backlog` invoca la purga global (borra todo
   el backlog legacy). En régimen permanente `legacy=0` (todo chunk web nace con `session_id` y
   se promueve o se borra), por lo que es idempotente y seguro; documentado en el test.

---

## 9. Recomendaciones / follow-ups

- **keep_alive del embedder:** el 99% de la latencia es recarga del modelo `nomic-embed-text`
  (`keep_alive:0`). Para lotes grandes (re-ingesta, harness), evaluar `keep_alive` positivo
  temporal → aceleraría re-chunking y evaluación 10–50×. (No se cambió aquí por la política de
  VRAM de ADR-006; evaluar como toggle de lote.)
- **Gold set más rico:** 1 consulta/sector es suficiente para el techo actual; si el corpus
  crece a varios documentos por sector, ampliar a consultas multi-intención y añadir juicios de
  relevancia a nivel de chunk para medir recall real (no proxy por documento).
- **MMR:** re-evaluar si se incorpora un corpus con múltiples documentos por sector (ahí sí
  aportaría diversidad).
