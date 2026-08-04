# DT-066 — Sección 2.1 de competidores KB-driven determinista (B2) — Hallazgos

> Sesión 2026-08-04 (rama `develop`). Sucesor de `DT065_HALLAZGOS.md`. Roadmap vivo: `ROADMAP.md`.
> Estado/decisiones: memoria `project_roadmap_ago2026`.

## Problema (por qué)

La sección **2.1 (Jugadores Clave)** del Cap 2 era la pieza más sensible: el **LLM autoraba cada
celda** de las fichas. Round-trip con pérdida — hechos estructurados del KB (`entidad_atributos`) →
texto (pre-fill T4) → tabla markdown del LLM → re-parseo (T3) — **no-determinista y variable
corrida-a-corrida**. Medición dura: en `output/alpina_gemini.docx`, **107/422 celdas (25%) = "no
disponible"**, frente al eval set humano (`DT064_EVAL_SET.json`) con fichas de 8 campos completas.
Matiz confirmado: parte del vacío es **falta de datos** en el KB para globales recién descubiertos
(están por nombre, sin campos) → la representación debe ser **robusta a huecos**.

## Solución elegida (usuario): (b) KB-driven determinista, estrategia B2 (ensamblaje completo)

Se **quita al LLM la autoría de la tabla 2.1** y se ensambla desde datos estructurados. El LLM solo
(i) rellena huecos por competidor desde la evidencia RAG (se persisten → convergen a caché) y
(ii) redacta la prosa 2.2/2.4/2.5 + radar, recibiendo la 2.1 ya hecha como contexto.

### Piezas nuevas (todas puras salvo la cadena inyectada)
- **`domain/kb/seccion21_assembler.py`** — `assemble_seccion_21(tiers, fichas, citas)` → el **mismo
  markdown** que emitía `chain_03` para 2.1 (headings de tier + tabla vertical `| Campo | Valor |`
  por competidor). Así el render docx (`parse_markdown`→`TableBlock`) y la persistencia T3
  (`parse_fichas_competidores`) **no cambian**. Regla (c): solo emite filas con dato → **cero
  "Dato no disponible"**; un competidor solo-nombre igual se lista (el nombre es el hecho anclado).
  Reusa `_tabla_markdown` (`informe_seccion`) y `FICHA_KEYS`.
- **`domain/chains/chain_03b_ficha_fields.py`** — hole-filler: por competidor, extrae los campos
  faltantes de la evidencia como JSON `{clave: valor|null}`. Tarea de extracción constreñida (menos
  variable que redactar). `parse_ficha_fields` reusa `_es_valor_util` → un hueco no puede
  reintroducir el veneno que DT-065 purgó. RN-001: `null`/ausencia → se omite, no se fabrica.
- **`domain/kb/seccion21_holes.py`** — `fill_holes(...)`: calcula huecos (`FICHA_KEYS` sin valor),
  invoca la cadena **acotado** (`seccion21_holefill_max`, globales primero), fusiona sin pisar el KB
  y devuelve `(fichas_enriquecidas, rellenados)` — `rellenados` son los valores nuevos (candidatos).

### Cableado (detrás de flag maestro, `config.py`)
- `seccion21_determinista_enabled: bool = False` + `seccion21_holefill_max: int = 8`.
- `chain_03_benchmarking.build_chain_03(llm, omitir_21=False)`: el prompt "sin 2.1"
  (`USER_PROMPT_03_SIN_21`) se **deriva del canónico** (conserva el spec de 2.2+ verbatim, sin drift;
  sustituye el bloque de 2.1 por `{seccion_21_context}`).
- `generate_benchmarking.execute`: con B2, ensambla 2.1 (assembler + hole-filler sobre el `context`
  RAG), inyecta `seccion_21_context`, y **antepone** la 2.1 ensamblada a la prosa del LLM.
- `generate_n1`: construye `tiers` (global=clase mundial, regional/startup=directorio) + `fichas_kb`
  (`list_ficha_atributos_by_sector`), decide `b2_on = flag AND hay anclas`, y construye las cadenas
  (primaria + escalada) con `omitir_21=b2_on`. La persistencia T3 no se toca: la 2.1 ensamblada
  (incl. huecos rellenados) round-trip-ea por `parse_fichas_competidores`.

### Invariante
Flag OFF **o** sin sujetos anclados → el LLM autora la 2.1 como hoy, prompt byte-idéntico. Verificado
por tests (`test_b2_off_es_invariante`, `test_b2_on_pero_sin_anclas_cae_a_invariante`).

## Gate
`ruff` 0 (src/ tests/). **Tests puros nuevos:** `test_dt066_assembler` (8), `test_dt066_holes` (11),
`test_dt066_wiring` (5, incl. formateo real del `ChatPromptTemplate` con `{{}}` del radar). Suite:
**617 passed, 3 skipped** (excluye `test_fase15_gate::...budget_file` — fallo **pre-existente** ajeno:
`docs/decisions/fase15_budget.json` se archivó en `785f79b`; falla igual sin estos cambios).

## E2E DT-066 (Alpina 1040, 2026-08-04, `output/alpina_dt066.docx`) — VALIDADO
Corrida con los 4 flags (`SELFREVIEW/DISCOVER_GLOBALES/ANCLAJE_LOCAL/SECCION21_DETERMINISTA=true`).
**EXIT=0.** El path B2 se activó (log `entidades competidoras: 8 (KB=8…)` + `hole-filling: 8
competidores procesados`).
- ✅ **"Dato no disponible": 25% → 3%** doc-wide (107/422 → 10/306). En la **sección 2.1 = 0 celdas**
  "no disponible" (el ensamblador las elimina por construcción); las 10 residuales están en 2.3
  Mercado (9) y 5.4 (1), tablas que aún redacta el LLM.
- ✅ **Fichas 2.1 deterministas con datos reales del KB**: globales food (Abbott/Arla Foods/Bel
  Group/Coca-Cola/Danone…) con `resumen_estrategico` + `portafolio` poblados; 3 tiers presentes.
- ✅ **0 competidores tabaco/cerveza en 2.1** (las 21 menciones de "tabaco"/"cerveza" del doc son la
  etiqueta del sector GICS 3020 "Alimentos, bebidas y tabaco" y contexto de tendencias en la PROSA —
  p. ej. British American Tobacco como dinámica sectorial —, no fichas de competidor; comportamiento
  pre-existente de los caps de prosa, ajeno a DT-066).
- ✅ Radar renderizado (1 figura en el doc).

## RE-VERIFICACIÓN sin dependencia del free tier (2026-08-04, `output/alpina_dt066_v2.docx`) — CIERRE
El caveat de la 1ª corrida (rate-limit del free) se resolvió con un cambio mínimo: **el hole-filler se
enruta al tier de síntesis (Gemini)** en vez del resiliente free-first (`generate_n1.py`,
`build_chain_ficha_fields(ctx.api_llm_synth or …)`). El hole-filler es extracción de precisión y
acotada (≤`holefill_max`) → cabe de sobra en la cuota de Gemini (500 RPD) y su calidad deja de
depender del free. Invariante: sin Gemini synth en `.env`, `api_llm_synth == api_llm` (idéntico a hoy).

Re-corrida Alpina 1040 (4 flags), con el **free saturado TODA la corrida** (`ResourceExhausted 32/32`):
- **EXIT=0**; path B2 activo (`entidades competidoras: 8 (KB=8, LLM=3)`, 8 globales food, 0 tabaco/cerveza).
- ✅ **Radar de Cap 2: `PRESENTE (6 competidores)`** (antes AUSENTE) + 1 figura en el `.docx`.
- ✅ **Hole-filler medido limpio:** `hole-filling: 8 competidores procesados, 0 con datos nuevos`,
  **sin una sola excepción de rate-limit** (las llamadas fueron por Gemini — visibles en los cost
  records: `gemini-3.5-flash-lite … out=76/86/23`). El M=0 de esta corrida es el resultado **honesto**:
  la evidencia RAG recuperada para esos 8 globales **no soporta** los campos faltantes → Gemini
  devuelve `null` (RN-001, no fabrica). NO es artefacto de rate-limit. **Conclusión:** B2 desacopla la
  calidad de la tabla de la disponibilidad del modelo; la riqueza de los huecos queda atada al **Frente
  Evidencia (DT-049)** (evidencia más diversa ⇒ más huecos rellenables).
- ✅ Regresiones intactas: **0 "no disponible" en la sección 2.1**; 11 doc-wide (~3%, 7 en 2.3 Mercado,
  tabla que aún redacta el LLM); **0 fichas de competidor tabaco/cerveza en 2.1** (las 4 menciones en
  tablas 2.1.2/2.1.3 son etiquetas de actividad CIIU de las empresas regionales/startup —
  "Elaboración de Alimentos, Bebidas y Tabaco (C2825)" —, no competidores); 3 tiers poblados.

## PROBLEMAS detectados (1ª corrida — RESUELTOS arriba)
- **Modelo free severamente rate-limited** (`nvidia/nemotron … ResourceExhausted: 32/32` durante toda
  la corrida). Consecuencias directas: (a) **hole-filling = 0 datos nuevos** (las llamadas del
  hole-filler cayeron por rate-limit → no se exploró su capacidad de rellenar huecos, solo su no-crash
  path); (b) **`radar_data: AUSENTE` en el log de Cap 2** (la generación prosa+radar se degradó).
  **RESUELTO** por la re-verificación de arriba (hole-filler a Gemini): radar confirmado y hole-filler
  medido limpio. La tabla 2.1 salió bien igual porque el ensamblaje es DETERMINISTA (no depende
  del LLM); solo los huecos lo hacen — evidencia de que B2 desacopla la calidad de la tabla de la
  disponibilidad del modelo.
- **Degradación en refusal/CJK:** si la PROSA del LLM se rehúsa/idioma-incorrecto, `execute` devuelve
  párrafo de ausencia y **se pierde la 2.1 ensamblada** (edge raro). Mejora futura: emitir la 2.1
  determinista + ausencia solo para la prosa.
- **Convergencia depende de evidencia:** B2 no crea datos; en KB frío la tabla sale con lo anclado +
  lo que el hole-filler saque de la web/RAG. La riqueza plena sigue atada al **Frente Evidencia
  (DT-049)**. El flag permite A/B (OFF vs ON) en la misma corrida.
- **Deuda:** `generate_benchmarking`/`generate_n1` crecieron algo (lógica nueva ubicada en módulos
  `domain/kb/` para no engordar el orquestador; DT-039 sigue vigente).

## AVANCES (esta sesión, 2026-08-04)
- **DT-066 CERRADO** (código `95d97de` + fix/cierre `e363870`): 2.1 determinista validada de punta a
  punta, con el hole-filler y el radar ya **medidos** (no solo "no-crash").
- Cambio quirúrgico (1 línea en `generate_n1.py`): hole-filler → tier synth (Gemini), decisión
  sancionada por el usuario. Sin nueva deuda, sin nuevos flags, invariante preservado.
- Gate verde (ruff 0, 618 tests) y E2E dirigido reproducible (`output/alpina_dt066_v2.docx`,
  `logs/e2e_dt066_v2.log`).

## RECOMENDACIONES (próximos pasos, en orden)
1. **Frente Evidencia (DT-049 / DT-034) — palanca directa del M>0.** El hole-filler funciona pero la
   evidencia RAG es delgada para los globales recién anclados (por eso M=0 en KB frío). Ingestar el
   lote **EMIS de 250 PDFs** (en disco, sin ingestar) sube la diversidad de fuentes ⇒ más huecos
   rellenables ⇒ fichas 2.1 más ricas **y** refs del `.docx` menos escuálidas (hoy 9 únicas).
2. **Detalles de la 2.1 (tarea acotada, opción 2 del usuario):** (a) cablear `citas_por_tier` en el
   assembler (ya lo acepta, no se pasa); (b) bug empresa-focal en su propia tabla (excluir por nombre
   normalizado); (c) ¿colapsar vacíos también en 2.3 Mercado / 5.4 (las 7+ "no disponible" residuales
   viven ahí, tablas que aún redacta el LLM)?
3. **Robustez del edge refusal/CJK:** cuando la PROSA se rehúsa, emitir la 2.1 determinista + ausencia
   solo para la prosa (hoy se pierde la 2.1 ensamblada). Bajo impacto (self-review OFF por defecto).
4. **Deuda estructural** (DT-037/039/040) antes de más features; DT-038 antes de HITL.
