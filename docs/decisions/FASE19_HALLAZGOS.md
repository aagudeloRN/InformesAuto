# FASE 19 — Hallazgos: Auditoría de Arquitectura, Código y Documentación

**Fecha:** 2026-07-24 · **Branch:** `feature/fase19-auditoria`

> Fase de **auditoría**: se lee y mide mucho, se cambia poco (solo higiene de bajo riesgo).
> Los ADR **no se reescriben** (son inmutables); las divergencias se registran como deuda nueva.

---

## 1. Objetivo

Tras 18 fases incrementales, verificar de una sola vez que infraestructura, código y
documentación (15 ADR + 13 RN + deuda §5) están alineados con las reglas del proyecto
(CLAUDE.md, PRIME DIRECTIVE) y con el comportamiento real del sistema. La salida re-prioriza
las fases 20–26.

**Gate de entrada:** `ruff check src/ tests/` = 0 · `pytest -m "not slow"` = 305 passed / 2 skipped.
**Gate de salida:** idéntico (los cambios de esta fase no tocan código de aplicación).

---

## 2. Formato de hallazgos

`ID · Hallazgo · Severidad · Acción · Fase destino`. Severidad: 🔴 Alta · 🟠 Media · 🟡 Baja.

---

## 3. T19.1 — Inventario y métricas

### 3.1 Tamaño de archivos (top, `src/`)

| Archivo | Líneas | Estado |
|---|---|---|
| `infrastructure/llm/gateway.py` | 503 | 🔴 > 300 (red flag PRIME §IX) |
| `presentation/app.py` | 487 | 🔴 > 300 |
| `domain/use_cases/generate_informe.py` | 438 | 🔴 > 300 (regresión: ADR-009 lo dejó en 347) |
| `infrastructure/render/docx_renderer.py` | 282 | 🟠 cerca del límite |
| resto | < 225 | ✅ |

Total `src/`: 6.110 L en 76 archivos.

### 3.2 Funciones > 60 líneas (AST)

| Líneas | Ubicación | Nota |
|---|---|---|
| **157** | `generate_informe.py:282 _run_n3()` | 🔴 ADR-009 lo declaró ~62 L; creció con la lógica APA/ensamblado de Fase 18 |
| 155 | `app.py:42 _render_repositorio()` | 🟠 vista Streamlit |
| 146 | `pdf_ingestor.py:73 ingest_batched()` | 🟠 ingesta por lotes (cohesiva) |
| 115 | `app.py:199 _render_historial()` | 🟠 vista Streamlit |
| 109 | `generate_convergencia.py:35 execute()` | 🟠 3 ejes + síntesis |
| 96 | `embedding_repo.py:129 search_similar()` | 🟠 SQL multi-capa (ADR-012/013) |

### 3.3 Cobertura de `domain/` (suite rápida)

`pytest -m "not slow" --cov=src/ic/domain` → **69%** (883 stmts, 273 sin cubrir). **< 80% exigido**
(PRIME §6.1, CLAUDE.md TIER 4). *(pytest-cov no estaba instalado; se añadió como dev-dep en esta fase.)*

| Módulo | Cobertura | Causa del hueco |
|---|---|---|
| `generate_n1.py` | 0% | solo ejercido por E2E `@slow` |
| `generate_informe.py` | 34% | orquestación cubierta solo por E2E `@slow` |
| `generate_empresa_description.py` | 40% | rama de fallback CJK/ausencia |
| `chain_01_descripcion.py` | 47% | builder de cadena sin unit test directo |
| `assembler.py` / `markdown_parser.py` | 69% | ramas de tabla/figura parcialmente cubiertas |

> **Matiz honesto:** la orquestación N1/N3 sí se ejercita en los E2E `@slow` (no en el gate
> rápido). La cifra 69% es la del **gate de CI** (suite rápida), que es la que protege el proyecto.

### 3.4 SoC / Dependency Agnosticism

| Regla | Verificación | Veredicto |
|---|---|---|
| `domain/` no importa librerías externas | 12 chains importan `langchain_core` (LCEL: `Runnable`, `ChatPromptTemplate`, `StrOutputParser`) | 🟠 **divergente** — ver DT-042 |
| `presentation/` no conoce `data/` | `app.py:60,132,212` importan `SessionLocal` + repos directamente | 🟠 **divergente** — ver DT-038 |
| Acceso externo vía wrapper `infrastructure/` | LLM/embeddings/pgvector/web/openalex vía wrappers; matplotlib/python-docx aislados en `render/` y `charts/` (ADR-011) | ✅ fiel |
| Sin nombres de modelo hardcodeados (TIER 1) | `gateway.py:23-29` `_PRICING` con IDs literales | 🟠 **divergente** — ver DT-040 |

### 3.5 Grafo de imports / ciclos

- **Sin dependencias circulares reales.** `generate_informe.py` usa **38 imports diferidos**
  dentro de funciones (patrón documentado en ADR-008/009 DT-003) para evitar circularidad y
  acelerar tests que ejercen un solo método. Es un *smell* aceptado, no un ciclo.

---

## 4. T19.2 — Plan de partición de archivos > 300 L

> Ninguna partición se ejecuta en esta fase (todas son riesgo Medio+ sobre código crítico).
> Se agendan con fase destino y DT asignada.

### 4.1 `gateway.py` (503 L) → DT-037

Costuras naturales (todas cohesivas hoy en un solo módulo):
`_PRICING` + `CallRecord` + `CostTracker` (L23-89) · `OllamaGatewayLLM` (L93-174) ·
`OpenRouterGatewayLLM` (L175-311) · helpers de error (L313-345) · `ResilientChatModel`
(L346-424) · factories `build_llm`/`build_api_llm`/`build_resilient_api_llm` (L425-503).

**Propuesta:** paquete `infrastructure/llm/` → `cost.py`, `ollama.py`, `openrouter.py`,
`errors.py`, `resilient.py`, `factory.py`; `gateway.py` queda como **fachada de re-export**
(preserva imports existentes). Riesgo **Medio** (muchos importadores). **Fase destino: 22.**

### 4.2 `presentation/app.py` (487 L) → DT-038

Tres vistas + main: `_render_repositorio` (155 L), `_render_historial` (115 L),
`_check_services`. **Propuesta:** `presentation/views/repositorio.py` + `views/historial.py`;
además **enrutar el acceso a `data/` por casos de uso** (cerrar la violación SoC §3.4).
Riesgo **Medio** (la UI toca BD directamente hoy). **Fase destino: 26** (la fase de estilo/UI
ya reabre `app.py`; se aprovecha para el split + SoC).

### 4.3 `generate_informe.py` (438 L) → DT-039  ·  candidato más limpio

`_run_n3` (157 L) concentra ensamblado + APA + persistencia. **Propuesta:** extraer a
`domain/use_cases/generate_n3.py` (mismo patrón que `generate_n1.py`, DT-004/T12.5), dejando
`_run_n3` como orquestador delgado. Riesgo **Medio** pero **precedente existente**.
**Fase destino: 22.**

---

## 5. T19.3 — Coherencia docs ↔ código (ADR-001..015, RN-001..013)

### 5.1 ADR

| ADR | Veredicto | Evidencia |
|---|---|---|
| 001 RAG propio | ✅ fiel | `pgvector_store.py`, `embedder.py` (httpx a Ollama), sin NotebookLM |
| 002 routing local-primero + wrapper único | ✅ fiel (matizado por ADR-010) | `gateway.py` `CostTracker`/tiers |
| 003 fuentes doble vía | ✅ fiel | `web_connector.py`, `openalex_connector.py`, `pdf_ingestor.py` |
| 004 LangChain orquestación | 🟠 **divergente parcial** | L49-50 afirma "el wrapper aísla al dominio del framework", pero las chains de `domain/` importan `langchain_core` (LCEL) directamente → DT-042 |
| 005 diseño retrieval | ✅ fiel | httpx directo, `<=>` coseno, ORM propio |
| 006 presupuesto free-first | ✅ fiel | tiers `free/free_alt/synth/paid` en `.env` |
| 007 memoria WSL2 tests | ✅ fiel | `[tool.pytest.ini_options] env` OPENBLAS/OMP=1; markers `slow` |
| 008 orchestrator + on_step | ✅ fiel | `InformeParams`/`InformeResult`/`StepCallback` |
| 009 refactor `_PipelineContext` | 🟠 **desactualizado** | declaró 347 L / métodos <65 L; hoy 438 L y `_run_n3`=157 L → DT-039 |
| 010 API-first GICS/Cap2 | ✅ fiel (refs de línea obsoletas) | patrón `api_llm or ctx.llm` en `generate_informe.py:204` (ADR cita L145/170) |
| 011 modelo documento + PDF | ✅ fiel | `report_model.py`, `render/`, `charts/` |
| 012 filtrado sectorial | ✅ fiel | `PGVectorStore.search()` con capas empresa/sector/global; `_prepend()` |
| 013 web solo-citado | ✅ fiel | `promote_cited_web`, `sweep_stale_web_sessions` |
| 014 caché + batch keep_alive | 🟠 **tabla de estado obsoleta** | L102 dice cableado E2E "⬜ pendiente"; ya cableado en `generate_informe.py:185-245` y `generate_n1.py:28-45` (Fase 16). Corrección documental, no de código |
| 015 HITL post-gen | ✅ fiel (pendiente por diseño) | módulos `chain_evaluar`/`generate_evaluacion`/`complement_context` **no** existen aún → correcto (F24-25) |

### 5.2 RN

| RN | Veredicto | Evidencia |
|---|---|---|
| 001 datos ausentes | ✅ | `absent_data.py` `check_retrieval_sufficient` + `build_absent_paragraph` |
| 002 APA trazable | ✅ | `apa_formatter.build_references_section`; orphan checker (Fase 10) |
| 003 API-primero LLM / local embeddings | ✅ | consistente con ADR-006/010 |
| 004 doble vía índice único | ✅ | mismo pgvector para web/openalex/pdf |
| 005 DAG con barreras | ✅ | N0→N1→N2→N3 en `generate_informe.py` |
| 006 historial completo BD | ✅ | `InformeRepository`, `_run_n3` persiste |
| 007 idioma es-CO (CJK) | ✅ | `has_cjk_characters` en benchmarking, descripción, convergencia, resumen, tendencias (DT-009 cerrado) |
| 008 presupuesto ≤ 1 USD | ✅ | `CostTracker.within_budget` |
| 009 divide y vencerás Cap 5 | ✅ | `generate_convergencia` 3 ejes + síntesis |
| 010 ingesta PDF por lotes | ✅ | `pdf_ingestor.ingest_batched` |
| 011 HITL post-gen | ✅ pendiente (F24-25) | coherente con ADR-015 |
| 012 regeneración completa | ✅ pendiente (F24-25) | `complement_context` aún no en firma |
| 013 **search_depth parametrizable** | 🔴 **divergente** | `web_connector.py:56` hardcodea `"search_depth":"basic"`; la firma **no** acepta el parámetro. La regla documenta un futuro no implementado → DT-035 |

---

## 6. T19.4 — Revalidación de deuda §5

| DT | Estado documentado | Estado real (evidencia) | Acción |
|---|---|---|---|
| DT-018 | 🟡 "settings.json actualizado en Fase 10" | **Falso**: `check-ruff.sh` no estaba en `settings.json`; el hook nunca corría | ✅ **Cerrado esta fase** (cableado en PreToolUse `git commit`) |
| DT-027 | 🔴 target "Fase 19" | Sigue con regex inline en `generate_benchmarking.py:21` (`_RADAR_RE`); la "cadena dedicada temp 0" no se hizo | **Retarget → F22** (robustez) |
| DT-030 | ⬜ F22 | Sin checkpoint/--resume | Confirmado F22 |
| DT-034 | ⬜ F23 | Índice EMIS generado; lote 250 PDFs sin ingestar | Confirmado F23 |
| DT-035 | ⬜ F21 | `search_depth` no parametrizado (§5.2 RN-013) | Confirmado F21 · **fix de colisión** (ver abajo) |
| DT-036 | ⬜ F21 | Casos globales sin constraint sectorial en prompt | Confirmado F21 |

**Colisión de numeración DT-035:** `FASE18_HALLAZGOS.md §9` reutilizó "DT-035" para "verificación
E2E de Alpina" (que el propio §7 de esa fase marca ✅ 4/4 criterios). El **DT-035 canónico** es el
del ROADMAP §5 (competidores Cap 2 / `search_depth`, F21). La entrada de Fase 18 queda como
**cerrada/histórica** (no se renumera el hallazgo pasado; esta nota es el mapeo oficial).

---

## 7. T19.5 — Higiene de repo

| Ítem | Hallazgo | Severidad | Acción |
|---|---|---|---|
| Hooks | `check-secrets`, `check-hardcoded-models`, `format-python` activos; **`check-ruff` no registrado** | 🟠 | ✅ cableado (DT-018) |
| Hook models | `check-hardcoded-models.sh` **no detecta** `nemotron`, `gpt-oss` ni formas con guion (`gemma-3`, `llama-3`, `claude-x`): sus patrones exigen dígito pegado (`gemma[0-9]`). Por eso `gateway._PRICING` pasó el guardarraíl | 🟠 | DT-040 |
| `output/` | gitignored (`.gitignore:19`) + `*.docx`/`*.pdf` globales; **nada trackeado** | ✅ | — |
| Raíz | `.coverage`, `InformeConvergenciaLocal2026V3RvADAA.pdf`, `InformeSectoryCompetitivoNoel.docx` sueltos, **todos gitignored** | 🟡 | sin acción (patrón/base de F20; Chesterton) |
| `docs/prompts/` | 4 md vs **17** `source_prompts/*.docx` | 🟠 | alcance F20 (T20.3), no F19 |
| README/CHANGELOG/CONTRIBUTING | presentes en raíz (PRIME §4.1) | ✅ | — |

---

## 8. Deuda técnica nueva (registrada en ROADMAP §5)

| ID | Descripción | Severidad | Fase destino |
|---|---|---|---|
| DT-037 | `gateway.py` 503 L → paquete `llm/` + fachada de re-export | 🟠 | 22 |
| DT-038 | `app.py` 487 L → `presentation/views/` **y** enrutar acceso a `data/` por casos de uso (violación SoC §3.4) | 🟠 | 26 |
| DT-039 | `generate_informe.py` 438 L / `_run_n3` 157 L (regresión ADR-009) → extraer `generate_n3.py` | 🟠 | 22 |
| DT-040 | `gateway._PRICING` hardcodea IDs de modelo + `check-hardcoded-models.sh` con puntos ciegos (patrones sin guion, sin `nemotron`/`gpt-oss`) | 🟠 | 22 |
| DT-041 | Cobertura `domain/` (gate rápido) 69% < 80%; orquestación N1/N3 solo cubierta por E2E `@slow` | 🟠 | 22 |
| DT-042 | Acoplamiento LCEL en `domain/`: las chains importan `langchain_core` directamente, en tensión con la afirmación de ADR-004 (wrapper aísla el dominio). Decidir: documentar excepción explícita o interfaz de cadena en `infrastructure/` | 🟡 | 22 (o backlog) |

---

## 9. Cambios ejecutados en esta fase (bajo riesgo)

1. **DT-018 cerrado** — `check-ruff.sh` registrado en `.claude/settings.json` (PreToolUse de
   `git commit`, antes de secrets y models). Verificado: el hook corre y devuelve exit 0.
2. **pytest-cov** añadido como dev-dep (`uv add --dev pytest-cov`) para medir cobertura de
   `domain/` (T19.1). RAM libre 8 GB / Ollama sin modelos al instalar (ADR-007 D3 respetado).

Sin cambios en código de aplicación. Gate final verde (ruff 0 · 305 passed / 2 skipped).

---

## 10. Re-priorización de F20–F26

- **F21** — confirmada (DT-035 `search_depth` + DT-036 casos locales). RN-013 es su especificación.
- **F22** — absorbe: DT-027 (radar dedicado, retarget desde "F19"), DT-030 (checkpoint), **DT-037**
  (gateway split), **DT-039** (generate_n3), **DT-040** (pricing+hook), **DT-041** (cobertura),
  **DT-042** (LCEL). Es la fase de robustez + higiene estructural.
- **F23** — confirmada (DT-034 lote EMIS + servicios de búsqueda pagos → ADR-016).
- **F24/F25** — HITL sin cambios (ADR-015 fiel, no implementado aún).
- **F26** — absorbe **DT-038** (split de `app.py` + SoC UI↔data), ya que reabre `app.py` para estilo.
- **F20** — sin cambios de alcance; el gap de `docs/prompts/` (4 de 17) y las secciones faltantes
  del patrón Noel se atacan allí. Su prompt de arranque se ajusta con estos hallazgos.

---

## 11. Métricas de cierre

| | Fase 18 | Fase 19 |
|---|---|---|
| Fast tests | 305 | 305 (sin cambio; fase de auditoría) |
| ruff | 0 | 0 |
| Cobertura `domain/` (rápida) | no medida | **69%** (nueva línea base) |
| Archivos > 300 L | 3 | 3 (particiones agendadas) |
| Deuda §5 viva | 6 abiertas | 5 abiertas + 6 nuevas (DT-018 cerrado) |
