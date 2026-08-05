# DT-049 — Frente Evidencia: retrieval / citación (diversidad de referencias) — Hallazgos

> Sesión 2026-08-04 (rama `develop`). Sucesor de `DT066_HALLAZGOS.md`. Roadmap vivo: `ROADMAP.md`.
> Estado/decisiones: memoria `project_roadmap_ago2026`, `project_rag_ingesta_paralelizacion`.

## Problema (por qué)

El `.docx` final citaba solo **~9 referencias únicas** pese a 238 PDFs EMIS ingestados (+ web). La
hipótesis del usuario ("~10 docs/sector × 25 sectores → el informe tira solo del puñado de su
sector") era correcta en el *síntoma* (pocas refs) pero el mecanismo real había que medirlo. El
frente NO es de ingesta (el corpus ya está ingestado: 264 docs locales, 23.816 embeddings) sino de
**retrieval/citación**: por qué no afloran más docs de los que el sector tiene.

## Diagnóstico (con números, read-only primero)

Medición directa sobre el índice real (`nomic-embed-text`, español), tres frentes:

### 1. El umbral 0.70 estrangula el *pool base* — pero es INERTE en el path real
Sonda SQL cruda por umbral (sector 3020, 14 docs / 286 chunks en índice):

| Umbral | chunks | docs distintos |
|-------:|-------:|---------------:|
| 0.70 (actual) | 9 | **1** |
| 0.60 | 40 | 3 |
| 0.55 | 91 | 10 |
| 0.50 | 177 | 14 |

Parecía la palanca. **Pero al medir el path `search()` real, 0.70 y 0.60 devuelven los mismos docs
distintos** (3020: 5 y 5; 2020: 6 y 6). Causa: las **reservas** (sector/global) corren a
`t_reserve = min(t, 0.5) = 0.5`, no al umbral general → inyectan la diversidad independientemente del
umbral principal. Bajar el umbral agranda el pool de candidatos (mejor material por doc) pero **no
mueve la aguja de las referencias**. Corrección honesta de la hipótesis inicial.

### 2. La palanca real: `top_k` + `min_distinct_docs`
Medición del path `search()` variando parámetros (docs distintos por query):

| Config | 3020 | 2020 | 5010 | 4510 |
|--------|-----:|-----:|-----:|-----:|
| base (tk10, mdd5) | 5 | 6 | 4 | 4 |
| **tk16, mdd8** (elegido) | **8** | **9** | **7** | 4* |
| tk20, mdd10, max3 | 10 | 11 | 8 | 5* |

(*4510 solo tiene 3 docs en índice → tope del corpus.) `sector_reserve` 3→6 no aporta nada
(`min_distinct_docs` ya lo domina). `max_chunks_per_doc=2` se conserva.

### 3. `pdf_manual` NO era un bug (Chesterton's fence)
`build_references_section` deduplica por `fuente_url`. Los 1033 chunks de `pdf_manual` colapsaban a
**1 referencia** — pero es correcto: son un **único documento** ("Informe Convergencia Local 2026").
Los EMIS `pdf` tienen 253 `fuente_url`/`documento_id` distintos → dedup correcto. No hay bug; se
descartó la "Fase 3" que habría partido un documento real en refs falsas.

### 4. Globales (fuera de alcance de este frente)
`hole-filling: 8 procesados, 0 con datos nuevos` (M=0): EMIS es corpus colombiano → no soporta los
campos de fichas de globales (Danone/Kraft Heinz). Su evidencia es **web dirigida por competidor**,
frente separado. El retrieval sectorial no lo toca.

## Cambios aplicados (config-only, TIER 1 OK — params de tuning, no nombres de modelo)

- `rag_top_k` **10→16** y `rag_min_distinct_docs` **5→8** (la palanca): casi duplica docs distintos
  por query donde el corpus los tiene. +60% de contexto de retrieval por capítulo (coste moderado).
- `rag_similarity_threshold` **0.70→0.60**: inofensivo (sin regresión de precisión/contaminación),
  enriquece el pool de candidatos. No es la palanca pero acompaña.
- En `config.py` + `.env` + `.env.example`, con comentarios que documentan la evidencia.

### Citación del Informe de Convergencia + sectoriales Ruta N (petición del usuario)
El autor corporativo es **"Ruta N Medellín"** (no la persona "Juan Sebastián Rodríguez Cuartas").
Se descubrieron **2 copias** del PDF de convergencia (una `pdf_manual` no citada, autor era la
persona; una **global** `informe_compilado` citada, autor "Ruta N") + **25 "Informe sectorial: X"**
compilados (autor "Ruta N"). Fix uniforme: **todo `autor='Ruta N'`/persona → "Ruta N Medellín"**
(autor + fuente_nombre) — **2625 chunks / 27 docs** en BD. Durabilidad: default corregido en
`scripts/ingest_global.py` (`_DEFAULT_AUTOR`) y `scripts/ingest_batch.py` (fallback del CSV).
Cita inline resultante: **(Ruta N Medellín, 2026)**.

## Validación

- **Retrieval (read-only):** `eval_retrieval --mode filtered` a 0.60 → precisión **1.0**,
  contaminación **0.0**, sin regresión. Docs distintos por query duplicados (§2). Snapshot:
  `docs/decisions/dt049_retrieval_060.json`.
- **E2E dirigido** (Alpina 1040, 4 flags, `output/alpina_dt049.docx`, `logs/e2e_dt049.log`): **EXIT=0**,
  1151.8s. **Referencias: 9 → 14 únicas (+56%)**. Anti-mezcla `on_sector=16 exento=56 ajeno=0` (0
  contaminación cross-sector con el umbral 0.60). Radar **PRESENTE (6 competidores)**. B2 activo
  (`entidades competidoras: 8, KB=8`). "no disponible" = 13 (en tablas 2.3/5.4 que aún redacta el
  LLM, 0 en 2.1). *(El `.docx` se generó antes del fix de citación → aún muestra "Ruta N"; una
  corrida fresca mostrará "Ruta N Medellín" — la BD ya está corregida.)*
- **Gate:** `ruff` 0 (src/ + scripts tocados); `pytest -m "not slow"` = **618 passed, 3 skipped**;
  único fallo `test_fase15_budget_file` = **pre-existente ajeno** (fase15_budget.json archivado en
  785f79b). Cambios config-only → sin lógica nueva → sin tests nuevos.

## PROBLEMAS / DEUDA detectados

- **Duplicado del PDF de convergencia** (2 ingestas: `pdf_manual` 1033 chunks + `pdf` global 594):
  data-hygiene, territorio DT-060 (reingesta A/B). Hoy solo la copia global se cita; ambas quedan
  con autor consistente. No urge.
- **Coste API $0** (Gemini sin trackear): deuda DT-040 conocida, no de este frente.
- **Globales M=0**: la riqueza de las fichas de globales sigue atada a evidencia web-por-competidor
  (frente separado, no retrieval sectorial).
- **"no disponible" (13)** persiste en tablas 2.3 Mercado / 5.4 que aún redacta el LLM (recomendación
  #2 de DT-066, no abordada aquí).

## RECOMENDACIONES (próximos pasos, en orden)

1. **Corrida fresca de verificación de la citación** (barata si se cachea): confirmar "Ruta N
   Medellín" en el `.docx` de una nueva corrida. O regenerar solo referencias.
2. **Globales por evidencia web dirigida** (el M>0 real): extraer campos de ficha desde web por
   competidor (reusar DiscoverGlobales/corroboración), separado del retrieval sectorial.
3. **Colapsar "no disponible" en 2.3/5.4** (deuda DT-066 #2): tablas que aún redacta el LLM.
4. **Deduplicar el PDF de convergencia** (DT-060): eliminar la copia redundante para no arriesgar
   doble cita futura.
5. **Deuda estructural** (DT-037/039/040) antes de más features; DT-038 antes de HITL.
</content>
</invoke>
