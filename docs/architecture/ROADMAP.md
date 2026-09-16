# 🗺️ ROADMAP — canónico

> **Roadmap vivo y ÚNICO** (consolidación 2026-08-03). Unidad de trabajo = **DT-NNN**; las "Fases"
> son historia. No es inmutable (a diferencia de los ADR).
>
> - **Historia detallada de fases y DT:** `docs/decisions/FASEN_HALLAZGOS.md` + el tracker
>   pormenorizado `ROADMAP_FASE9+.md` (congelado ~F22/DT-064; tabla completa de DT-004..064).
> - **Estado/decisiones activas:** memoria `project_roadmap_ago2026` + `project_historial_fases`.

## Estado actual (2026-08-06)

Rama `develop`. Últimos hitos (esta línea de trabajo, DT-050→):
- **Despliegue en servidor local (2026-08-06):** UI Streamlit operativa en `http://192.168.0.99:8503`
  (contenedor `informesauto_streamlit`, `docker-compose.server.yml`). Reusa servicios compartidos:
  Postgres+pgvector `repositorio_postgres_server` (db `repositorio_ctie`, esquema dedicado
  `informes_ic`, KB migrado por `pg_dump`/`pg_restore` — 115k entidades/26k embeddings) y Ollama del
  host (`nomic-embed-text`). Fix `Dockerfile.streamlit` (faltaba el CSV CIIU→GICS de runtime).
  Runbook: `docs/runbooks/DESPLIEGUE_SERVIDOR.md`.
- **Estilo — estandarización (2026-08-06):** (1) la data local de StartIA venía en MAYÚSCULAS y dejaba
  la subsección "Startups y Disruptores" gritando → `soften_caps` (`shared/text_utils.py`, puro:
  Title Case que preserva acrónimos BYD/AES en nombres, caja de oración en descripciones; solo actúa
  sobre texto "gritado") aplicado en `seccion21_assembler._ficha_prosa`. (2) Cap 5 Convergencia usaba
  tono imperativo ("La empresa debe migrar/desarrollar/incorporar") porque `SYSTEM_PROMPT_06`/`_06A`
  **prohibían "podría"** y exigían "tono directo" → reescrito a **PROPOSITIVO** (documento de
  recomendación; decide el lector): quitada la prohibición de "podría", prohibido el imperativo/
  obligación ("debe"/"tiene que"/"implemente"). Mismo tratamiento en **Cap 6 Accionables**
  (`SYSTEM_PROMPT_07`/`USER_PROMPT_07`): título como etiqueta neutra + cuerpo propositivo, sin mandato.
  Tests: `test_text_utils.py` (soften_caps).
- **DT-UI04b — Tier local vacío → anclaje local multi-sector (CERRADO 2026-08-06):** causa raíz de
  config (flags ausentes de `.env`, no bug de código) + fix de routing multi-sector para que una
  eléctrica clasificada en Energía(1010) vea sus pares curados de Utilities(5510). E2E ERCO OK
  (Enerbit/EPM/Isagen en 2.1.2). Valida además UI04c/UI04a en el mismo `.docx`. Ver la sección
  DT-UI04b abajo y `DT_UI04b_HALLAZGOS.md`.
- **Higiene de suite (2026-08-05):** suite `not slow` al **100% verde** (630 passed, 2 skipped, 14
  deselected=slow). Se corrigió el único test que fallaba desde días atrás (`test_fase15_gate.py`):
  no era bug de código sino rutas obsoletas — `fase15_budget.json` y `fase14_final_filtered.json` se
  movieron a `docs/decisions/archive/` en la consolidación de doc (commit `785f79b`) y el test seguía
  apuntando a la ruta vieja. Fix = re-apuntar a `archive/` (reactiva además un test que se saltaba en
  silencio). Los 14 `slow` (Ollama/red real) se corren antes de release, no en cada cambio.
- **DT-UI04c — Cap 3 (y todos los caps narrativos) inician con gibberish/código (CERRADO 2026-08-05):**
  saneo determinista `strip_preamble()` en `shared/text_utils.py` (poda cercas ``` /JSON antes del
  primer encabezado; conserva prosa legítima; desenvuelve documentos envueltos en cerca), aplicado en
  `generate_tendencias/ecosistema/convergencia/accionables/resumen_ejecutivo` tras el `invoke` y antes
  del guard CJK. Prevención: `SYSTEM_PROMPT_04` prohíbe explícitamente bloques de código. Tests:
  `tests/test_text_utils.py` (6) + `test_tendencias.py` (strip en execute + prompt). No se tocó el juez
  (el saneo evita que el gibberish llegue al `.docx`).
- **DT-UI04a — Empresa focal aparece como su propia competencia (CERRADO 2026-08-05):** filtro real en
  el repo (no en el prompt): `exclude_nombre` en `list_competidores_by_sector` y `list_locales_by_sector`
  (`entidad_repo.py`), match robusto a sufijos societarios y acentos (`_clave_exclusion`:
  `normalize_entity` + sin acentos → "ERCO ENERGÍA S.A.S." ≡ "ERCO ENERGIA"). `generate_n1.py` pasa
  `exclude_nombre=e` en los anclajes global/regional/startup + el guard de descubrimiento. Tests:
  `test_kb_entidades.py` (competidores + locales).
- **DT-UI02 — Selección genuina Caps 3–6 (CERRADO, commit ad140a3):** `caps_incluidos: set[str] | None`
  en `InformeParams`; DAG de dependencias (Cap 6→5→3+4) con auto-activación en UI + info al usuario.
  `_fns` en `generate_n1.py` filtradas; `_run_n2` condicional con guardas `run_cap5`/`run_cap6`.
- **DT-UI03 — Cap 2: prosa + web enrichment globales + mercado sin tabla (CERRADO, commit 7499053 +
  fix chain_judge 2026-08-05):** fichas 2.1 en mini-párrafo `**Nombre** *(País)* — desc` (antes tablas
  10 columnas con 70% "No disponible"); radar desconectado del pipeline (código preservado en
  `radar_chart.py`); sección 2.3 en texto corrido sin tabla regional; `_enriquecer_globales_web()`
  busca top-3 globales con campos vacíos y persiste hallazgos al KB. **Bug encontrado post-deploy:**
  el juez de calidad (`chain_judge.py`) tenía criterio F que exigía tablas+radar → forzaba al revisor
  a revertir al formato viejo. Corregido hoy: criterio F actualizado a "prosa NO tablas, sin radar,
  2.3 en texto corrido".
- **DT-049 — Frente Evidencia: retrieval/citación** (**CERRADO**, E2E OK): el `.docx` citaba ~9 refs.
  Diagnóstico con números: la palanca **no** era el umbral (0.70 inerte — las reservas ya inyectan
  diversidad a 0.5) sino **`top_k` + `min_distinct_docs`**. Cambio config-only: `rag_top_k` 10→16,
  `rag_min_distinct_docs` 5→8, `rag_similarity_threshold` 0.70→0.60. E2E Alpina 1040:
  **9 → 14 refs (+56%)**, anti-mezcla `ajeno=0`, radar presente. El "bug" `pdf_manual` no era bug
  (documento único legítimo). **Citación:** autor corporativo del Informe de Convergencia + 25
  sectoriales corregido a **"Ruta N Medellín"** (2625 chunks + ambos scripts de ingesta). Globales
  siguen M=0 (evidencia web-por-competidor, frente aparte). Detalle: `DT049_HALLAZGOS.md`.
- **DT-066 — Sección 2.1 KB-driven determinista (B2)** (**CERRADO**, E2E + re-verificación OK): la tabla
  de Jugadores Clave se **ensambla desde los hechos del KB** (`seccion21_assembler`), el LLM solo
  rellena huecos desde evidencia (`chain_03b_ficha_fields` + `seccion21_holes`) y redacta la prosa
  2.2/2.4/2.5 + radar. Elimina el round-trip con pérdida y el spam de "Dato no disponible" (regla de
  colapso de vacíos). Detrás del flag `seccion21_determinista_enabled` (OFF = invariante). Detalle:
  `DT066_HALLAZGOS.md`.
- **Competidores/KB** (cerrado): DT-050 (local EMIS/StartIA), DT-056 (KB entidades), DT-059 (auto-revisión),
  DT-061/062/063 (descubrimiento producto-driven, 0 tabaco/cerveza), DT-064 (fichas ancladas), DT-065
  (data local → campos de ficha + **fix del bucle de veneno**: parser de ausencia robusto + purga 189).
- **Modularidad Fase 1** (cerrado): caché durable por capítulo con keep-best + fallback (`commit_best`,
  `domain/kb/completitud.py`) → un capítulo degradado cae al cacheado bueno.
- **Robustez LLM** (cerrado, pendiente `.env`): guard `content=None`/`finish_reason` + `max_tokens` 32k;
  **síntesis por Gemini** (provider por tier) + fallback `openrouter/free`. Cambiar en `.env`
  `LLM_API_SYNTH_MODEL=gemini-3.5-flash-lite` (500 RPD; 2.5-flash tenía 20). Ver
  `project_llm_robustez_modelos`.

## Frentes activos (2026-08-05)

### DT-UI01 — UI modular PMV (CERRADO 2026-08-05, commit ad140a3)
`InformeParams` recibe 4 flags opcionales (`selfreview`, `discover_globales`, `anclaje_local`,
`seccion21_determinista`) como `bool | None` (None = respeta `.env`). `_setup_infra()` aplica
`Settings.model_copy(update=...)` → `generate_n1.py` sin cambios. UI Streamlit: sección "Módulos
del análisis" con checkboxes (todos ON por defecto); Caps 3–6 marcados disabled ("próxima iteración");
caché/refresh expuestos. `Dockerfile.streamlit` + `docker-compose.yml` ampliado para servicio
`streamlit` (port 8503, bind mount output/, Ollama via host.docker.internal). **Pendiente: DT-UI02
— selección de capítulos (Caps 3–6 opcionales): condicionar `_fns` en `run_n1_parallel` + assembler
tolerante a None.**

## Pruebas pendientes (validaciones que faltan)
0. ✅ **CERRADO 2026-08-04 — E2E DT-066 (B2) + re-verificación:** Alpina 1040 con los 4 flags, EXIT=0.
   **"Dato no disponible" 25%→3%** doc-wide (**0 en la sección 2.1**); fichas 2.1 deterministas con
   datos reales del KB; 0 competidores tabaco/cerveza; radar renderizado. Detalle: `DT066_HALLAZGOS.md`.
1. ✅ **HECHO 2026-08-03** — E2E Gemini síntesis (`gemini-3.5-flash-lite`): Alpina EXIT=0, 0 crashes,
   Cap 1 completo (9 subsecciones), 2.1.1 = 8 globales food (0 tabaco/cerveza). `output/alpina_gemini.docx`.
2. ✅ **HECHO 2026-08-05 — E2E DT-UI03 con ERCO ENERGÍA SAS (EnergyTech, GICS 5510):** Cap 1 excelente
   (LinkedIn + fuentes web; StartIA citada como "Ruta N Medellín, 2026"); 2.1 ya en prosa (fix chain_judge
   mediante); Cap 3 tendencias relevantes con buenos casos de éxito. **Bugs abiertos:** ver DT-UI04 abajo.
3. **E2E Fase 1**: un capítulo degradado cae al cacheado bueno (fallback); re-corrida reusa.
4. **E2E DT-064/065 con KB limpio**: Alpina 1040 + Emtelco full → fichas con datos reales, 0 veneno,
   0 cerveza/tabaco, tiers regional/startup pre-llenados por data local.
5. **Re-medir cobertura `domain/`** (base F19 = 69%).
6. ✅ **RESUELTO** — empresa focal en su propia tabla: el SYSTEM_PROMPT_03 ya tiene la regla; el LLM
   la incumple esporádicamente (DT-UI04a). Fix real: filtrado en repo/N1, no solo instrucción al LLM.

## DT-UI04 — Bugs y mejoras detectados en E2E ERCO (2026-08-05)

Bugs encontrados en la corrida de validación con ERCO ENERGÍA SAS (EnergyTech / GICS 5510):

### DT-UI04a — Empresa focal aparece como su propia competencia (✅ CERRADO 2026-08-05)
~~El LLM incluye a ERCO ENERGÍA dentro de sus propios competidores.~~ **Resuelto:** filtrado en el
repo (`exclude_nombre` en `list_competidores_by_sector`/`list_locales_by_sector`, match sin acentos ni
sufijos societarios vía `_clave_exclusion`); `generate_n1.py` pasa `exclude_nombre=e` en los tres
anclajes + guard de descubrimiento. Tests en `test_kb_entidades.py`. Pendiente: verificar en E2E ERCO.

### DT-UI04b — Tier local (2.1.2/2.1.3) vacío pese a datos presentes (✅ CERRADO 2026-08-06)
Detalle completo: **`DT_UI04b_HALLAZGOS.md`**.

**Causa raíz (config, no código):** los flags `ANCLAJE_LOCAL_ENABLED`,
`SECCION21_DETERMINISTA_ENABLED` y `DISCOVER_GLOBALES_ENABLED` **no estaban en `.env`** → default
`False` → el guard `if s.anclaje_local_enabled and g_code:` cortaba el anclaje local entero. Todas las
sospechas heredadas (JOIN `es.sector_gics`, `g_code`, ausencia de datos) fueron **refutadas** con
reproducción aislada contra la BD real: `list_locales_by_sector("5510")`/`("3510")`/`("1010")`
devuelven 6+6 jugadores; `extract_gics_code` resuelve bien; los tres sectores están poblados.

**Segundo hallazgo (routing de sector):** al habilitar los flags, ERCO — que el usuario aclara **es
Energía (1010), no Servicios públicos** — llenaba el tier local con **pares irrelevantes**
(minería/construcción), porque en GICS canónico las eléctricas (incl. solar) son **Utilities (5510)**,
no Energy (1010 = petróleo/gas/minería), y la data curada (EPM, Celsia, Isagen) fue sembrada bajo 5510
(el seed usa `ciiu_division_to_gics`: D3511 → 5510). **Fix = anclaje local multi-sector:**
`sectores_ancla_local(g_code, ciiu)` (grupo del LLM ∪ grupo canónico del CIIU por división);
`list_locales_by_sector` acepta `str | Sequence[str]` (`ANY(:sectores)` + re-rank por solape + **dedup
por nombre**, que colapsa "ERCO ENERGIA"×2); `generate_n1` toma el CIIU de `ctx.empresa.actividad_ciiu`.
HolaDr sin regresión (8690→3510 = mismo sector). Tests: `test_fase14_ciiu_gics.py` +
`test_kb_entidades.py`; suite `not slow` **638 passed**.

**E2E validado (ERCO `--ciiu 3511 --refresh`, 2026-08-06):** 2.1.2 Regionales = Enerbit, EPM, Isagen,
Neu Energy, BTG Pactual Energía, Vervantis (¡pares energéticos reales vía 5510!); startups = GOLDEN
ENERGY, ECOCITY, TELEMETRIK, COVATIO, ECOLUMEN; globales (discover web) = BYD, EDF Renewables, First
Solar, Fluence, AES, CATL, Enel Green Power. **UI04c** validado en el mismo `.docx` (los 6 capítulos
inician con prosa/encabezado, cero gibberish). **UI04a** validado (ERCO no aparece en ningún tier).
**HolaDr `--ciiu 8690` validado también:** 2.1.2 = Angiosur/Expert Médica/IQ Interquirófanos/Clínica
Sandiego/Neurum/Genezen; startups healthtech (TERAL/COCO/SUNUBE…); globales Doctolib/Ping An/Teladoc;
sin regresión (3510); UI04c/UI04a OK ("HOLADR." quedó fuera del top-6, no como propia competencia).

**Deuda descubierta:** (a) "HOLADR." (forma pegada) NO se excluye contra "HOLA DOCTOR S.A.S." (sin
tokens en común → endurecer UI04a por **aliases**, no por tokens); (b) duplicados KB (ERCO×2, ENERGY
MASTER×2) → DT-050b; (c) fichas y anclaje **global** (2.1.1) siguen single-sector.

### DT-UI04c — Cap 3 inicia con texto tipo código/gibberish (✅ CERRADO 2026-08-05)
~~La primera línea del Cap 3 en el `.docx` ERCO era texto similar a código.~~ **Resuelto:** (1) regla
en `SYSTEM_PROMPT_04` que prohíbe bloques de código; (2) `strip_preamble()` en `shared/text_utils.py`
(saneo conservador: poda cercas ``` /JSON antes del primer encabezado, conserva prosa legítima),
aplicado en los 5 use cases narrativos (tendencias/ecosistema/convergencia/accionables/resumen).
Tests: `test_text_utils.py` + `test_tendencias.py`. Pendiente: verificar en E2E ERCO/HolaDr.

### DT-UI04d — Web enrichment globales: validar que dispare y mida impacto (MEJORA)
`_enriquecer_globales_web()` está implementado pero no fue posible validar si corrió para ERCO
(sector 5510 sin tiers anclados en KB → B2 cae a modo LLM, la función puede no disparar). Añadir
log visible en la UI (contador "X competidores globales enriquecidos desde web") para trazabilidad.
Además, cuando B2 cae a modo LLM por KB vacío, los globales igualmente podrían buscarse en web
antes de invocar el LLM para enriquecer el prompt.

### DT-UI04e — Contenido globales 2.1 pobre en sectores sin corpus EMIS suficiente (MEJORA)
Para EnergyTech (sector 5510), el corpus EMIS tiene documentos pero la evidencia sobre competidores
globales (Enel, Iberdrola, Nextracker, SolarEdge) es escasa. La búsqueda web por los top-3 es la
palanca correcta; una vez funcione DT-UI04d, este problema debería mejorar. Complementar con queries
web más específicas por empresa+sector en el paso de retrieval de benchmarking.

---

## Frentes abiertos (prioridad)
- **Frente Evidencia (DT-049 / DT-034):** el lote EMIS **YA está ingestado** (238/250 PDFs + 25 Pulso =
  264 docs, 23.816 embeddings; 10 pendientes) y el RAG lo consulta. El cuello NO es volumen sino
  **retrieval/citación** (~10 docs/sector → solo ~9 refs únicas afloran en el `.docx`) + evidencia de
  **globales** (fuera del corpus colombiano). Ver `project_rag_ingesta_paralelizacion`.
- **Paralelizar la ingesta ENTRE PDFs** (`scripts/ingest_batch.py`, hoy secuencial): el embedding
  intra-PDF ya es paralelo (F23, `embedder_max_workers`); falta paralelizar el lote de PDFs (sesión DB
  por hilo + embedders concurrentes; aplazado en FASE23 §3.2). Tarea elegida por el usuario.
- **HITL (F24/F25):** captura/aprobación humana; depende de **DT-050b** (reconciliación EMIS↔NER por NIT).
- **Estilo/documento (F26):** coherencia, Cap 5/6, numeración, estilo.

## Deuda estructural y Estado de Calidad

### Deudas Saldadas en Spec 005 (Fase 31 ? QA, Integraci?n E2E y Deuda Estructural)
| DT | Deuda | Resoluci?n (Spec 005) | Estado |
|----|-------|------------------------|:------:|
| **DT-037** | `gateway.py` >300L | Refactorizado en 4 subm?dulos (`gateway.py`, `gateway_errors.py`, `gateway_models.py`, `gateway_pricing.py`), todos <300L | **CERRADA** |
| **DT-038** | `presentation/app.py` acoplado a `data/` | Desacoplado mediante `ui_query_services.py` (0 violaciones SoC) | **CERRADA** |
| **DT-039** | `generate_informe.py` 576L | Refactorizado en 5 subm?dulos (`_informe_context.py`, `_informe_nodes_n0.py`, `_informe_nodes_n2.py`, `_informe_nodes_n3.py`, `generate_informe.py`), todos <300L | **CERRADA** |
| **DT-040** | `_PRICING` y tracking de Gemini | Modelos Gemini 2.5 + lookup cascading (`CallRecord.costo_usd: float | None`) | **CERRADA** |
| **DT-041** | Cobertura `domain/` <80% | Cobertura total de `src/ic/domain` elevada al **93%** (710 tests unitarios) | **CERRADA** |

### Deudas Pendientes / Pr?ximos Frentes
| DT | Deuda | Nota |
|----|-------|------|
| **DT-050b** | Reconciliaci?n EMIS?NER por NIT + HITL | Duplicados inertes hoy; paliados por dedup en el anclaje |
| **DT-UI04a+** | Exclusi?n focal por aliases en casos extremos | "HOLADR." vs "HOLA DOCTOR S.A.S." |
| **DT-UI04b+** | Anclaje global multi-sector y fichas | Extensi?n de `sectores_ancla_local` |

## Documentación — cómo continuar (plan explícito)

La consolidación 2026-08-03 dejó **1 roadmap canónico** (este) + memoria slim (54→14). Falta cerrar la
"documentación completa"; hacerlo en este orden:

1. **Actualizar la auditoría** (`auditoria_arquitectura.md`): es un snapshot de Fase 30/DT-063. Añadir un
   **addendum** con esta línea de trabajo (DT-064, DT-065, modularidad F1 caché, robustez gateway/Gemini)
   y **re-medir cobertura** `domain/` (`uv run pytest --cov=src/ic/domain --cov-report=term-missing -m
   "not slow" -q`) → fijar la nueva línea base (era 69% en F19).
2. **Actualizar docs obsoletos** (auditoría §P2): `docs/architecture/REGLAS_NEGOCIO.md` (RN-007/RN-013 ya
   implementadas), tabla de estado de `ADR-014` (cableado ya hecho), nota puerto 5434 en `PRIME
   DIRECTIVE.md`.
3. **Formalizar decisiones nuevas**: decidir si merecen ADR (inmutable) o solo entrada aquí — candidatos:
   **provider-por-tier + Gemini síntesis** (¿ADR-016?), **caché de contenido por capítulo / keep-best**
   (¿ADR-017?). Si no ameritan ADR, basta `ROADMAP.md` + un `HALLAZGOS`.

### Convención hacia adelante (para NO volver a regar la doc)
Al cerrar cada DT/hito:
- **(a)** Documentar hallazgos en `docs/decisions/FASEN_HALLAZGOS.md` (o `DTNNN_HALLAZGOS.md` para DTs
  grandes, patrón `DT064_HALLAZGOS.md`).
- **(b)** Actualizar **este** `ROADMAP.md` (estado + pruebas pendientes + deuda). **NO** tocar
  `ROADMAP_FASE9+.md` (congelado).
- **(c)** Añadir **1 línea** al digest `project_historial_fases` (memoria) y actualizar
  `project_roadmap_ago2026`. **NO crear una memoria de estado por fase** (fue la causa del bloat 54→14).

## Convenciones
Ver `CLAUDE.md` (TIER 1–4) y `PRIME DIRECTIVE.md`. Gate de cierre: `uv run ruff check src/ tests/` +
`uv run pytest -m "not slow" -q` en verde. Modelos solo en `.env` (ADR-002). Commits Conventional.
