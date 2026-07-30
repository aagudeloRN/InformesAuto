# Fase 23 — Hallazgos y cierre

> Enriquecimiento del índice RAG **sin reingesta** (DT-057). Rama `feature/fase23-dt057` desde
> `develop` (base `1a1a8d1`). Gate final: **ruff 0, 409 fast tests** (390 base + 19 nuevos), 2 skipped.

## §1 — DT-057: re-etiquetado + NER, sin re-embeber (cerrado 2026-07-30)

Decisión previa (usuario, 2026-07-29): si no cambia la forma (chunking/extracción) ni el modelo
(embedder), la reingesta no vale la pena (no-op por anti-dup SHA + ~2 días). DT-057 hace solo lo
barato/seguro que NO toca vectores. Lo que exige reprocesar el PDF quedó fuera → **DT-060**.

### AVANCES (con números)

**T1 — `tipo_fuente` en EMIS individuales (`687d885`).** Cierra DT-054 del todo.
- Constante `TipoFuente` (`shared/constants`) centraliza `informe_compilado`/`informe_emis`;
  eliminado el string suelto en `pdf_ingestor` y `apa_formatter`.
- `pdf_ingestor` estampa `tipo_fuente='informe_emis'` para `tipo=INFORME_EMIS` (PDFs nuevos entran
  etiquetados en documento y chunk).
- `EmbeddingRepository.backfill_tipo_fuente_emis`: UPDATE idempotente (guarda `IS NULL`, acotado a
  documentos EMIS del esquema propio) + `scripts/backfill_tipo_fuente_emis.py` (`--dry-run`).
- **Backfill aplicado en BD: 22.224 chunks + 238 documentos** etiquetados; **re-ejecución = 0**
  (idempotencia verificada en la BD real). Inventario previo: 238 docs EMIS con `tipo_fuente` NULL,
  26 sectoriales ya con `informe_compilado`.
- **Matiz de medición (honesto):** la reserva sectorial estricta ya había dejado de filtrar por
  `tipo_fuente` en Sprint B (T1a `24aef9f`), así que la etiqueta **no era un gate** — habilita
  **telemetría de mix + palanca de boost futura**. La métrica `_es_emis_individual` de
  `measure_competitor_evidence.py` cuenta EMIS individual como `sector_gics ≠ NULL AND tipo_fuente ≠
  'informe_compilado'`, condición que **NULL ya satisfacía** → el backfill no mueve esa métrica por
  sí solo (no se corrió el harness Ollama para no reportar un delta ficticio de 0). La ganancia de
  citación viene de T1a (reserva) + un boost por `tipo_fuente` que ahora es posible (futuro).

**T2 — `sectores_adicionales` → `metadatos.sectores` (`b95690f`).** Arranca DT-053 (datos).
- `EmbeddingRepository.backfill_sectores`: UPDATE idempotente (guarda `IS DISTINCT FROM`, acotado
  por título) + `scripts/backfill_sectores_adicionales.py` (lee el CSV, computa `[primario]+adic`).
- La capacidad multi-sector del retrieval ya existía (`search_similar`: `jsonb_exists(sectores)`);
  faltaba el mecanismo de activación sin reingesta. Test confirma que un doc con `sectores=[3020,
  2530]` aflora al buscar el sector secundario.
- **Corrida real: 0 docs activados** — la columna `sectores_adicionales` del `indice_emis.csv`
  está **vacía en las 238 filas**. No se inventaron mapeos (regla del prompt). **Único pendiente =
  curación humana** del CSV; el código está listo y probado.

**T3 — NER → `entidad_menciones` (`d3a20d3`).** Sustrato del KB (DT-056), sin reingesta.
- Tabla `entidad_menciones` (esquema propio, migración idempotente `ensure_*`, índice único de
  dedup `(entidad_normalizada, chunk_id)`) con provenance (documento, chunk, sector, fuente_tipo,
  fecha) y estado **candidato** (gate anti-envenenamiento RN-001).
- Wrapper NER en `infrastructure/ner/` (TIER 1 regla 5), motor spaCy por config, parser puro
  testeable. `EntidadMencionRepository.upsert_many` idempotente (`ON CONFLICT DO NOTHING`).
- **Corrida sobre el corpus completo: 23.222 chunks → 59.647 menciones candidatas**
  (20.430 entidades distintas, 25 sectores); **re-ejecución = 0** (idempotencia en BD).

### RETOS / lecciones

- **El corpus EMIS es ~79% inglés** (18.453/23.222 chunks con marcadores EN), no español. El modelo
  español (`es_core_news_md`) sobre texto inglés daba **~10.8 menciones/chunk de puro ruido**
  (MISC: "powered", "copyright", "unauthorized distribution"; ORG: "the", "licensed"). **Se detuvo
  y se consultó al usuario** (TIER 2: realidad ≠ plan) → decisión: **NER bilingüe** por idioma del
  chunk (`en_core_web_md` + `es_core_news_md`), solo etiqueta **ORG** + stoplist de boilerplate +
  filtros de OCR (letras espaciadas) y años. Ruido bajó a **~2.6 menciones/chunk**.
- **El ruido residual son publishers/fuentes**, no competidores (top multi-sector: IEA, BMI, Fitch,
  OECD, World Bank, TBRC, DANE). Es **esperado y aceptable**: el sustrato es de *candidatos* con
  provenance; el filtrado/ranking/verificación (p. ej. priorizar entidades concentradas en 1 sector
  frente a las omnipresentes) es **DT-056**, no esta ventana. No se adelantó el merge del KB.
- Modelos spaCy fijados en `pyproject.toml` como wheels de GitHub (reproducibilidad `uv sync`).

### RECOMENDACIONES

1. **Curar `sectores_adicionales`** (paso humano, DT-053): rellenar los docs transversales del CSV y
   re-correr `scripts/backfill_sectores_adicionales.py` (idempotente). Sin esto, T2 queda inerte.
2. **Boost por `tipo_fuente='informe_emis'`** en el retrieval (palanca ya habilitada por T1): medir
   con `measure_competitor_evidence.py` si sube el mix EMIS citado. Candidato a DT-054-seguimiento.
3. **DT-056 (KB)** debe consumir `entidad_menciones` con criterio de señal: descartar publishers
   omnipresentes, priorizar entidades sector-específicas de alta frecuencia, y cruzar con NIT/ciudad.
4. **DT-060 (reingesta gated por A/B)** sigue pendiente y fuera de alcance: preservar tablas/cifras
   EMIS y metadata posicional exigen reprocesar el PDF; solo si un A/B en 1 sector lo justifica.

### Verificación

- `uv run ruff check src/ tests/` → 0.  `uv run pytest -m "not slow" -q` → **409 passed, 2 skipped**.
- Backfills idempotentes verificados en BD real (re-ejecución = 0 filas en T1, T2, T3).
- Sin `docker compose down -v`, sin re-embeber, sin pérdida de datos.

---

## §2 — Prompt de arranque de la siguiente ventana

El usuario decide entre **DT-056 (KB de entidades)** y **DT-060 (revisión RAG + reingesta A/B)**.
Recomendación: **DT-056** — el sustrato `entidad_menciones` ya está poblado (59.647 candidatos) y es
el mayor apalancamiento sobre el problema de competidores; DT-060 es más caro y gated por A/B.

### (Opción recomendada) Prompt — DT-056: KB de entidades (merge/verificación sobre el sustrato)

```
## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto): informes de
inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas). DT-057
está CERRADO y mergeado (rama feature/fase23-dt057): tipo_fuente EMIS (T1), mecanismo multi-sector
(T2, 0 docs por CSV vacío), y el SUSTRATO `entidad_menciones` poblado por NER bilingüe (T3):
59.647 menciones candidatas, 20.430 entidades distintas, 25 sectores, con provenance
(documento_id, chunk_id, sector, fuente_tipo) y estado 'candidato'. Gate base: ruff 0, 409 tests.

Hoy ejecutas DT-056 — KB de entidades: merge/verificación sobre el sustrato ya poblado. Rama nueva
`feature/fase24-dt056` desde develop (tras mergear DT-057).

## RESTRICCIONES (CLAUDE.md TIER 1)
- Sin nombres de modelo en código (config/.env/routing, ADR-002). domain/ no importa
  SQLAlchemy/httpx/Streamlit; acceso a librería externa por wrapper en infrastructure/. Sin
  credenciales. BD compartida: esquema propio SIEMPRE; NUNCA `down -v`; migraciones idempotentes
  `ensure_*`; datos en bind mount.
- RN-001 / gate anti-envenenamiento: provenance por campo + estado candidato/verificado. Una
  mención mal extraída NO se reusa como hecho. Prioridad conflicto: usuario > emis/db_oficial > web.
  Clave dedup: NIT (fallback nombre normalizado + ciudad/país). NO re-litigar ADRs cerrados.
- Cambios atómicos: 1 commit por tarea, gate verde tras cada uno (ruff 0 + pytest -m "not slow").
  Plan Mode (toca esquema BD + agregación sobre datos reales).

## TAREAS (criterios de éxito; afinar en Plan Mode con el usuario)
T1 — Entidad canónica + atributos con provenance: tablas `entidades` (+ `entidad_atributos` o
  JSONB con lineage) en esquema propio, migración idempotente. Clave NIT / fallback nombre+ciudad.
  Estado candidato/verificado. Ver PROPUESTA_KNOWLEDGE_BASE.md §1.1.
T2 — Agregación/merge desde `entidad_menciones` → entidades candidatas: dedup por
  entidad_normalizada, descartar publishers omnipresentes (heurística de señal: aparece en muchos
  sectores = ruido; concentrada en 1 sector = competidor probable), ranking por frecuencia/chunks.
  Parser/agregador puro testeable. NO fabricar: solo consolidar lo presente.
T3 — Anclaje de competidores (cierra causas A/E del diagnóstico): el pipeline identificar→enriquecer
  (T22.4, chain_02b) consulta el KB por sector_gics para la lista canónica ANTES de buscar. Cablear
  en generate_benchmarking / generate_n1 sin romper el path B1 (None = comportamiento actual).
T4 — Enriquecimiento "base viva": cada corrida nutre el KB con la empresa principal (campos con
  provenance; web entra como candidato). Riesgo: sin gate, error sistemático (RN-001 a escala).

## PRUEBAS POR TAREA (gate = ruff 0 + pytest -m "not slow")
- Migración idempotente (fake engine, IF NOT EXISTS). Merge/agregador puro (fixtures de menciones).
- Anclaje: mock del KB devuelve competidores; el chain los usa. Gate candidato/verificado.

## DONE
1. KB poblado desde el sustrato con provenance + estado; publishers filtrados; competidores por
   sector consultables. Anclaje cableado sin romper B1. 2. Gate verde (≥409 + nuevos). 3. 1 commit
   atómico por tarea. 4. Roadmap/memoria actualizados (DT-056 hecho, enlaces DT-057/054/059). 5.
   Decidir siguiente ventana con el usuario (DT-059 loop auto-revisión o DT-060 reingesta A/B).

## REGLAS DURAS (checklist)
- [ ] ¿Reingiero/re-embebo o reproceso un PDF? → PARAR (DT-060). Esta ventana NO toca vectores.
- [ ] ¿Migración idempotente en esquema propio? ¿Sin `down -v`?
- [ ] ¿Toda entidad/atributo con provenance + estado candidato/verificado (RN-001)?
- [ ] ¿Sin nombre de modelo en código? ¿Sin credenciales? ¿Gate verde tras cada commit?

## LECTURAS OBLIGATORIAS
- docs/architecture/PROPUESTA_KNOWLEDGE_BASE.md §1 (KB), §0 (diagnóstico competidores).
- docs/decisions/FASE23_HALLAZGOS.md (este cierre + números del sustrato).
- Código: data/models/entidad_mencion.py + data/repositories/entidad_mencion_repo.py (sustrato),
  infrastructure/ner/entity_recognizer.py, domain/chains/chain_02b_entidades.py +
  use_cases/generate_benchmarking.py (anclaje), PROPUESTA_BASE_EMPRESAS.md (DT-050, NIT/criterios).
- memory: project_kb_entidades_plan, project_fase23_dt057_estado.

## CIERRE DOCUMENTADO
AVANCES/RETOS/RECOMENDACIONES con números (entidades consolidadas, publishers filtrados,
competidores por sector) en docs/decisions/ y en el memory de la fase. Dejar el prompt de la
siguiente ventana con esta MISMA estructura.
```

### (Alternativa) DT-060 — revisión RAG + reingesta gated por A/B
Ver la fila DT-060 del roadmap: metadata posicional, chunking estructural, tablas/cifras EMIS,
doc-summary vector, (tras benchmark) embedder. Regla dura: cambiar pipeline → reingerir **1 sector**
→ A/B con `eval_retrieval.py` → escalar solo si sube precisión + mix. Requiere el update-path de
DT-053. Más caro; solo si el A/B lo justifica.
