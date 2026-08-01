# DT-064 — Fichas de competidores ancladas, enriquecidas, persistidas y anti-negativas

> Estado: **T1–T5 implementado y commiteado** (rama `develop`, 5 commits). Gate: ruff 0, **575 fast
> tests**. E2E de validación **pendiente** (sección al final). Sucesor de DT-063
> (`FASE30_DT063_HALLAZGOS.md`). Plan de trabajo: `DT064_PLAN.md`. Esquema de ficha:
> `DT064_FICHA_SPEC.md`.

## Contexto

El E2E de Alpina con DT-063 dejó el **conjunto de competidores anclado ya correcto** (globales lácteos
Danone/Fonterra/Kellogg's, 0 tabaco). Pero el `.docx` seguía sacando **Bavaria (cerveza) y British
American Tobacco (tabaco)** en la ficha 2.1.1. Diagnóstico validado leyendo el código:

1. **La síntesis escribía las fichas desde el RAG, no desde la lista anclada.**
   `generate_benchmarking.execute` invocaba `chain_03` con `retrieval_competidores` (RAG, contaminado
   por queries genéricas del grupo "Alimentos, bebidas y **tabaco**") + `jugadores_locales`, pero **sin
   pasar `kb_competidores`** como sujetos. El prompt decía "identifica 8 líderes globales" → el LLM los
   elegía del RAG.
2. **El self-review re-sintetizaba sin el anclaje.** `review_web_cap` → `chain_revise` solo veía
   borrador + faltantes + evidencia (RAG). Al rescatar el Cap 2 (6→11 en el E2E) reescribía las fichas
   desde el RAG → volvían Bavaria/BAT.
3. **Teníamos nombres, no datos.** Los campos de ficha se re-buscaban cada corrida; no se extraían ni
   persistían → sin memoria ni reuso sectorial.
4. **Variabilidad del modelo gratuito.** A veces rehusaba ("no es posible con las fuentes…"); no había
   detector → la negativa se emitía como contenido.

## Hallazgo transversal (paso 1 — verdad de terreno)

Se leyó la sección **2.1 Jugadores Clave** de los 5 informes manuales del cliente
(`docs/ReportesHumanos/`, NO trackeados). Resultado en `DT064_FICHA_SPEC.md`:

- **El esquema de ficha del humano es idéntico y estable en los 5 informes, e independiente del
  sector** (food y no-food usan los mismos 3 tiers y los mismos campos). Confirma que el mecanismo
  debe ser **genérico**, no food-specific.
- **Los 8 campos que ya pedía el prompt mapean 1:1** con los del humano → la brecha de DT-064 **no era
  de campos** sino de **sujetos** (T1/T2) y **persistencia** (T3/T4). Esto reorientó el trabajo: no se
  tocó el set de campos.
- **Tiers:** Referentes Globales (7-8) / Referentes Regionales LatAm-Colombia (3) / Startups (3, con
  label adaptado al sector: `Startups / FoodTech` en food, `Startups` en no-food). Nunca se omiten.

## Solución — T1 a T5

### T1 — Anclar los SUJETOS globales (`0a8e294`)
`format_referentes_globales` (puro, en `kb/relevance.py`) + slot `{referentes_globales_anclados}` en
`chain_03`: si hay globales anclados, esos son EXACTAMENTE las fichas de 2.1.1 y el RAG solo llena sus
campos. Vacío → `""` (invariante: el LLM identifica los globales del sector, como antes). Mata
Bavaria/BAT **por construcción en la generación**.

### T2 — Self-review anclaje-aware (`1464311`)
Slot `{sujetos_anclados}` en `chain_revise`; `review_web_cap` construye el bloque (globales anclados +
locales del directorio) y lo reinyecta en cada re-síntesis. `review_integration_cap` (Caps 5/6) y las
llamadas de Cap 3/4 pasan `""` → invariante. El rescate ya no revierte a RAG.

### T3 — Extraer y persistir los campos de ficha (`8bab057`)
`domain/kb/ficha_parser.py` (puro): `parse_fichas_competidores` reusa `parse_markdown` y extrae las 8
claves canónicas + tier por competidor. **Tolera dos formatos**: tabla vertical `| Campo | Valor |`
(la que emite el sistema) y tabla ancha una-fila-por-competidor (**la de los informes manuales** — key
para la siembra futura). Descarta celdas vacías o "Dato no disponible" (RN-001).
`entidad_repo.get_id_by_nombre_sector` (solo lookup). `_fn_cap2` persiste las fichas **solo de nombres
anclados** (evita persistir competidores del RAG) via `add_atributo` (idempotente, fuente=web,
candidato). Best-effort. Reusa el patrón de atributos DT-056.

### T4 — Pre-fill del prompt desde el KB (`17e910e`)
`entidad_repo.list_ficha_atributos_by_sector` + `relevance.format_fichas_conocidas` (puro) + slot
`{fichas_conocidas}` en `chain_03`. El LLM escribe DESDE hechos ya persistidos (menos fabricación,
menos negativas). Cierra el ciclo: cada corrida enriquece, la siguiente parte de más. Vacío →
invariante.

### T5 — Detector de negativas + retry + escalada (`b4a10a0`)
`text_utils.is_llm_refusal` (puro, conservador: frases de rechazo es/en **o** capítulo corto dominado
por "Dato no disponible"). `GenerateBenchmarking._redactar_con_escalada`: ante negativa/idioma
**reintenta 1× con el primario** (modelo estocástico) y, si persiste y hay `escalation_chain`, **escala
a un tier de API superior** (`build_api_llm(tier=synth)`, modelo en `.env` — ADR-002). Si aún así
rehúsa → párrafo de ausencia (no emite el rechazo; el self-review puede rescatar). La escalada corre
SOLO ante negativa confirmada tras retry → **coste acotado** (≤20 USD/mes). Decisión del usuario:
retry+escalada (frente a solo-ausencia).

## Invariantes preservados

Todos los cambios degradan a comportamiento previo cuando faltan insumos: bloques formateados vacíos =
no-op; `selfreview_enabled=False` no revisa; sin API key no hay escalada; sin KB no hay pre-fill ni
sujetos. Los flags `anclaje_local_enabled` / `discover_globales_enabled` / `selfreview_enabled` siguen
OFF por defecto.

## Archivos

- Nuevos: `src/ic/domain/kb/ficha_parser.py`, `docs/architecture/DT064_FICHA_SPEC.md`,
  `tests/test_dt064_{anclaje,fichas,negativas}.py`.
- Tocados: `chain_03_benchmarking.py`, `chain_revise.py`, `kb/relevance.py`, `shared/text_utils.py`,
  `data/repositories/entidad_repo.py`, `use_cases/{generate_benchmarking,generate_n1,self_review_hooks}.py`.

## Pendiente

### E2E de validación (diferido a lote)
- **Alpina** (`scripts/run_pilot.py --empresa "Alpina Productos Alimenticios S.A." --ciiu 1040`) con los
  3 flags: 2.1.1 = globales lácteos anclados, **0 cerveza / 0 tabaco** incluso tras el rescate; fichas
  CON datos; atributos persistidos verificables por consulta; re-corrida reusa (menos búsquedas).
- **Segundo sector NO-alimentos** (anti-sesgo, obligatorio): Emtelco/BPO o Andercol/químicos (o Sofasa
  2510 / Bancolombia 4010) → globales del dominio correcto, fichas los usan, locales re-rankeados por
  producto.
- Forzar una negativa y confirmar que **escala de tier** en vez de emitir el rechazo.

### Siembra del KB desde los informes manuales (siguiente sección)
Los 5 informes son verdad de terreno con las fichas en tablas anchas → `parse_fichas_competidores` YA
las parsea. Sembrar el KB (entidades + membresías + atributos, provenance `informe`/candidato) da a la
vez: reuso sectorial inmediato, pre-fill más rico (T4) y el **set de evaluación** (regresión medible) +
gap analysis (calibra la rúbrica v1.0). Deuda viva paralela: DT-050b (reconciliación + HITL).
