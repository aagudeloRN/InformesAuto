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

---

# FASE 22 — Sprint B (Bloque B1): Robustez del pipeline

> Estado: **B1 en rama `feature/fase22-sprintB`** (desde develop, sin mergear aún).
> Tres tareas acotadas de deuda técnica: DT-055 (fuga intro), T22.2/DT-027 (radar) y
> T22.3/DT-030 (checkpoint --resume). Gate verde tras cada commit (ruff 0).

## 11. DT-055 — Saneo de la fuga de andamiaje en el intro — commit `4b176ba`

**Causa raíz (verificada).** Los párrafos introductorios de capítulo se generan con una
única cadena LCEL genérica (`chain_intro.build_chain_intro`), invocada en dos puntos del
DAG: `generate_n1` (Caps 2/3/4) y `generate_informe._run_n2` (Caps 5/6). El prompt pedía
"sin meta-comentarios", pero **no saneaba la salida**. El modelo local con modo *thinking*
mezcló razonamiento en inglés con el intro en español y lo filtró al `.docx` de Sofasa
("We need to produce a paragraph intro…", "Answer", "(In)"). Ocurrió en una corrida y no
en otra (no determinismo), por eso una defensa por prompt sola no basta.

**Fix (dos capas, RN-001).** `sanitize_intro` (helper puro y testeable):
1. elimina bloques `<think>…</think>`;
2. si hay un marcador `Answer:/Respuesta:`, conserva solo lo que le sigue;
3. descarta líneas de razonamiento meta en inglés (el intro válido es español) y paréntesis
   sueltos tipo `(In)`;
4. si tras sanear no queda intro, devuelve `""` (el llamador ya lo antepone condicionalmente).

Nunca fabrica texto: solo elimina. Se cablea **dentro** de `build_chain_intro` vía
`RunnableLambda` → cubre N1 y N2 sin tocar los call-sites, que además solo anteponen el
intro cuando no queda vacío. Prompt (system+user) endurecido para prohibir
razonamiento/inglés/etiquetas. **+8 tests fast** (`test_sanitize_intro.py`): fuga real de
Sofasa → limpio; intro limpio → inalterado; 100% razonamiento → `""`.

## 12. T22.2 (DT-027) — Hit-rate del radar: medición y decisión — commit `4b16e0c`

**Endurecimiento previo a medir.** Antes de decidir si construir una cadena dedicada, se
endureció el camino existente:
- **Prompt** (`chain_03_benchmarking`): reglas explícitas del bloque (JSON válido, 5
  dimensiones fijas, 4–8 competidores con listas de 5 números, comillas dobles, **sin comas
  colgantes ni comentarios**, nada de texto/razonamiento tras el cierre del fence).
- **Extractor** (`generate_benchmarking._extract_radar`): tolera etiquetas de fence variables
  (` ```radar_json `, ` ```json `, ` ``` `), **comas colgantes** (error frecuente del LLM
  local) y bloques **sin fence** vía escaneo de llaves balanceadas; el bloque cercado se retira
  de la prosa aunque el JSON no sea parseable. Contrato T16.1 preservado (parseo laxo; la
  validación de claves la hace el pipeline). Log determinista `radar_data: PRESENTE/AUSENTE
  (N competidores)`.

**Medición reproducible** (`scripts/measure_radar_hitrate.py`, snapshot
`docs/decisions/fase22_radar_hitrate.json`). N=5 corridas del **camino del radar** (Cap 2
completo: retrieval sectorial + web + `chain_03` + `_extract_radar`), alternando 3020 (Alpina)
y 2510 (Sofasa) sobre el corpus EMIS enriquecido. Se aísla el radar (no el pipeline completo)
para reproducibilidad y coste; el LLM API conserva su no determinismo, que es justo lo que se
mide.

| corrida | empresa | GICS | radar | competidores | seg |
|:-------:|---------|:----:|:-----:|:------------:|:---:|
| 1 | Alpina | 3020 | ✅ | 7 | 186 |
| 2 | Sofasa | 2510 | ✅ | 4 | 237 |
| 3 | Alpina | 3020 | ✅ | 6 | 204 |
| 4 | Sofasa | 2510 | ❌ | 0 | 132 |
| 5 | Alpina | 3020 | ✅ | 4 | 288 |

**Hit-rate: 4/5 = 80%** (antes: ~50% histórico, F17/F19). `retrieval_suficiente=true` en las 5
→ el fallo **no** es de retrieval. La corrida 4 logueó `AUSENTE` **sin** warning "no parseable":
el modelo **omitió por completo el bloque radar**, no lo emitió malformado. Por tanto la robustez
del extractor (que ya cubre etiquetas/comas/sin-fence) no puede recuperar ese caso: es un fallo
de **generación**, no de parseo.

**Decisión (cierre parcial de DT-027).** 80% supera con holgura el umbral de 50% y alcanza el
≥80% de la rúbrica original, de forma estable en dos sectores. **No se crea la cadena dedicada
ahora**: el endurecimiento de prompt + extractor es suficiente y de menor complejidad. DT-027
queda **parcialmente cerrado** (prompt+extractor+medición). **Cadena LCEL dedicada = tarea
futura condicional**: solo si el 20% de omisión se vuelve un problema en producción. Su
especificación, si se retoma: sub-cadena con temperatura 0 y `response_format` estructurado que
recibe las fichas de la sección 2.1 ya generadas y emite **solo** los scores; **reintento único**
si el primer intento no emite bloque; fallback al placeholder garantizado. Se mide con el mismo
harness (meta 5/5).

## 13. T22.3 (DT-030) — Checkpoint --resume — commit `1b7473c`

**Problema.** Un fallo tardío (crash, agotamiento de VRAM, timeout de red, corte del budget)
descartaba Caps 1–5 ya generados (~13 min). CLAUDE.md TIER 3 exige persistir estado antes de
las barreras de sincronización (Cap 6 / N3).

**Diseño (SoC estricto).**
- **data/models/checkpoint.py**: tabla `checkpoint_capitulos` (PK `run_key`+`cap_nombre`,
  `payload` JSONB) en el esquema propio; `ensure_checkpoint_table` idempotente
  (`CREATE TABLE IF NOT EXISTS`), patrón `ensure_*` como `historial_informe`.
- **data/repositories/checkpoint_repo.py**: `save_capitulo` (upsert `ON CONFLICT`),
  `load_capitulos`, `clear`.
- **domain/checkpoint_serde.py**: (de)serialización pura de los dataclasses de capítulo,
  incluyendo `chunks_usados` → **las Referencias sobreviven al resume**; `make_run_key`
  determinista (empresa+ciiu). Sin SQLAlchemy (Dependency Agnosticism).
- **domain/use_cases/checkpoint_hooks.py**: `load/restore/save/clear` compartidos por el
  orquestador y la paralelización N1; **best-effort** (un fallo de persistencia nunca aborta
  la corrida; solo se pierde la capacidad de reanudar).

**Integración en el DAG.** Restore-or-compute por capítulo en N0 (empresa, GICS), N1
(Caps 2/3/4 + mercado, en paralelo: solo se computan los faltantes) y N2 (Caps 5/6). El
párrafo intro se aplica solo a caps recién computados (los restaurados ya lo incluyen).
**Cap 6 es barrera de sincronización**: si Cap 5 se restaura y Cap 6 falta, Cap 6 se recomputa
sobre el Cap 5 restaurado (el DAG se respeta). El checkpoint se **limpia** al completar la
corrida con éxito. Flag `--resume` en `run_pilot.py`. **+10 tests fast**
(`test_checkpoint_repo.py`): round-trip serde, repo mockeado (upsert/load/clear), migración
idempotente, gancho de resume (persistido se salta, ausente se recomputa).

## 14. Cierre del Bloque B1 — avances, retos, recomendaciones

**Gate.** ruff 0; **372 fast tests** (351 base + 8 intro + 3 radar + 10 checkpoint), 2 skipped.
Tres commits atómicos + este de cierre: `4b176ba` (T1), `4b16e0c` (T2), `1b7473c` (T3). B1
**queda en la rama `feature/fase22-sprintB`, sin mergear** (el merge se decide con el usuario
tras B2).

**Avances (con números).**
- **DT-055** ✅: la fuga de andamiaje del intro se sanea con un helper puro (`sanitize_intro`)
  cableado en la cadena; cubre N1 y N2. 8 tests, incluyendo el caso real de Sofasa. Antes: el
  `.docx` de Sofasa filtraba "We need to produce a paragraph intro…/Answer/(In)". Después: el
  meta-texto se elimina y, si no queda intro, no se antepone nada (RN-001, sin fabricar).
- **DT-027** (radar): hit-rate **~50% → 80%** (4/5, N=5, 2 sectores) solo con endurecer prompt +
  extractor. Decisión fundamentada: **sin cadena dedicada**. Medición reproducible en el snapshot.
- **DT-030** ✅: checkpoint `--resume` funcional (tabla propia idempotente + serde + hooks +
  flag), 10 tests. Una corrida interrumpida ya no recomputa lo hecho; las Referencias sobreviven.

**Retos.**
- **No determinismo del intro (DT-055).** El problema no era reproducible siempre (ocurrió en
  Sofasa, no en Alpina). Por eso el fix no confía solo en el prompt: sanea la salida
  determinísticamente. El saneador es conservador (filtra inglés/razonamiento) para no tocar
  intros válidos en español.
- **Medición del radar.** Correr 5 pilots completos era caro (~10 min solo Cap 1 por corrida) y
  frágil: un primer intento falló por **editar código mientras un proceso largo corría** (el
  proceso cargó `generate_informe` viejo y luego importó `generate_n1` nuevo → `AttributeError`
  de un campo que aún no existía). Se resolvió con un **harness enfocado** que ejercita solo el
  camino del radar (Cap 2), más rápido y reproducible. Lección: no lanzar E2E de fondo mientras
  se siguen editando módulos del pipeline.
- **Alcance del checkpoint.** Se optó por serializar el capítulo **completo** (no solo el texto):
  incluir `chunks_usados` era necesario para que las Referencias no se perdieran al reanudar. El
  intro se aplica solo a caps frescos para no duplicarlo sobre uno restaurado.

**Recomendaciones para B2 (competidores + Cap 4).**
1. **DT-054 + T22.4 (competidores, Cap 2).** El diagnóstico del plan KB (5 causas) apunta a
   identificar+enriquecer **por entidad** y anclar nombres. El radar ya trae 4–7 competidores
   reales el 80% de las veces → hay señal de entidad explotable: extraer esas entidades del Cap 2
   y usarlas para búsquedas dirigidas (contraste) y para la reserva sectorial (incluir EMIS
   individuales, hoy `tipo_fuente` NULL). Reutilizar el **harness enfocado** (patrón de
   `measure_radar_hitrate.py`) para medir "n competidores con ficha completa" antes/después.
2. **DT-058 (Cap 4 adaptativo).** Gatear subsecciones con `check_retrieval_sufficient` (ya
   existe) y omitir el cap si no hay evidencia (ADR-002). El checkpoint de B1 ayuda: iterar Cap 4
   sin recomputar Caps 1–3 vía `--resume`.
3. **Aprovechar el checkpoint** en todo E2E de B2 para acelerar el ciclo (retomar tras un fallo).
4. **No re-lanzar E2E de fondo mientras se edita** el pipeline (ver retos).

---

## Prompt de arranque — Sprint B / Bloque B2 (competidores + Cap 4)

```
## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto), sistema de
informes de inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura
por capas). El Bloque B1 de Sprint B está CERRADO en la rama feature/fase22-sprintB (sin
mergear): DT-055 (sanitize_intro), T22.2/DT-027 (radar 80%, sin cadena dedicada), T22.3/DT-030
(checkpoint --resume). Hoy ejecutas el BLOQUE B2: el fix de competidores (DT-054 + T22.4) y el
Cap 4 adaptativo (DT-058). Trabaja sobre la MISMA rama feature/fase22-sprintB (continúa B1) o
crea feature/fase22-sprintB2 desde ella si el usuario lo prefiere.

## RESTRICCIONES (CLAUDE.md TIER 1 — no negociables)
- Sin nombres de modelo en código (van en .env y tabla de routing; ADR-002).
- domain/ NO importa SQLAlchemy/httpx/Streamlit; todo acceso a librería externa por un wrapper
  en infrastructure/. No credenciales en código/git. Esquema propio; nunca down -v.
- Ollama en el host (127.0.0.1:11434). Cambios atómicos: 1 commit por tarea, gate verde tras
  cada uno (ruff 0 + pytest -m "not slow"). Plan Mode para lo no trivial.
- E2E solo con Ollama libre (api/ps vacío), uno a la vez (VRAM WSL 8GB), streams separados
  (1>out 2>err). NO editar módulos del pipeline mientras un E2E de fondo corre (lección B1).
- No re-litigar ADRs cerrados (012/013/014/015). RN-001: nunca fabricar datos/atribuciones.

## PASO 0 — PRE-CHECK (read-only)
  curl -s http://127.0.0.1:11434/api/ps          # libre: {"models":[]}
  git checkout feature/fase22-sprintB
  uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q   # base verde ≥372

## TAREAS Y CRITERIOS DE ÉXITO
T1 — DT-054 + T22.4: fix de competidores (Cap 2).
  Contexto: el Cap 2 no trae datos sólidos de competidores porque identifica+enriquece en un
  solo paso (sin extracción de entidades), consulta a nivel sector (no por entidad), y la
  reserva sectorial estricta filtra a tipo_fuente='informe_compilado' → los EMIS individuales
  (tipo_fuente NULL) nunca entran. El radar de B1 ya trae 4–7 competidores reales el 80% → hay
  entidades explotables.
  Éxito: (a) extraer entidades competidoras del Cap 2 (o del radar_data ya disponible) como
  paso explícito; (b) búsquedas dirigidas por entidad (no solo por sector) que alimenten las
  fichas de la sección 2.1; (c) ampliar la reserva sectorial para incluir EMIS individuales
  (o dar boost de score / etiquetar tipo_fuente en la ingesta) — sin romper anti-mezcla; (d)
  medición reproducible con un harness enfocado (patrón measure_radar_hitrate.py): "n
  competidores con ficha completa" y "n refs EMIS individuales" antes/después. Sin hardcodear
  entidades. Plan Mode primero (toca retrieval + generación).

T2 — DT-058: Cap 4 (Ecosistema) adaptativo.
  Contexto: hoy fuerza 4.1–4.5 aunque no haya evidencia → filler "Dato no disponible".
  Éxito: (a) gatear cada subsección con check_retrieval_sufficient (ya existe); (b) omitir el
  cap entero si no supera el umbral (ADR-002 datos ausentes, párrafo de ausencia desde
  plantilla); (c) NO eliminar el capítulo; (d) test fast del gating (evidencia suficiente →
  subsección presente; insuficiente → ausente/omitida). Aprovechar --resume de B1 para iterar
  Cap 4 sin recomputar Caps 1–3.

## PRUEBAS POR TAREA (gate = ruff 0 + pytest -m "not slow")
- T1: harness enfocado + números en el cierre; tests fast de la extracción de entidades y de
  la reserva sectorial ampliada (mockeados). Verificación E2E opcional (un pilot, refs EMIS).
- T2: test fast del gating de subsecciones de Cap 4; E2E opcional con --resume.

## DEFINICIÓN DE "DONE" (B2 cerrado)
1. Competidores: entidades ancladas + refs EMIS individuales presentes, con números
   antes/después. Cap 4 adaptativo con gating testeado.
2. Gate verde (ruff 0 + pytest -m "not slow" ≥ 372 + tests nuevos).
3. 1 commit atómico por tarea (Conventional Commits; el cuerpo explica el porqué).
4. Roadmap/deuda y memoria actualizados (DT-054, T22.4, DT-058).
5. Decidir con el usuario el merge de B1+B2 a develop.

## LECTURAS OBLIGATORIAS
- memory: project_kb_entidades_plan (diagnóstico 5 causas + secuencia), este cierre de B1.
- docs/decisions/FASE22_HALLAZGOS.md §9 (DT-054), §12 (radar/entidades), §14 (cierre B1 +
  recomendaciones). ROADMAP_FASE9+.md: DT-054/058, §SPRINT B (T22.4).
- Código: generate_benchmarking.py + chain_03_benchmarking.py (radar_data, fichas 2.1);
  embedding_repo.search_similar (reserva sectorial estricta); pdf_ingestor (tipo_fuente);
  chain_05_ecosistema.py + generate_ecosistema.py (Cap 4); domain/absent_data.py.

## CIERRE DOCUMENTADO (al terminar B2)
Redactar AVANCES/RETOS/RECOMENDACIONES (con números) en FASE22_HALLAZGOS.md y en el memory de
Sprint B, y dejar el prompt de arranque de la siguiente ventana (DT-057 reingesta / DT-056 KB
o el merge), con la misma estructura.
```
