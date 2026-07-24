# FASE 20 — Hallazgos: Gap Analysis de Calidad vs Informe Patrón (Noel)

**Fecha:** 2026-07-24 · **Branch:** `feature/fase20-gap-analysis`

> Fase de **análisis**: produce rúbrica + matriz de brechas + `docs/prompts/` completo.
> El código de aplicación **no se toca** (salvo higiene documental). Los prompts de las chains
> **no se modifican** aquí; las divergencias se documentan y se agendan en F21/F22/F26.

**Gate de entrada:** `ruff check src/ tests/` = 0 · `pytest -m "not slow"` = 305 passed / 2 skipped. ✅
**Gate de salida:** idéntico (sin cambios de código de aplicación).

---

## 1. Método

- Estructura de `InformeSectoryCompetitivoNoel.docx` (patrón) y de 3 informes generados
  (`alpina`, `avianca`, `bancolombia`) extraída con `python-docx` (headings + tablas).
- 17 `source_prompts/*.docx` volcados a texto y comparados contra las 8 chains operativas de
  `src/ic/domain/chains/`.
- Rúbrica versionada en `docs/eval/RUBRICA_CALIDAD.md` (5 dimensiones × 0–3 por capítulo).

---

## 2. T20.1 — Rúbrica (resumen)

Entregable: **`docs/eval/RUBRICA_CALIDAD.md`** (v1.0). 5 dimensiones por capítulo:
Estructura (E), Profundidad (P), Evidencia/Citación (V), Elementos visuales (F), Tono (T),
cada una 0–3. Umbral por capítulo ≥ 11/15; informe aceptable ≥ 73% ponderado y sin dimensión en 0.
Aplicable manual y como *LLM-judge* (temperatura 0). Incluye plantilla de evaluación.

**Estructura del patrón Noel (referencia canónica):**

| Cap | Subcapítulos del patrón | Tablas |
|---|---|---|
| Resumen Ejecutivo | (texto corrido) | — |
| 2 Análisis Competitivo | 2.1 Líderes · 2.2 División · **2.3 Mercado** · 2.4 Módulos innov/inv/RRHH · 2.5 Brechas | T3–T8 (fichas 7 col), T9 (matriz) |
| 3 Análisis Tendencial | 3.1 TES · 3.2 MECE · 3.3 Casos de éxito | — |
| 4 Panorama Ecosistema | 4.1 Inversiones · 4.2 Integraciones · 4.3 M&A · 4.4 JV · 4.5 Alianzas | — |
| 5 Convergencia (Distrito) | 5.1 Sostenibilidad · 5.2 Transf. Digital · 5.3 Social-Humano · 5.4 Económico | — |
| 6 Accionables | (6 accionables) | — |
| **Metodología + Aviso IA** | secciones formales | — |
| Referencias | APA | T10 (mercado por región) |

---

## 3. T20.2 — Matriz de brechas de 3 informes

Puntuación 0–3 por dimensión (E/P/V/F/T). Σ/15. Fuente: `output/{empresa}_informe.docx`.

### 3.1 Alpina (sector 3020 Alimentos — coincide con el corpus)

| Capítulo | E | P | V | F | T | Σ | Brecha principal |
|---|---|---|---|---|---|---|---|
| Resumen Ejecutivo | 3 | 2 | 2 | 3 | 2 | 12 | — |
| Cap 1 Descripción | 3 | 3 | 2 | 2 | 3 | 13 | ficha de identificación pobre |
| Cap 2 Competitivo | 2 | 3 | 2 | 2 | 3 | 12 | **falta 2.3 Mercado**; fichas no en tabla 7-col |
| Cap 3 Tendencial | 3 | 2 | 2 | 3 | 3 | 13 | casos locales off-topic (DT-036) |
| Cap 4 Ecosistema | 1 | 2 | 2 | 3 | 2 | 10 | **estructura divergente** (no 4.1–4.5) |
| Cap 5 Convergencia | 2 | 2 | 2 | 3 | 2 | 11 | plano (sin subcaps renderizados) |
| Cap 6 Accionables | 2 | 2 | 1 | 3 | 2 | 10 | no referencia hallazgos previos (Q1) |
| Transversales | 0 | — | 2 | 1 | — | — | **sin Metodología ni Aviso IA** |

### 3.2 Avianca (sector 2030 Transporte — fuera del corpus food)

| Capítulo | E | P | V | F | T | Σ | Brecha principal |
|---|---|---|---|---|---|---|---|
| Cap 2 Competitivo | 1 | 1 | 1 | 0 | 2 | 5 | **plano, 0 tablas, sesgo FoodTech** en prompt |
| Cap 4 Ecosistema | 1 | 1 | 2 | 0 | 2 | 6 | estructura divergente + sin datos |
| Cap 5 Convergencia | 1 | 2 | 2 | 0 | 2 | 7 | **deriva a 5.1–5.7** (patrón = 4 áreas) |
| (resto) | 2 | 1 | 2 | 0 | 2 | ~7 | corpus sectorial ausente (RN-001) |

### 3.3 Bancolombia (sector 4010 Bancos — fuera del corpus food)

| Capítulo | E | P | V | F | T | Σ | Brecha principal |
|---|---|---|---|---|---|---|---|
| Cap 2 Competitivo | 1 | 1 | 1 | 0 | 2 | 5 | **plano, 0 tablas**; benchmarking food-céntrico |
| Cap 3 Tendencial | 2 | 1 | 2 | 0 | 2 | 7 | tendencias genéricas; casos off-sector |
| Cap 4 Ecosistema | 1 | 1 | 2 | 0 | 2 | 6 | estructura divergente |
| (resto) | 2 | 1 | 2 | 0 | 2 | ~7 | corpus sectorial ausente |

### 3.4 Lectura transversal

- **Variabilidad brutal por sector.** Alpina (food, dentro del corpus) ≈ 11–13/cap; Avianca y
  Bancolombia (fuera del corpus) ≈ 5–7/cap y **0 tablas**. El sistema produce calidad-patrón
  **solo cuando el sector coincide con el corpus RAG + con el sesgo de los prompts**. Es el
  hallazgo raíz: *"no se parece al patrón"* es en gran parte un problema de **cobertura de
  fuentes por sector** (RN-001) sumado a **prompts con sesgo alimentos**.
- **0 tablas** en avianca/bancolombia pese a que `chain_03` pide fichas en tabla markdown → el
  LLM no las emite cuando el retrieval está vacío (aplica ausencia). Coherente con RN-001, pero
  destruye la dimensión F (visual).
- El bug de numeración `5.x` bajo Cap 4 visible en estos `.docx` es **pre-fix** (DT-032 cerrado
  en Fase 18); verificado con `renumber_subheadings()` (5.1→4.1 correcto). No es deuda viva.

---

## 4. T20.3 — Auditoría de fidelidad chain ↔ source_prompt

Entregable: **`docs/prompts/`** completado (8/8 chains + `README.md` con el mapa de los 17
archivos). Veredicto por chain:

| Chain | source_prompt | Fidelidad | Divergencia relevante |
|---|---|---|---|
| `chain_01_descripcion` | 1 | ✅ fiel | contexto web como única fuente (mejora vs original) |
| `chain_02_gics` | 2 | ✅ fiel | 25 grupos en `gics_groups.py`; exige "(GICS XXXX)" |
| `chain_03_benchmarking` | 3 | 🟠 | **sesgo "bienes de consumo/FoodTech"** hardcodeado; 2.3 Mercado fuera de alcance |
| `chain_04_tendencias` | 6 | 🟠 | **sesgo "agroindustriales"**; casos locales sin constraint sectorial (DT-036) |
| `chain_05_ecosistema` | 7 | 🔴 | **estructura reescrita** (Local/Global/Disruptores vs 4.1–4.5 movimientos) |
| `chain_06_convergencia` (+06a) | 8 | 🟠 | 4 áreas correctas; variante `06a` puede derivar el nº de áreas |
| `chain_07_accionables` | 9 | ✅/🟠 | fiel; recibe retrieval, no textos completos de caps previos (coherencia → F22) |
| `chain_08_resumen_ejecutivo` | 11 | ✅ fiel | 6 elementos; faltan algunas prohibiciones de frases (→ F26) |
| `chain_intro` | 10 | ✅ fiel | genérico; convive con intros fijas por capítulo |

**No implementados (documentados en `README.md`):**
- `source_prompt 4` (Mercado 1/2/3/Único) + `5` (Gestiones Anexas) → **Cap 2.3 Mercado ausente** 🔴.
- `source_prompt 0` (Ecuaciones de búsqueda) → runbook EMIS (F21, T21.3).
- `source_prompt 12` (Referencias) → resuelto por `apa_formatter` (código, no LLM).
- `source_prompt 13` (Evaluar Informe) → HITL, F24/F25.

**Nota de estilo/formato de source_prompts:** los prompts originales usan un flujo iterativo
(genera → "amplia hallazgos" → "quita prefijos" → "actúa como editor humano" → "quita
citaciones y mini-checklist"). Las chains **colapsan** ese flujo en una sola llamada con el
resultado final ya pedido en el system prompt. Es una divergencia **deliberada** y correcta
(1 llamada vs 5), no una pérdida.

---

## 5. T20.4 — Secciones faltantes del patrón

| Sección del patrón Noel | ¿En el ensamblado actual? | Acción |
|---|---|---|
| **Metodología** (Heading 1) | ❌ no existe | F21 (DT-045): añadir en `assembler.py` a partir de plantilla + fuentes usadas |
| **Aviso sobre el uso de IA** | ⚠️ solo `disclaimer` de 1 línea (Caption) | F21/F26 (DT-045): elevar a sección formal |
| **2.3 Mercado** (+ tabla región) | ❌ no existe | F21 (DT-044): implementar chain de mercado |
| **Subcaps 4.x del patrón** | ❌ estructura distinta | F21 (DT-046): rediseñar Cap 4 |
| **Fichas de competidor en tabla 7-col** | ⚠️ markdown pipe pedido; 0 tablas en 2/3 | F21/F23 (fuentes) + F26 (render) |
| Portada + ficha (T1/T2) | ✅ portada; ficha básica | F26 (estilo) |
| Referencias APA | ✅ presente | — |

---

## 6. Deuda técnica nueva (registrada en ROADMAP §5)

| ID | Descripción | Severidad | Fase destino |
|---|---|---|---|
| DT-043 | **Sesgo sectorial hardcodeado** en system prompts (`chain_03` "bienes de consumo/FoodTech", `chain_04` "agroindustriales") + ecuaciones de búsqueda food-céntricas. Falla para empresas fuera de alimentos (avianca/bancolombia: Cap 2 plano, 0 tablas). Parametrizar el rol/sector por GICS. | 🔴 | 21 |
| DT-044 | **Cap 2.3 Mercado ausente**: `source_prompt 4/5` (Mercado) nunca se implementó como chain; el patrón lo tiene con tabla de mercado por región (T10). | 🔴 | 21 |
| DT-045 | **Metodología + Aviso de uso de IA ausentes**: el patrón los tiene como secciones formales; hoy solo hay un disclaimer de una línea. Añadir en `assembler.py`. | 🟠 | 21 |
| DT-046 | **Cap 4 estructura divergente**: `chain_05_ecosistema` produce Local/Global/Disruptores en vez de 4.1 Inversiones / 4.2 Integraciones / 4.3 M&A / 4.4 JV / 4.5 Alianzas con eventos (Título + capacidad estratégica adquirida + vulnerabilidad mitigada). | 🔴 | 21 |
| DT-047 | **Deriva del nº de áreas en Cap 5**: `chain_06a` (variante paralela RN-009) permite que el LLM improvise áreas (avianca 5.1–5.7 vs 4 fijas del patrón). Restringir a las 4 áreas del distrito. | 🟠 | 22 |
| DT-048 | **Score de calidad no automatizado**: la rúbrica (`docs/eval/RUBRICA_CALIDAD.md`) es manual. Cablear un *LLM-judge* que la aplique sobre el `.docx` y emita el score por capítulo. | 🟡 | 22 (o backlog) |

> Las divergencias de contenido de mayor impacto (DT-043, DT-044, DT-046) se concentran en **F21**,
> que pasa de "Sprint A de 2 arreglos" a "Sprint A de contenido" (ver §7).

---

## 7. T20.5 — Re-priorización de F21–F26

- **F21** — **ampliada**. Además de DT-035/036 (ya planificados), absorbe **DT-043** (sesgo
  sectorial), **DT-044** (2.3 Mercado), **DT-045** (Metodología + Aviso IA), **DT-046** (rediseño
  Cap 4). Es ahora la fase de "acercar el output al patrón Noel". Nuevas tareas T21.5–T21.8.
- **F22** — suma **DT-047** (áreas Cap 5) y **DT-048** (LLM-judge de la rúbrica) a lo ya agendado
  (radar, checkpoint, coherencia Q1).
- **F23** — sin cambios de alcance; refuerza la causa raíz de la variabilidad por sector
  (corpus EMIS por sector GICS). La matriz §3.4 es evidencia de por qué F23 importa.
- **F26** — suma: fichas de competidor como **tablas** reales, nivel de headings consistente,
  prohibiciones de estilo del Resumen Ejecutivo.

Ninguna brecha queda huérfana (criterio de aceptación #4). ✅

---

## 8. Cambios ejecutados en esta fase (bajo riesgo, sin código de aplicación)

1. **`docs/eval/RUBRICA_CALIDAD.md`** creado (rúbrica v1.0).
2. **`docs/prompts/`** completado: `prompt-04-tendencias.md`, `prompt-05-ecosistema.md`,
   `prompt-07-accionables.md`, `prompt-08-resumen-ejecutivo.md`, `prompt-intro-parrafos.md`,
   `README.md` (mapa 17 source_prompts ↔ chains). `prompt-05-convergencia.md` renombrado a
   `prompt-06-convergencia.md` (alineación con `chain_06`; sin referencias externas rotas).
3. `docs/decisions/FASE20_HALLAZGOS.md` (este archivo).
4. ROADMAP: tablero §4 (F20 ✅), deuda §5 (DT-043..048), changelog §8, tareas F21/F22/F26,
   prompt de arranque F21 ajustado.

Sin cambios en `src/`. Gate final verde (ruff 0 · 305 passed / 2 skipped).

---

## 9. Métricas de cierre

| | Fase 19 | Fase 20 |
|---|---|---|
| Fast tests | 305 | 305 (sin cambio; fase de análisis) |
| ruff | 0 | 0 |
| Cobertura `domain/` (rápida) | 69% | 69% (sin cambio) |
| `docs/prompts/` (chains documentadas) | 4 archivos (parcial) | **8/8 chains + README** |
| Rúbrica de calidad | — | **v1.0 versionada** |
| Deuda §5 viva | 5 + 6 nuevas (F19) | +6 nuevas (DT-043..048) |
