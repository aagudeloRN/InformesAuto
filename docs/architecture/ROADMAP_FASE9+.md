# 🗺️ ROADMAP — Fase 9 en adelante

> **Propósito:** Plan de trabajo vivo y pormenorizado para llevar el sistema de Informes
> de Inteligencia Competitiva desde su estado actual (pipeline E2E funcional) hasta un
> producto **fiable, bien formateado y anclado en evidencia sectorial**, útil para empresas
> en Colombia.
>
> **Este documento se consulta y se actualiza en cada ejecución.** No es inmutable (a
> diferencia de los ADR). Cada fase se refina con los hallazgos de la anterior.

**Versión del roadmap:** 3.1 · **Creado:** 2026-07-21 · **Última actualización:** 2026-07-24

---

## 1. Cómo usar este roadmap (modelo operativo)

**Regla base: cada fase se ejecuta en un chat limpio** para evitar saturación de contexto.
El flujo de cada sesión es siempre el mismo:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Abrir chat nuevo                                                  │
│ 2. Pegar el "PROMPT DE ARRANQUE" de la fase (está al final de cada   │
│    sección de fase, en un bloque copiable)                          │
│ 3. El agente LEE lo necesario → entra en Plan Mode → propone → espera│
│ 4. Ejecuta las tareas de la fase                                    │
│ 5. Gate de calidad verde (ruff + pytest)                            │
│ 6. Documenta hallazgos en docs/decisions/FASE<N>_HALLAZGOS.md       │
│ 7. Actualiza el TABLERO DE AVANCE (§4) de este roadmap              │
│ 8. Genera el PROMPT DE ARRANQUE de la fase siguiente y lo propone   │
└─────────────────────────────────────────────────────────────────────┘
```

**Principio de auto-contención:** el prompt de arranque de cada fase incluye qué leer, qué
hacer y cómo cerrar. No asume memoria de sesiones anteriores más allá de los artefactos
persistidos (código, `docs/`, este roadmap, `MEMORY.md`).

**El roadmap evoluciona:** si durante una fase se descubre algo que cambia el plan de las
fases siguientes, se actualiza este documento en la misma sesión (sección de la fase
afectada + changelog en §8). El plan es la especificación (CLAUDE.md Tier 2).

---

## 2. Convenciones de trabajo

Estas reglas aplican a **todas** las fases. Se heredan de `CLAUDE.md` y
`docs/architecture/PRIME DIRECTIVE.md`; se resumen aquí para referencia rápida.

| Tema | Regla |
|------|-------|
| **Plan Mode** | Obligatorio para todo lo no trivial. Leer → proponer → aprobar → ejecutar. |
| **Gate de calidad** | Toda fase cierra con `uv run ruff check src/ tests/` **y** `uv run pytest -m "not slow" -q` en verde. Sin excepciones. |
| **Modelos** | Nunca hardcodear nombres de modelo. Solo en `.env` + routing. (ADR-002/006/010) |
| **Secretos** | Nunca en código ni git. Solo en `.env`. |
| **Wrappers** | Todo acceso a librería externa pasa por `infrastructure/`. (Dependency Agnosticism) |
| **SoC** | `presentation/` no conoce `data/`; `domain/` no importa librerías externas. |
| **Tamaño** | Archivo/función > 300 líneas = red flag → separar. |
| **Commits** | Conventional Commits. El cuerpo explica el *porqué*. Co-Author + Session trailers. |
| **Ramas** | Flujo GitHub del PRIME DIRECTIVE §4.3. `main` protegida (solo releases); `develop` = base de integración; **una rama `feature/fase<N>-*` (o `fix/`, `docs/`) por fase, creada desde `develop`**, que se mergea de vuelta a `develop` con `--no-ff` al cerrar la fase. CI solo **local** (sin remoto GitHub por ahora). |
| **Docs por fase** | Hallazgos técnicos en `docs/decisions/FASE<N>_HALLAZGOS.md` (patrón existente FASE0–FASE8). |
| **Tests** | En el mismo PR/commit que el código. Cobertura mínima 80% en `domain/`. |

**Comandos base de verificación:**
```bash
docker ps | grep repositorio_postgres           # BD en :5434
curl http://127.0.0.1:11434/api/tags             # Ollama responde
uv run ruff check src/ tests/                    # lint limpio
uv run pytest -m "not slow" -q                   # suite rápida verde
```

---

## 3. Visión y orden de las fases

Objetivo final: **documento fiable de vigilancia e inteligencia competitiva, bien
formateado, anclado en evidencia sectorial curada, útil para empresas colombianas.**

Orden por dependencia y valor (fiabilidad → entregable → optimización → diferenciación):

```
Fase 9  (cierre)  Estabilización y Gate de Calidad        [P0 · desbloquea todo]
Fase 10           Fiabilidad del Contenido                [P0 · trazabilidad/APA/idioma]
Fase 11           Formato del Documento Final             [P0 · el entregable comercial]
Fase 12           Optimización de Operación               [P1 · caché/resiliencia/cola]
Fase 13           Repositorio Sectorial RAG (26 sectores) [P1 · mayor palanca de calidad]
```

> **Nota histórica:** La "Fase 9" se abrió parcialmente en los commits `5baaf98` y `7ddc127`
> (ADR-010 routing API-first, DT-013 OOM fix, DT-014 PDF fast-path). Lo que quedó **sin
> cerrar** fue el gate de calidad (DT-009) y la validación E2E (DT-005). Por eso la primera
> fase de este roadmap es el **cierre de Fase 9**.

---

## 4. Tablero de avance

Leyenda de estado: ⬜ Pendiente · 🟡 En curso · ✅ Completada · ⏸️ Bloqueada

| Fase | Título | Estado | Fecha cierre | Commit(s) | Hallazgos |
|------|--------|--------|--------------|-----------|-----------|
| 9 | Estabilización y Gate de Calidad | ✅ | 2026-07-21 | `7188674`+ | `FASE9_HALLAZGOS.md` |
| 10 | Fiabilidad del Contenido | ✅ | 2026-07-21 | `8f00f9d`+ | `FASE10_HALLAZGOS.md` |
| 11 | Formato del Documento Final | ✅ | 2026-07-21 | `a581201`+ | `FASE11_HALLAZGOS.md` |
| 12 | Optimización de Operación | ✅ | 2026-07-21 | `8f6e8f5`+ | `FASE12_HALLAZGOS.md` |
| 13 | Repositorio Sectorial RAG | ✅ | 2026-07-22 | `62fe327` | `FASE13_HALLAZGOS.md` |
| 14 | Calidad de Retrieval y Evaluación | ✅ | 2026-07-22 | `1fbe8a1` | `FASE14_HALLAZGOS.md` |
| 15 | Resiliencia y Costo | ✅ | 2026-07-22 | `a367b57`+ | `FASE15_HALLAZGOS.md` |
| 16 | Presentación del Contenido | ✅ | 2026-07-22 | `aadd99e` | `FASE16_HALLAZGOS.md` |
| 17 | Instrumentación, Radar y Pulido E2E | ✅ | 2026-07-23 | `7e6ec20`..`6927063` | `FASE17_HALLAZGOS.md` |
| 18 | Evidencia y Citación | ✅ | 2026-07-23 | `8c6b8c2`..`7dcd676` | `FASE18_HALLAZGOS.md` |
| 19 | Auditoría de Arquitectura, Código y Docs | ✅ | 2026-07-24 | _pendiente_ | `FASE19_HALLAZGOS.md` |
| 20 | Gap Analysis de Calidad vs Informe Patrón (Noel) | ✅ | 2026-07-24 | `f08fc53` | `FASE20_HALLAZGOS.md` |
| 21 | Calidad de Contenido — Sprint A + A' (ex-F19) | ✅ | 2026-07-24 | `1a96d7b`..`17a9a91` (merge `307ec4b`) | `FASE21_HALLAZGOS.md` |
| 22 | Evidencia, Retrieval y Coherencia (Sprint A: DT-049/052/053; Sprint B: coherencia) | 🟢 **Sprint A cerrado** | 2026-07-29 | A1 `4c342c4` · A2 `e364a52` · T22.1 `6e6e220` · T22.6 `71d67d2` · DT-053 `04604cf` · anti-mezcla `aeb4482` · A3 harness+E2E (2 sectores) | `FASE22_HALLAZGOS.md §5/§6` |
| 23 | Fuentes: Corpus EMIS completo + Búsqueda paga | ⬜ | — | — | — |
| 24 | HITL Módulo 1 — Gap Auditor (ex-F21) | ⬜ | — | — | — |
| 25 | HITL Módulo 2 — Consistency Checker + UI (ex-F22) | ⬜ | — | — | — |
| 26 | Estilo y Visualización del Documento Final | ⬜ | — | — | — |

> Cada fase, al cerrar, actualiza su fila (estado ✅, fecha, hash de commit) y marca sus
> tareas en la sección correspondiente.

---

## 5. Deuda técnica viva

Se arrastra y actualiza entre fases. (Fuente: `ARQUITECTURA.md` §5 + hallazgos.)

| ID | Descripción | Fase objetivo | Estado |
|----|-------------|---------------|--------|
| DT-004 | `generate_informe.py` ≥ 300 líneas (~400 L) | 12 | ✅ 345 L — N1 extraído a `generate_n1.py` |
| DT-005 | E2E Cap5 con servicios reales (`test_convergencia_e2e.py`) | 9 | ✅ 165.87 s, verde |
| DT-009 | Gate ruff ✅; validación idioma (CJK) N1+ | 10 | ✅ CJK cerrado en todos los caps N1–N3 |
| DT-010 | CostTracker para Ollama (tiempo como proxy de tokens) | 12 | ✅ tokens reales + tiempo en `CallRecord.tiempo_ollama_s` |
| DT-011 | Ingesta de fuentes sectoriales / EMIS | 13 | ✅ corpus GICS: panel Repositorio + `ingest_batch.py` + filtrado sectorial (ADR-012) |
| DT-012 | Multi-empresa / cola + historial paginado | 12 | ✅ paginación PAGE_SIZE=10 + filtro ILIKE + CSV export |
| DT-015 | Citación APA 7 no fiel (sin sangría/cursiva) + sin cita inline trazable | 10 | ✅ APA 7 fiel (dispatch por tipo); cursiva→Fase 11; orphan checker operativo |
| DT-016 | Formato .docx pobre (sin tablas/imágenes/TOC/portada) + salida única | 11 | ✅ Cerrado — portada, TOC, tablas, figuras, PDF vía LibreOffice |
| DT-019 | Datos estructurados del LLM para radar chart real (actualmente placeholder) | 16 | ✅ bloque `radar_json` en prompt + `_extract_radar()` en `generate_benchmarking`; fallback garantizado |
| DT-017 | Acoplamientos "piloto" (PDF hardcodeado en `_run_pdf`, footer NOEL) | 10 / 13 | ✅ footer parametrizable + `_run_pdf` retirado (corpus vía UI/lote, ADR-012) |
| DT-018 | Hook check-ruff.sh creado; settings.json pendiente registro manual | 9 | ✅ **Cerrado en Fase 19**: la nota "settings.json actualizado en Fase 10" era falsa (el hook nunca se registró). Cableado en `.claude/settings.json` (PreToolUse `git commit`, antes de secrets/models); verificado exit 0. |
| DT-020 | Persistencia web indiscriminada: se ingesta todo lo buscado (usado o no). Objetivo: persistir **solo lo citado** (`chunks_usados`) + purgar el backlog no usado | 14 | ✅ ADR-013: session ingest + `promote_cited_web` + `sweep_stale` + purga única (backlog 1202→0); la purga subió la evidencia sectorial 3.20→3.68 chunks/consulta |
| DT-021 | Resiliencia OpenRouter free: rate-limits transitorios (`ResourceExhausted 32/32`) sin backoff/reintento dedicado | 15 | ✅ `is_rate_limit_error` + `ResilientChatModel` (free→free_alt→synth→paid); timeouts por tier. Ver `FASE15_HALLAZGOS.md` §4 |
| DT-022 | Reranking/afinado de retrieval: MMR completo + evaluación, `chunk_size` 500→1000, índice parcial/GIN sobre `metadatos->>'sector_gics'` | 14 | ✅ harness T14.1 (métricas propias); MMR medido y **revertido** (degrada mono-doc); `chunk_size` 1000/200 (neutral, se mantiene por eficiencia); índice **descartado** (SQL 15ms). Ver `FASE14_HALLAZGOS.md` + addendum ADR-012 |
| DT-023 | Clasificación GICS: `chain_02_gics` no emite el código (mitigado por `extract_gics_code`). Usar `Comparacion_GICS_CIIU.csv` (CIIU→GICS) para acotar/validar candidatos y endurecer el prompt para emitir "(GICS XXXX)" | 14 | ✅ `ciiu_gics.py` (CIIU→Sección→candidatos); `ClassifyGICS` acota+valida/corrige; `chain_02` endurecido; fallback por nombre conservado; ≥5 CIIU probados |
| DT-024 | Estilo Normal del documento no fijado: objetivo Source Sans Pro 11 pt, justificado, interlineado 1,16, espacio después 8 pt, control de viudas/huérfanas | 16/17 | ✅ `_apply_normal_style()` con **Open Sans** 11 pt (Fase 17; Source Sans Pro no empaquetado en Ubuntu 24.04, instalados `fonts-open-sans` + Carlito) |
| DT-025 | Medición real de latencia `--bench --warm`: los números en `FASE15_HALLAZGOS.md §2` son estimados teóricos (Ollama no disponible en sesión de Fase 15/16) | 17 | ✅ cold 1527.8 ms / warm 158.3 ms → 9.6× mejora. FASE15_HALLAZGOS §2 actualizado con datos reales (E2E post-Fase 16, 2026-07-22) |
| DT-026 | Hit-rate de caché no instrumentado: `CachedWebConnector`/`CachedOpenAlexConnector` no emiten métricas de hits/misses en el log del informe | 17 | ✅ `CacheCounter` thread-safe compartido + log `Cache web: N HITs / M MISSes` al cierre de `_run_n3` + campos en `InformeResult` (commit `7e6ec20`) |
| DT-027 | Hit-rate del bloque `radar_json`: qué % de corridas emiten JSON parseable. Umbral de decisión: ≥ 80% | 17→**22** | 🔴 Tasa confirmada 50% (Nestlé ✅, Avianca ❌ placeholder). Sigue con regex inline (`generate_benchmarking.py:21 _RADAR_RE`); la cadena dedicada temp 0 no se hizo en F18/F19. **Retarget a Fase 22** (robustez). Verificado en Fase 19. |
| DT-028 | `RetrievalCache` no importado en `models/__init__.py`: `create_schema.py` no creaba la tabla `retrieval_cache` (rompe arranque en BD vacía) | E2E post-16 | ✅ import añadido en `src/ic/data/models/__init__.py`. Fix en commit `e2e-post-fase16` |
| DT-029 | `ResilientChatModel` solo hacía fallback ante rate-limit: un `RemoteProtocolError` transitorio abortaba el pipeline completo (incidente EPM, se perdieron Caps 1–5) | 17 | ✅ `is_transient_network_error()` + fallback de tier en `_generate`/`_stream` ante red transitoria; +9 tests; **validado en producción** (corrida Alpina sobrevivió al mismo error) (commit `7c1fec1`) |
| DT-030 | Sin checkpoint antes de barreras de sincronización (Cap 6 / N3): CLAUDE.md TIER 3 exige persistir estado antes de cruzarlas; un fallo tardío descarta Caps 1–5 (~13 min) | 22 | ⬜ Persistir Caps N0/N1/N2 (BD) y permitir **reanudar** una corrida fallida |
| DT-031 | Cap 5/6 inconclusos: falta ingestar `InformeConvergenciaLocal2026RvADAA.pdf` como fuente **global** (aplica a todo sector) cableada al retrieval de Convergencia/Accionables | 18 | ✅ `es_global=True` + reserva global (`rag_global_reserve=2`) + `scripts/ingest_global.py`; 594 chunks globales ingestados. Ver addendum ADR-012 Fase 18. |
| DT-032 | Bug de numeración: tras el capítulo 4 aparecen subcapítulos numerados `5.x` (desfase en headings del renderer o en la estructura del ReportDocument) | 18 | ✅ `chain_05` corregido a 4.1/4.2/4.3 + `renumber_subheadings()` en `markdown_parser.py` como defensa en profundidad; 6 tests. |
| DT-033 | Citación no-APA para PDFs locales: el texto cita el nombre crudo del archivo ("El InformeConvergenciaLocal2026V3RvADAA.pdf destaca…") en vez de (Autor, año). Faltan metadatos APA en la ingesta y en el bloque de fuentes inyectado al prompt | 18 | ✅ `format_chunks_with_meta` omite rutas locales; `_apa_report` solo emite URLs `http`; `pdf_ingestor` con fallback "Ruta N" y título sin `.pdf`; chains 04-07 unificadas; 8 tests de contrato. |
| DT-034 | Ingesta completa del lote EMIS (**250 PDFs, 25 sectores**). El corpus **ya está en disco** en `documentos_sectoriales/FuentesEMIS/<Sector>/` con su índice `documentos_sectoriales/FuentesEMIS/indice_emis.csv` (columnas: archivo, sector_gics, sectores_adicionales, tipo, autor, año, titulo, empresa). Corrida (~2–4 h): `uv run python scripts/ingest_batch.py --dir documentos_sectoriales --csv documentos_sectoriales/FuentesEMIS/indice_emis.csv` (idempotente por título; NO colisiona con los compilados de Fase 13). | 18→23 | ⬜ **Corpus listo, ingesta pendiente.** Es la palanca directa de DT-049 (diversidad de fuentes). Verificado 2026-07-24: 250 filas en el CSV, rutas y columnas compatibles con `ingest_batch.py`. |
| DT-035 | Cap 2 — Competidores sin datos: `WebConnector.search()` usa `search_depth="basic"` y queries genéricas de sector → solo overviews, no perfiles de competidores individuales. Solución: parámetro `search_depth` en `WebConnector.search()` + `search_depth="advanced"` en `generate_benchmarking.py` + queries targeted por empresa/competidor. | 21 | ✅ **Cerrada F21 (T21.1, `1a96d7b`)**: `search_depth` propagado (WebConnector + CachedWebConnector) + queries de competidor `advanced`. Firma pública intacta (default `basic`). |
| DT-036 | Cap 3 — Casos locales off-topic: 594 chunks del InformeConvergenciaLocal2026 contienen casos Medellín/Antioquia multi-sector (KPO, turismo inteligente) que se recuperan para cualquier empresa independientemente de su sector GICS. Causa: reserva global sin constraint sectorial en el prompt de casos locales. Solución: añadir instrucción explícita en `chain_04_tendencias.py` que restrinja los casos locales al sector de la empresa analizada + query web de casos locales sectoriales. | 21 | ✅ **Cerrada F21 (T21.2, `e64c107`)**: constraint sectorial en `chain_04` + query web dedicada de casos locales en `generate_tendencias`. |
| DT-037 | `gateway.py` = 503 L (red flag > 300). Partición en paquete `infrastructure/llm/` (`cost.py`, `ollama.py`, `openrouter.py`, `errors.py`, `resilient.py`, `factory.py`) con `gateway.py` como fachada de re-export para no romper importadores. | 22 | ⬜ Detectado en Fase 19 (T19.2). Riesgo Medio. |
| DT-038 | `presentation/app.py` = 487 L (red flag) **y** violación SoC §3.4: la UI importa `data/` directamente (`SessionLocal`, `EmpresaRepository`, `DocumentoRepository`, `InformeRepository` en L60/132/212). Partir en `presentation/views/` y enrutar el acceso a datos por casos de uso del `domain/`. | 26 | ⬜ Detectado en Fase 19. F26 ya reabre `app.py` para estilo. Riesgo Medio. |
| DT-039 | `generate_informe.py` = 438 L / `_run_n3()` = 157 L. Regresión respecto a ADR-009 (347 L, métodos < 65 L); el crecimiento vino de la lógica APA/ensamblado de Fase 18. Extraer N3 a `domain/use_cases/generate_n3.py` (mismo patrón que `generate_n1.py`, DT-004). | 22 | ⬜ Detectado en Fase 19. Candidato de partición más limpio (precedente existente). |
| DT-040 | `gateway.py:23-29` `_PRICING` hardcodea IDs de modelo (`nvidia/nemotron-…`, `google/gemma-3-…`); el hook `check-hardcoded-models.sh` no los bloquea porque sus patrones exigen dígito pegado (`gemma[0-9]`) y omiten `nemotron`/`gpt-oss`. Decidir: mover la tabla de precios a config/`.env` o declararla excepción explícita, **y** endurecer los patrones del hook (formas con guion + familias faltantes). | 22 | ⬜ Detectado en Fase 19 (T19.3/T19.5). TIER 1 en espíritu. |
| DT-041 | Cobertura de `domain/` en el gate rápido = 69% (< 80% PRIME §6.1). La orquestación N1/N3 (`generate_n1.py` 0%, `generate_informe.py` 34%) solo se cubre con E2E `@slow`. Añadir unit tests de orquestación con dependencias mockeadas para subir el gate sin depender de servicios reales. | 22 | ⬜ Línea base medida en Fase 19 (pytest-cov añadido). |
| DT-042 | Acoplamiento LCEL en `domain/`: las 12 chains importan `langchain_core` (`Runnable`, `ChatPromptTemplate`, `StrOutputParser`) directamente, en tensión con ADR-004 (L49-50: "el wrapper aísla al dominio del framework"). Decidir: documentar la excepción explícita (LCEL como sustrato de orquestación, no "librería envuelta") o introducir una interfaz de cadena en `infrastructure/`. | 22 | ⬜ Divergencia documentada en Fase 19. Severidad Baja (acoplamiento aceptado de facto). |
| DT-043 | **Sesgo sectorial hardcodeado** en system prompts: `chain_03` ("bienes de consumo/FoodTech"), `chain_04` ("agroindustriales") + ecuaciones de búsqueda food-céntricas. Para empresas fuera de alimentos (avianca/bancolombia) el Cap 2 sale plano y con 0 tablas. Parametrizar rol/sector por GICS. | 21 | ✅ **Cerrada F21 (T21.5, `f927ac8`)**: `chain_03`/`chain_04` parametrizados por `{sector_gics}`; fuera "bienes de consumo/FoodTech/agroindustrial". Ecuaciones food → generalizadas en el runbook (T21.3). |
| DT-044 | **Cap 2.3 Mercado ausente**: `source_prompts 4/5` (Mercado) nunca se implementaron como chain; el patrón Noel tiene 2.3 Mercado + tabla de mercado por región (T10). | 21 | ✅ **Cerrada F21 (T21.6, `7883ec6`)**: `chain_03b_mercado` + `CapMercado` + `GenerateMercado` + cableado N1 + interleave entre 2.2 y 2.4 en `assembler`. |
| DT-045 | **Metodología + Aviso de uso de IA ausentes**: el patrón Noel los tiene como secciones formales (Heading 1 + Heading 2); hoy solo hay un `disclaimer` de una línea (Caption). Añadir sección en `assembler.py`. | 21 | ✅ **Cerrada F21 (T21.7, `a97b029`)**: secciones formales Metodología (antes de Referencias) y Aviso de uso de IA (tras Referencias) en `assembler.py`. Estilo fino → F26. |
| DT-046 | **Cap 4 estructura divergente**: `chain_05_ecosistema` produce Local/Global/Disruptores en vez de 4.1 Inversiones / 4.2 Integraciones verticales / 4.3 M&A / 4.4 Joint ventures / 4.5 Alianzas, con eventos (Título + capacidad estratégica adquirida + vulnerabilidad mitigada). Es la mayor divergencia de contenido. | 21 | ✅ **Cerrada F21 (T21.8, `beecd9c`)**: `chain_05` reescrita a 4.1–4.5 (movimientos corporativos), 3 eventos por subcap con los 4 campos del patrón. Doc `prompt-05` actualizado. |
| DT-047 | **Deriva del nº de áreas en Cap 5**: la variante paralela `chain_06a` (RN-009) permite que el LLM improvise áreas (avianca 5.1–5.7 vs 4 fijas del distrito). Restringir a las 4 áreas del patrón. | 22 | ⬜ Detectado en Fase 20 (T20.2). |
| DT-048 | **Score de calidad no automatizado**: `docs/eval/RUBRICA_CALIDAD.md` es manual. Cablear un LLM-judge (temperatura 0) que la aplique sobre el `.docx` y emita score por capítulo, para medir regresión de calidad entre fases. | 22 | ⬜ Propuesto en Fase 20 (T20.1). Severidad Baja. |
| DT-049 | **Evidencia RAG delgada / baja diversidad de fuentes**: en el E2E de cierre F21 (Alpina 3020) el informe citó **solo 3 referencias** (2 documentos compilados + 1 web) con **18 "Dato no disponible"** y Cap 2.1 (fichas de competidor) ausente. Diagnóstico en BD: 2687 chunks totales, 3020 con 44 chunks sectoriales + 594 globales, pero los 44 provienen de **un único documento compilado** por sector → poca diversidad de fuentes citables. **Causa confirmada 2026-07-24:** el lote EMIS diverso (250 PDFs, p. ej. 3020 tiene 13 fuentes: CFA, EMIS, Euromonitor, GlobalData…) **está en disco pero NUNCA se ingestó** (DT-034); la BD solo tiene los compilados de Fase 13. La búsqueda web devolvió 122 chunks pero solo **1 se citó** (resultados poco relevantes tipo `todolicitaciones.cl`; el resto lo purga ADR-013 "solo citado"). Las secciones granulares nuevas (fichas de competidor, 2.3 tabla de mercado, Cap 4 eventos M&A/JV) exigen datos que el corpus compilado no contiene. **Acciones:** (F23) **ingestar el lote EMIS de `documentos_sectoriales/FuentesEMIS/` (ver DT-034)** — es la palanca directa; luego evaluar búsqueda paga; (F22) afinar retrieval/breadth — investigar por qué solo 1 de 122 chunks web se cita, mejorar queries web por competidor con entidades extraídas de Cap 1/2 (T22.4 enriquecimiento dirigido), y revisar si la reserva sectorial y la purga ADR-013 son demasiado agresivas cuando el corpus es concentrado. | **22 (Sprint A)** ✅ / 23 (mix de fuentes) | 🟢 **Validado 2026-07-29** (A1 `4c342c4`): harness sin regresión (prec 1.0, contam 0.0, avg_correct 3.2→3.76) + E2E refs 3→8/14. El *conteo* de diversidad sube; el *mix* sigue web-pesado (EMIS individuales sub-citados) → **DT-054** (F23). Evidencia: `FASE22_HALLAZGOS.md §5/§6`. |
| DT-050 | **Base de conocimiento de empresas (directorio + acumulación)**: los informes siempre buscan competidores/jugadores del mismo sector y hoy esa identificación se recomputa por web en cada corrida (y ADR-013 descarta casi todo). Propuesta: tabla `informes_ic.empresas_directorio` que (a) se **siembra** del corpus `documentos_sectoriales/FuentesEMIS/EmpresasColombia/` (~97.935 empresas colombianas de ISI Markets/WVB: nombre, sector local, actividad, ingreso, ciudad, empleados, descripción, NIT), (b) se **nutre** con las entidades identificadas en cada informe, y (c) se **cura con intervención humana** más adelante (`curado` bool; el usuario indicó "todavía no"). Inyectar jugadores locales como contexto estructurado en Cap 2/4 cierra la mitad "local" de DT-049. Retos: mapeo Sector-Local→GICS, volumen ~98k, dedup por NIT, ToS. Diseño completo en `docs/architecture/PROPUESTA_BASE_EMPRESAS.md`. | 23 (o mini-fase previa) | ⬜ **Propuesto 2026-07-24** (activos aportados por el usuario). No implementado; requiere Plan Mode. Curación humana → HITL (F24/F25). |
| DT-051 | **Ingesta de PDF falla con bytes NUL**: al ingestar el lote EMIS del sector 3020, 10 de 13 PDFs (todos los Euromonitor "Sector Capsule") fallaron con `ValueError: A string literal cannot contain NUL (0x00) characters` — esos PDFs inyectan 0x00 en el texto extraído y PostgreSQL lo rechaza en columnas TEXT. Euromonitor aparece en muchos sectores del lote, así que bloqueaba buena parte del corpus. | — | ✅ **Cerrada F21-post (`1be4993`, merge `3256403`)**: `_sanitize_text()` en `pdf_ingestor.py` elimina NUL y controles C0 (conserva tab/LF/CR) antes de chunkar; +1 test. |
| DT-052 | **Atribución/citación no sigue al corpus recuperado**: prueba A/B de Alpina tras enriquecer el sector 3020 (44→286 chunks / 14 docs). El **contenido mejoró mucho** (Cap 2.1 de ausente → 14 fichas de competidor en tabla; radar de placeholder → datos reales del LLM; 1→16 tablas Word), pero **la citación NO**: las 14 fuentes EMIS nuevas no aparecen en Referencias (siguen 3) ni sus nombres en el texto (Euromonitor/CFA/GlobalData = 0 menciones); 0 chunks web citados (123 descartados por ADR-013); y se detectó una **cita huérfana** `(Alpina, Carvajal Empaques, 2019)`. Riesgo **RN-001**: sin atribución no se puede verificar que las fichas nuevas estén ancladas a fuentes vs sintetizadas. Causa probable: la reserva sectorial/`rag_max_chunks_per_doc` favorece el doc compilado y `build_references_section` solo surface los chunks efectivamente en `chunks_usados`; el LLM redacta desde el contexto sin emitir citas trazables por fuente. **Acción:** F22 Sprint A T22.A2 — asegurar que las fuentes recuperadas y usadas se citen y aparezcan en Referencias, resolver huérfanas, y medir nº de fuentes distintas citadas. | **22 (Sprint A)** ✅ | 🟢 **Validado 2026-07-29** (A2 `e364a52`): E2E Alpina 8 refs / Sofasa 14 refs, **0 huérfanas** en ambos, fuentes EMIS del sector presentes (Informe sectorial 3020/2510 + "Automotor"). RN-001 preservado (huérfanas se suprimen, no se inventan). Evidencia: `FASE22_HALLAZGOS.md §5/§6`. |

| DT-053 | **Documentos multi-sector: capacidad implementada pero sin datos ni medición fiel.** Verificado 2026-07-27: un informe EMIS puede servir a varios sectores/subsectores y el **diseño ya lo soporta** — la ingesta guarda `metadatos["sectores"] = [primario] + adicionales` (`pdf_ingestor.py`, columna CSV `sectores_adicionales`, Fase 18 T18.4) y el retrieval aflora el doc en cualquiera de esos sectores (`embedding_repo.search_similar`: `sector_gics = :sector OR jsonb_exists(sectores, :sector)`). PERO: (a) **la columna `sectores_adicionales` está VACÍA en las 250 filas del CSV** → ningún doc está multi-etiquetado hoy (capacidad dormida); (b) la **idempotencia por título** significa que re-etiquetar un doc ya ingerido NO surte efecto al re-correr el batch (lo salta) → re-etiquetar exige borrar/re-ingerir ese doc o un update path; (c) **la medición no es fiel al multi-sector**: el harness (`retrieval_metrics.py` / `eval_retrieval._to_retrieved`) y el chequeo anti-mezcla de T22.A3 leen SOLO `metadatos["sector_gics"]` (primario), así que un doc legítimamente multi-sector contaría como "contaminación cross-sector" falsa. **Acciones:** (medición, con A3) que el harness y el anti-mezcla consideren on-sector si el sector pedido está en `sectores` (no solo `== sector_gics`); (datos, curación) pase para poblar `sectores_adicionales` en los docs transversales del CSV + procedimiento de re-etiquetado que respete la idempotencia. Refuerza el objetivo de la base documental (reducir dependencia web, ADR-001/003) sin duplicar PDFs. | 22 (medición) ✅ / 23 (curación de datos) | 🟢 **Medición cerrada 2026-07-29** (`04604cf` + anti-mezcla `aeb4482`): harness y `sector_histogram` honran el array `sectores` O el primario. Datos ⬜ (columna `sectores_adicionales` vacía) → curación **F23**. Anti-mezcla E2E `ajeno=0` en 3020 y 2510. |
| DT-054 | **EMIS individuales sub-citados (mix de fuentes web-pesado).** E2E F22 A3: aunque las Referencias subieron (3→8 Alpina / 14 Sofasa) y el corpus tiene ~14 docs por sector completo (13 EMIS individuales + 1 compilado), las citas siguen dominadas por web + el informe compilado; casi ningún EMIS individual se cita. Causa (verificada en BD 2026-07-29): (a) la **reserva sectorial estricta** de `embedding_repo.search_similar` filtra a `metadatos->>'tipo_fuente' = 'informe_compilado'`, y los EMIS individuales tienen `tipo_fuente` NULL → **nunca entran a la reserva garantizada**; (b) en el pool general compiten por score con la web y suelen perder. **Acciones (F23):** ampliar la reserva sectorial más allá del compilado (incluir EMIS individuales) o dar boost de score/etiquetar `tipo_fuente` en la ingesta EMIS; revisar el peso de la web frente a EMIS. Ligado a DT-049 (mix) y DT-053 (multi-sector dormido). | 23 | 🟡 **Abierta 2026-07-29** (hallazgo de A3). No bloquea Sprint A (criterios de refs/huérfanas/anti-mezcla cumplidos). |
| DT-055 | **Fuga de andamiaje del prompt en el intro del Cap 6.** En el E2E de Sofasa, el párrafo introductorio de "Accionables Estratégicos" filtró meta-texto del modelo al `.docx` ("We need to produce a paragraph intro…", "Answer", "(In)"). El *cuerpo* de accionables quedó limpio y cruza capítulos previos (T22.1 OK). Aislado a la cadena de párrafos intro N2; no ocurrió en Alpina (misma cadena, distinta corrida). **Acción (Sprint B):** endurecer/sanear la salida del intro (p. ej. `strip` de reasoning o validación de formato). | 22 Sprint B | 🟡 **Abierta 2026-07-29** (hallazgo de A3). Cosmético/trazabilidad; no afecta anti-mezcla/refs/huérfanas. |
| DT-056 | **Knowledge Base de entidades (empresas + competidores + oportunidades + eventos) con procedencia por campo y estado candidato/verificado.** Generaliza DT-050 a un patrón de entidad único que se **nutre en cada corrida** (idea del usuario 2026-07-29): al recuperar la empresa principal, se enriquece el KB; informes futuros del sector reusan esas entidades como competidores anclados. Cierra causas A/D/E del diagnóstico de competidores. Riesgo clave: sin provenance + gate candidato/verificado, un dato mal extraído se vuelve error sistemático (RN-001 a escala). Incluye pipeline **identificar→enriquecer por entidad (T22.4)** y base de **oportunidades de inversión** (alimenta Cap 4). Diseño en `docs/architecture/PROPUESTA_KNOWLEDGE_BASE.md §1`. | 23 (diseño DBs+agentes → luego UI) | ⬜ **Propuesto 2026-07-29.** Requiere Plan Mode. UI de captura manual → HITL (F24/F25). |
| DT-057 | **Ingesta RAG enriquecida (batch en la reingesta por sector).** La reingesta cuesta ~2 días → batchear lo que no se backfillea barato (metadata enriquecida sube precisión ~73→82 %). Tanda 1 (sí o sí): `tipo_fuente` a EMIS individuales (arregla DT-054), metadata por chunk (sección/página/fecha/idioma), idempotencia por hash + update path (arregla DT-053), **NER en ingesta → `entidad_menciones`** (base de DT-056), preservar tablas/cifras EMIS, poblar `sectores_adicionales`. Tanda 2 (probar 1 sector antes): chunking estructural, doc-summary vector (multi-vector, ataca DT-054). Fuera de default: cambiar embedder (probar vs harness primero). Detalle `PROPUESTA_KNOWLEDGE_BASE.md §2`. | 23 (con reingesta) | ⬜ **Propuesto 2026-07-29.** Se ejecuta junto con la reingesta EMIS por sector. |
| DT-058 | **Cap 4 (Ecosistema) adaptativo.** Hoy fuerza 5 subsecciones fijas (4.1–4.5) aunque no haya evidencia → filler "Dato no disponible". Gatear cada subsección con `check_retrieval_sufficient` (ya existe) y emitir solo las que tienen evidencia; si el cap entero no supera el umbral, omitirlo (ADR-002 datos ausentes). NO eliminar el capítulo: es donde el KB de oportunidades (DT-056) más aportará. `PROPUESTA_KNOWLEDGE_BASE.md §3`. | 22 Sprint B | ⬜ **Acordado 2026-07-29.** |
| DT-059 | **Loop de auto-revisión (extiende T22.7/DT-048).** Patrón Reflection/Reflexion: generar→juez con rúbrica→revisar, **por-nodo dentro de UNA corrida** (no mezclar caps de corridas distintas → coherencia), guardar-el-mejor, parada score≥umbral/sin-mejora/**máx 3**, selectivo (solo el cap que falla el gate). Caps web pueden **re-buscar** en el loop (Reflexion con herramientas); caps de integración solo re-sintetizan. Evaluador OpenRouter/Nemotron (Ollama fallback). Latencia aceptable (manual ~1 semana vs ~1 h). `PROPUESTA_KNOWLEDGE_BASE.md §4`. | 22 Sprint B (T22.7) / posterior | ⬜ **Acordado 2026-07-29.** Se monta sobre T22.7 (LLM-judge) una vez sólido. |

> **Nota de numeración DT-035 (Fase 19):** `FASE18_HALLAZGOS.md §9` reutilizó el ID "DT-035"
> para "verificación E2E de Alpina" (que el §7 de esa misma fase marca ✅ 4/4). El **DT-035
> canónico** es el de esta tabla (competidores Cap 2 / `search_depth`, Fase 21). La entrada de
> Fase 18 se considera cerrada/histórica; no se renumera el hallazgo pasado.

---

# FASE 9 — Estabilización y Gate de Calidad

**Prioridad:** P0 · **Estimación:** ~1 día · **Estado:** ✅ Completada (2026-07-21)

### Objetivo
Dejar el repositorio en verde real y **blindar el gate** para que no vuelva a regresar. Es
el cierre de la Fase 9 iniciada en `5baaf98`.

### Contexto / por qué
`ruff check` reporta hoy **13 errores** (7×E402 + 2×E501 en `gateway.py`, 4×E501 en
`test_pdf_ingestor.py`), introducidos por commits posteriores al último gate verde. DT-009
se documentó como "verificar antes de nuevo código" pero no hay mecanismo que lo imponga:
por eso regresa cada fase. Esta fase corrige y **automatiza** la barrera (DT-018).

### Precondiciones
- Ollama y PostgreSQL accesibles (para DT-005; el resto no los requiere).
- `OPENROUTER_API_KEY` en `.env` (para el E2E de DT-005).

### Lecturas requeridas al iniciar
- `docs/architecture/ROADMAP_FASE9+.md` → esta sección (Fase 9)
- `CLAUDE.md` + `docs/architecture/PRIME DIRECTIVE.md` (§VI calidad, §IV commits)
- `docs/decisions/FASE8_HALLAZGOS.md` (contexto DT-009, gate)
- `pyproject.toml` (config ruff: `line-length=100`, `select=["E","F","I","UP"]`)
- `.claude/settings.json` (hooks actuales: `check-secrets`, `check-hardcoded-models`, `format-python`)
- Archivos a corregir: `src/ic/infrastructure/llm/gateway.py`, `tests/test_pdf_ingestor.py`

### Tareas
- [x] **T9.1** ✅ 13 errores ruff corregidos en `gateway.py` (E402+E501) y `test_pdf_ingestor.py` (E501). Commit `7188674`.
- [x] **T9.2** ✅ Script `check-ruff.sh` creado en `.claude/hooks/`. **Pendiente manual**: registrar en `.claude/settings.json` (clasificador Bash caído durante sesión — H9-02).
- [x] **T9.3** ✅ `Makefile` (`make check`) y `.github/workflows/ci.yml` (inerte, para future remoto).
- [x] **T9.4** ✅ DT-005 ejecutado: `test_cap5_paralelo_e2e` pasó en **165.87 s** con Ollama + PostgreSQL + OpenRouter reales (< límite 30 min).
- [x] **T9.5** ✅ `generate_informe.py` = 347 líneas. Documentado en FASE9_HALLAZGOS.md; separación planificada para Fase 12 (T12.5).

### Entregables
- Repo con `ruff check` = 0 errores y `pytest -m "not slow"` = todo verde.
- Hook `check-ruff.sh` operativo + entrada en `.claude/settings.json`.
- Workflow de CI (activo o preparado).
- `docs/decisions/FASE9_HALLAZGOS.md` con: qué se corrigió, resultado de DT-005, decisión de ramas/CI.

### Criterios de aceptación (Definition of Done)
1. `uv run ruff check src/ tests/` → `All checks passed!`
2. `uv run pytest -m "not slow" -q` → 0 failed.
3. Commit de prueba muestra que el hook de ruff bloquea si se introduce un error.
4. DT-005 ejecutado (o documentado por qué no se pudo, con plan).
5. Tablero (§4) y deuda técnica (§5) actualizados.

### Riesgos
- El clasificador de Bash pudo estar caído en fases previas (H8-02). Si vuelve a ocurrir,
  documentarlo y no dar por verde sin ejecutar.
- DT-005 puede tardar >30 min o topar rate-limit del tier free (RN-009). Aceptable
  documentarlo como observación.

### PROMPT DE ARRANQUE — Fase 9
```text
Estás ejecutando la FASE 9 (Estabilización y Gate de Calidad) del roadmap del sistema de
Informes de Inteligencia Competitiva. Trabaja según las reglas de
/home/aagudelo/Test/InformesAuto/CLAUDE.md y docs/architecture/PRIME DIRECTIVE.md.

PASO 0 — Ramas (flujo PRIME DIRECTIVE §4.3, ya adoptado): parte de `develop` (si no existe,
créala desde `main`) y crea la rama de trabajo `feature/fase9-gate-calidad`. NO trabajes en
`main` ni en `develop` directamente. Al cerrar la fase, mergea a `develop` con `--no-ff`.

PASO 1 — LEE antes de tocar nada:
- docs/architecture/ROADMAP_FASE9+.md  → sección "FASE 9" (y §2 Convenciones)
- CLAUDE.md
- docs/decisions/FASE8_HALLAZGOS.md
- pyproject.toml  (config de ruff)
- .claude/settings.json  (hooks actuales)
- src/ic/infrastructure/llm/gateway.py y tests/test_pdf_ingestor.py

PASO 2 — Diagnostica: corre `uv run ruff check src/ tests/ --output-format=concise` y
`uv run pytest -m "not slow" -q`. Reporta el estado real.

PASO 3 — Entra en Plan Mode y propón el plan detallado de las tareas T9.1–T9.5. Espera
aprobación.

PASO 4 — Ejecuta:
- Corrige los errores ruff (T9.1).
- Crea el hook bloqueante check-ruff.sh y regístralo en .claude/settings.json (T9.2, DT-018).
- CI LOCAL (no hay remoto): hook pre-push o script `make check` que corra ruff+pytest y
  bloquee si falla; deja un .github/workflows/ci.yml preparado (inerte) para el futuro (T9.3).
- Ejecuta el E2E lento de Cap 5 (T9.4, DT-005) con OpenRouter y registra tiempos.
- Revisa tamaño de generate_informe.py (T9.5, DT-004).

PASO 5 — Gate: `uv run ruff check src/ tests/` y `uv run pytest -m "not slow" -q` en verde.

PASO 6 — Documenta en docs/decisions/FASE9_HALLAZGOS.md (usa el patrón de FASE8_HALLAZGOS.md).

PASO 7 — Actualiza en ROADMAP_FASE9+.md: el TABLERO DE AVANCE (§4, fila Fase 9), la deuda
técnica (§5, DT-005/009/018) y el changelog (§8). Marca las tareas T9.x hechas.

PASO 8 — Cierre: confirma conmigo el mensaje de commit (Conventional Commits), commitea en
`feature/fase9-gate-calidad` y mergea a `develop` con `--no-ff`. Luego redacta y propón el
PROMPT DE ARRANQUE de la FASE 10, ajustándolo con lo aprendido en esta fase.

Pregunta si algo no está claro.
```

---

# FASE 10 — Fiabilidad del Contenido

**Prioridad:** P0 · **Estimación:** ~3–4 días · **Estado:** ⬜ Pendiente

### Objetivo
Que el informe sea **confiable para tomar decisiones**, no solo plausible: idioma
controlado en todo el documento, citación APA 7 fiel y **trazabilidad claim↔fuente** real
en el cuerpo del texto.

### Contexto / por qué
- RN-007 solo valida idioma (CJK) en Cap 1; el resto puede colarse en otro idioma (DT-009).
- RN-002 exige trazabilidad, pero hoy las referencias existen al final sin **cita inline**
  que ancle cada afirmación a su chunk. Un informe de IC sin cita rastreable no es fiable.
- `apa_formatter.py` produce APA aproximado (sin sangría francesa, sin cursivas, orden y
  formato de autor naíf, `clave` sin uso) → DT-015.
- Acoplamientos "piloto": footer "NOEL" y PDF hardcodeado (DT-017, se limpia aquí y en 13).

### Lecturas requeridas al iniciar
- `docs/architecture/ROADMAP_FASE9+.md` → esta sección (Fase 10)
- `docs/business-rules/REGLAS_NEGOCIO.md` (RN-001, RN-002, RN-007)
- `src/ic/infrastructure/citation/apa_formatter.py`
- `src/ic/shared/text_utils.py` (`has_cjk_characters`)
- `src/ic/domain/absent_data.py`
- `src/ic/domain/chains/` (todas las chains: cómo se inyecta el contexto y las fuentes)
- `src/ic/domain/use_cases/generate_*.py` (cómo se pasan `chunks_usados`)
- `src/ic/domain/assembler.py` (footer/piloto)

### Tareas
- [ ] **T10.1** Extender validación de idioma a todos los caps N1–N3 (post-generación).
      Centralizar en una utilidad; si un cap falla, aplicar política de datos ausentes
      (RN-001) o reintento. (Cierra DT-009 lado idioma.)
- [ ] **T10.2** Citación inline trazable (RN-002): inyectar en cada chain el bloque de
      fuentes numeradas de sus `chunks_usados` y exigir en el prompt citas `(Fuente, año)`.
      Validar post-generación que toda cita del texto exista en las referencias; loguear
      huérfanas.
- [ ] **T10.3** Reescribir `format_reference` a APA 7 fiel: sangría francesa (en el
      renderizador, coordinar con Fase 11), cursiva de títulos/fuentes, orden alfabético
      correcto, tipos diferenciados (web / artículo OpenAlex / PDF sectorial). (DT-015.)
- [ ] **T10.4** Tests de contrato APA (varios tipos de fuente → salida esperada).
- [ ] **T10.5** Panel de fiabilidad por informe: cobertura de evidencia (% caps con
      `retrieval_suficiente`), nº fuentes por cap, caps en modo ausencia. Persistir en
      `HistorialInforme` y mostrar en la UI (tab Historial).
- [ ] **T10.6** Desacoplar "piloto": footer/disclaimer parametrizables; sacar el nombre de
      empresa y textos fijos de `assembler.py`. (El PDF hardcodeado se aborda en Fase 13.)

### Entregables
- Validación de idioma global operativa + tests.
- Citación inline trazable + validador de citas huérfanas.
- `apa_formatter.py` en APA 7 fiel + tests de contrato.
- Métricas de fiabilidad persistidas y visibles en UI.
- `docs/decisions/FASE10_HALLAZGOS.md`.

### Criterios de aceptación
1. Todo cap generado pasa por validación de idioma (test que lo demuestre).
2. Una afirmación con fuente en el texto es rastreable a un chunk (test E2E o unit sobre el validador).
3. Referencias APA 7 correctas para ≥3 tipos de fuente (tests verdes).
4. UI muestra el panel de fiabilidad de un informe del historial.
5. Gate ruff + pytest verde. Tablero y deuda técnica actualizados.

### Riesgos
- Forzar cita inline puede degradar la fluidez del texto del LLM free-tier: iterar el prompt.
- La sangría francesa real es de renderizado (docx) → coordinar con Fase 11; en Fase 10 dejar
  el dato estructurado correcto y el string APA, y aplicar el estilo visual en Fase 11.

### PROMPT DE ARRANQUE — Fase 10
```text
Estás ejecutando la FASE 10 (Fiabilidad del Contenido) del roadmap del sistema de Informes
de Inteligencia Competitiva. Trabaja según CLAUDE.md y docs/architecture/PRIME DIRECTIVE.md.

PASO 1 — LEE:
- docs/architecture/ROADMAP_FASE9+.md → sección "FASE 10"
- docs/decisions/FASE9_HALLAZGOS.md (lo aprendido en la fase previa)
- docs/business-rules/REGLAS_NEGOCIO.md (RN-001, RN-002, RN-007)
- src/ic/infrastructure/citation/apa_formatter.py
- src/ic/shared/text_utils.py y src/ic/domain/absent_data.py
- src/ic/domain/chains/  y  src/ic/domain/use_cases/generate_*.py (cómo fluyen chunks/fuentes)
- src/ic/domain/assembler.py

PASO 2 — Entra en Plan Mode y propón el plan de T10.1–T10.6. Espera aprobación.

PASO 3 — Ejecuta las tareas: validación de idioma global (T10.1), cita inline trazable +
validador de huérfanas (T10.2), APA 7 fiel + tests de contrato (T10.3/T10.4), panel de
fiabilidad persistido y en UI (T10.5), desacople del "piloto" en assembler (T10.6).

PASO 4 — Gate: ruff limpio + pytest -m "not slow" verde. Añade tests en el mismo cambio.

PASO 5 — Documenta en docs/decisions/FASE10_HALLAZGOS.md.

PASO 6 — Actualiza ROADMAP_FASE9+.md: tablero §4 (Fase 10), deuda técnica §5 (DT-009,
DT-015, DT-017), changelog §8. Marca tareas T10.x.

PASO 7 — Redacta y propón el PROMPT DE ARRANQUE de la FASE 11 con lo aprendido.

Confirma el mensaje de commit conmigo antes de commitear. Pregunta si algo no está claro.
```

---

# FASE 11 — Formato del Documento Final

**Prioridad:** P0 (es el entregable comercial) · **Estimación:** ~4–5 días · **Estado:** ⬜ Pendiente

### Objetivo
Convertir el `.docx` plano actual en un **documento profesional**: portada con membrete,
TOC, encabezados/pies con paginación, **tablas reales**, **imágenes/gráficos**, callouts y
referencias APA con sangría francesa. Habilitar **salida en PDF** (y opcionalmente HTML).

### Contexto / por qué
`docx_builder.py` solo soporta headings, viñetas y negrita; `assembler.py` habla directo a
python-docx (acopla contenido a un formato). El benchmarking de 14 competidores se emite
como prosa en vez de tabla. No hay imágenes, TOC ni portada. Salida única .docx. (DT-016.)

### Decisión de arquitectura (a validar en Plan Mode)
Introducir un **modelo de documento** intermedio y renderizadores múltiples, respetando
Dependency Agnosticism (PRIME DIRECTIVE §1.2):

```
domain/report_model.py     → bloques: Heading, Paragraph, Table, Figure, Callout,
                             Citation, PageBreak, Toc  (dominio, sin conocer docx/pdf/html)
infrastructure/render/
    docx_renderer.py        → python-docx (master editable)
    pdf_renderer.py        → docx→pdf vía LibreOffice headless  (ver §7-Q2)
    html_renderer.py       → Jinja2 → HTML (preview UI / correo)  [opcional en esta fase]
```

**Estrategia de formatos recomendada:** master **.docx** (editable por el analista) →
**PDF** por conversión (una sola fuente de verdad de estilo = la plantilla membrete). HTML
como render paralelo desde el mismo modelo para preview. No mantener 3 motores de maquetación.

### Lecturas requeridas al iniciar
- `docs/architecture/ROADMAP_FASE9+.md` → esta sección (Fase 11)
- `src/ic/infrastructure/docx_builder.py` y `src/ic/domain/assembler.py`
- `src/ic/shared/types.py` (DTOs: `InformePiloto`, `Cap*`, `Referencia`)
- `src/ic/domain/use_cases/generate_informe.py` (`_run_n3` ensamblado)
- `src/ic/domain/chains/chain_03_benchmarking.py` (necesita emitir datos estructurados para tabla)
- Plantilla membrete (`settings.docx_template_path`, si existe)
- Resultado de Fase 10 (APA fiel) en `docs/decisions/FASE10_HALLAZGOS.md`

### Tareas
- [x] **T11.1** Definir `domain/report_model.py` (bloques semánticos, inmutables) + tests.
- [x] **T11.2** `infrastructure/render/docx_renderer.py`: portada + TOC + encabezado/pie con
      paginación + estilos + sangría francesa en referencias. Refactor de `assembler.py`
      para construir el modelo y delegar en el renderer.
- [x] **T11.3** **Tablas reales:** `markdown_parser.py` detecta `|col|col|` → `TableBlock` Word.
      `CapBenchmarking.tabla_data` añadido para uso futuro (DT-019).
- [x] **T11.4** **Imágenes/gráficos:** `infrastructure/charts/radar_chart.py` (matplotlib Agg).
      `FigureBlock` con `alt`. Radar chart placeholder 5×5 embebido en Cap 2.
- [x] **T11.5** **Salida PDF:** `pdf_renderer.py` (LibreOffice headless). Botón descarga PDF en UI.
- [ ] **T11.6** *(Opcional)* `html_renderer.py` + preview del informe en la UI. → Pospuesto.
- [x] **T11.7** Callouts para "datos ausentes" y "accionables"; disclaimer parametrizable (Fase 10).

### Entregables
- Modelo de documento + renderer docx enriquecido + renderer PDF.
- Cap 2 con tabla real; al menos un gráfico embebido.
- UI con descarga .docx y .pdf.
- `docs/decisions/FASE11_HALLAZGOS.md` + posible ADR-011 (modelo de documento + estrategia de formatos).

### Criterios de aceptación
1. `.docx` generado tiene portada, TOC, paginación y referencias con sangría francesa.
2. Cap 2 se renderiza como tabla (no prosa) y hay ≥1 figura con `alt`.
3. Se genera un PDF válido desde el mismo informe.
4. `domain/` no importa python-docx ni matplotlib directamente (solo via infrastructure).
5. Gate ruff + pytest verde. Tablero y deuda técnica actualizados.

### Riesgos
- Conversión docx→PDF depende de LibreOffice en el entorno (§7-Q2). Si no está, evaluar
  WeasyPrint (desde HTML) o `docx2pdf`. Documentar la elección en ADR-011.
- Emitir datos estructurados desde las chains puede requerir tocar prompts → iterar y testear.
- Riesgo de exceder 300 líneas en renderer: dividir por responsabilidad (portada, cuerpo, refs).

### PROMPT DE ARRANQUE — Fase 11
```text
Estás ejecutando la FASE 11 (Formato del Documento Final) del roadmap del sistema de
Informes de Inteligencia Competitiva. Trabaja según CLAUDE.md y PRIME DIRECTIVE
(respeta Dependency Agnosticism: el dominio NO importa python-docx/matplotlib).

PASO 1 — LEE:
- docs/architecture/ROADMAP_FASE9+.md → sección "FASE 11" (incluye la decisión de arquitectura
  del modelo de documento + renderers)
- docs/decisions/FASE10_HALLAZGOS.md (APA fiel ya resuelto)
- src/ic/infrastructure/docx_builder.py, src/ic/domain/assembler.py
- src/ic/shared/types.py, src/ic/domain/use_cases/generate_informe.py (_run_n3)
- src/ic/domain/chains/chain_03_benchmarking.py

PASO 2 — Verifica el entorno para PDF: comprueba si LibreOffice está disponible
(`which soffice libreoffice`). Reporta la opción de conversión que usarás.

PASO 3 — Entra en Plan Mode. Propón: (a) el modelo de documento report_model.py, (b) los
renderers, (c) cómo Cap 2 emitirá datos estructurados para la tabla, (d) qué gráfico(s)
generar, (e) la estrategia de PDF. Considera registrar un ADR-011. Espera aprobación.

PASO 4 — Ejecuta T11.1–T11.7 (HTML T11.6 es opcional según tiempo).

PASO 5 — Gate: ruff limpio + pytest -m "not slow" verde. Genera un informe de prueba y
adjunta/verifica el .docx y el .pdf resultantes.

PASO 6 — Documenta en docs/decisions/FASE11_HALLAZGOS.md y, si aplica, crea
docs/architecture/ADR-011-*.md.

PASO 7 — Actualiza ROADMAP_FASE9+.md: tablero §4 (Fase 11), deuda técnica §5 (DT-016),
lista de ADR, changelog §8. Marca tareas T11.x.

PASO 8 — Redacta y propón el PROMPT DE ARRANQUE de la FASE 12.

Confirma el mensaje de commit conmigo. Pregunta si algo no está claro.
```

---

# FASE 12 — Optimización de Operación

**Prioridad:** P1 · **Estimación:** ~2–3 días · **Estado:** ⬜ Pendiente

### Objetivo
Hacer la generación **más rápida, barata y resiliente**, y preparar la operación para varios
informes: caché de retrieval, resiliencia ante rate-limit del tier free, costo de Ollama y
cola/multi-empresa.

### Contexto / por qué
- Cap 5 llegó a 79 min por rate-limit (RN-009, mitigado pero no eliminado).
- Cada corrida re-consulta web/OpenAlex desde cero (gasto de créditos Tavily + latencia).
- Ollama no expone tokens → no hay costo registrado para sus llamadas (DT-010).
- La UI genera un informe a la vez; historial sin paginar (DT-012).

### Lecturas requeridas al iniciar
- `docs/architecture/ROADMAP_FASE9+.md` → esta sección (Fase 12)
- `docs/business-rules/REGLAS_NEGOCIO.md` (RN-008 presupuesto, RN-009 subdivisión)
- `src/ic/infrastructure/llm/gateway.py` (`CostTracker`, tiers, circuit breaker)
- `src/ic/infrastructure/sources/web_connector.py` y `openalex_connector.py`
- `src/ic/infrastructure/retrieval/` (embedder, pgvector_store, chunker)
- `src/ic/data/repositories/informe_repo.py` (`list_recientes`) y `presentation/app.py`

### Tareas
- [ ] **T12.1** Caché de retrieval: cachear resultados web/OpenAlex por `(query, ttl)` en BD
      (tabla en `informes_ic`) para no re-consultar en cada corrida. → Pospuesto a Fase 14.
- [ ] **T12.2** Resiliencia free-tier: timeouts/paralelismo por tier configurables; backoff
      explícito ante 429/rate-limit; métrica de latencia por cap. → Pospuesto a Fase 14.
- [x] **T12.3** ✅ DT-010: `CostTracker.add_ollama_call()` + `tiempo_ollama_s` en `CallRecord`;
      tokens reales desde respuesta Ollama (`prompt_eval_count`, `eval_count`, `total_duration`).
- [x] **T12.4** ✅ DT-012: historial paginado (PAGE_SIZE=10, offset), filtro ILIKE por empresa
      y exportación CSV desde la UI.
- [x] **T12.5** ✅ DT-004: `_run_n1` extraído a `generate_n1.py`; `generate_informe.py` = 345 L.

### Entregables
- Caché de retrieval operativa + tests.
- Backoff/resiliencia configurables + métricas de latencia.
- Costo de Ollama registrado.
- UI con cola y paginación.
- `docs/decisions/FASE12_HALLAZGOS.md`.

### Criterios de aceptación
1. Una segunda corrida de la misma empresa reutiliza caché (test o log que lo demuestre).
2. Ante un 429 simulado, el sistema aplica backoff y no aborta.
3. El historial muestra costo/tiempo también para pasos con Ollama.
4. La UI encola ≥2 informes o pagina el historial.
5. Gate ruff + pytest verde. Tablero y deuda técnica actualizados.

### PROMPT DE ARRANQUE — Fase 12
```text
Estás ejecutando la FASE 12 (Optimización de Operación) del roadmap del sistema de Informes
de Inteligencia Competitiva. Trabaja según CLAUDE.md y PRIME DIRECTIVE.

PASO 1 — LEE:
- docs/architecture/ROADMAP_FASE9+.md → sección "FASE 12"
- docs/decisions/FASE11_HALLAZGOS.md
- docs/business-rules/REGLAS_NEGOCIO.md (RN-008, RN-009)
- src/ic/infrastructure/llm/gateway.py
- src/ic/infrastructure/sources/web_connector.py y openalex_connector.py
- src/ic/infrastructure/retrieval/ (embedder, pgvector_store)
- src/ic/data/repositories/informe_repo.py y src/ic/presentation/app.py

PASO 2 — Entra en Plan Mode. Propón el plan de T12.1–T12.5 (caché de retrieval, resiliencia
free-tier, costo Ollama, cola/paginación). Espera aprobación.

PASO 3 — Ejecuta. Añade tests (incluye simulación de rate-limit y de cache hit).

PASO 4 — Gate: ruff limpio + pytest -m "not slow" verde.

PASO 5 — Documenta en docs/decisions/FASE12_HALLAZGOS.md.

PASO 6 — Actualiza ROADMAP_FASE9+.md: tablero §4 (Fase 12), deuda técnica §5 (DT-004,
DT-010, DT-012), changelog §8. Marca tareas T12.x.

PASO 7 — Redacta y propón el PROMPT DE ARRANQUE de la FASE 13 (repositorio sectorial RAG).

Confirma el mensaje de commit conmigo. Pregunta si algo no está claro.
```

---

# FASE 13 — Repositorio Sectorial RAG

**Prioridad:** P1 (mayor palanca de calidad de evidencia) · **Estimación:** ~5–7 días · **Estado:** ⬜ Pendiente

### Objetivo
Convertir los documentos sectoriales (EMIS/informes industriales + papers académicos en PDF)
en un **corpus curado con filtrado por sector GICS**, gestionado desde la UI, con ciclo de vida
controlado (activar/desactivar/borrar). El retrieval priorizará chunks del corpus del sector
correcto antes de buscar en la web genérica.

### Decisiones ya tomadas (2026-07-21 — no re-discutir)
1. **Tipos de documentos:** PDFs sectoriales (EMIS, reportes industriales) + papers académicos.
   Mismo flujo de ingesta para ambos.
2. **Metadatos:** cada documento lleva `sector_gics` (ej. `"Consumer Staples"`) y opcionalmente
   `empresa_nombre`. El retrieval filtra por `sector_gics` del informe activo antes de buscar.
3. **Ingesta:** el analista sube PDFs manualmente desde un panel en la UI Streamlit.
4. **Ciclo de vida:** columna `activo: bool = True` en `DocumentoLocal`. Desactivar excluye
   chunks del retrieval sin borrarlos. Panel permite: listar, activar/desactivar y borrar.
5. **Carga masiva inicial:** script `scripts/ingest_batch.py` con CSV de índice para los
   26+ docs existentes (columnas: archivo, sector_gics, tipo, autor, año, empresa).

### Contexto / por qué
- La infraestructura ya existe: `PdfIngestor` (RN-010), pgvector, `DocumentoLocal`
  (ya tiene `empresa_id`, `tipo`, `metadatos`). Falta `sector_gics`, `activo` y la UI de gestión.
- Los 26+ PDFs se ingestan una vez; el retrieval sectorial reemplaza la búsqueda web genérica
  para evidence sectorial, mejorando fiabilidad y reduciendo costo Tavily.
- Se limpia `_run_pdf` hardcodeado (DT-017).

### Lecturas requeridas al iniciar
- `docs/architecture/ROADMAP_FASE9+.md` → esta sección (Fase 13)
- `docs/architecture/ADR-001` (RAG propio), `ADR-003` (fuentes), `ADR-005` (retrieval)
- `docs/business-rules/REGLAS_NEGOCIO.md` (RN-004, RN-010)
- `src/ic/data/models/documento_local.py` (DocumentoLocal — base a extender)
- `src/ic/data/models/embedding_vectorial.py` (EmbeddingVectorial — sin cambiar tabla)
- `src/ic/shared/constants/__init__.py` (TipoDocumento, FuenteTipo actuales)
- `src/ic/infrastructure/sources/pdf_ingestor.py` (firma de ingest_batched)
- `src/ic/infrastructure/retrieval/pgvector_store.py` (search — añadir filtros)
- `src/ic/data/repositories/embedding_repo.py` (search_similar)
- `src/ic/shared/constants/gics_groups.py` (sectores GICS disponibles)
- `src/ic/presentation/app.py` (patrón UI existente — pestaña Historial como referencia)
- **Externo:** carpeta con los PDFs sectoriales + CSV de índice (el usuario los provee al arrancar)

### Tareas — Parte A: Diseño (antes de código)
- [ ] **T13.A** Leer esquema actual → proponer cambios → ADR-012 → esperar aprobación:
  - `DocumentoLocal`: añadir `sector_gics TEXT`, `activo BOOL DEFAULT TRUE`.
    Migración idempotente `ensure_documento_columns()` (patrón de `ensure_historial_columns()`).
  - `EmbeddingVectorial`: NO cambiar tabla; propagar `sector_gics` a `metadatos` JSONB
    de cada chunk en ingesta (más simple que JOIN en query pgvector) O añadir columna
    `sector_gics TEXT` directa (decide según benchmark de query).
  - `TipoDocumento`: añadir `PAPER_ACADEMICO = "paper_academico"`.
  - `PGVectorStore.search(query, k, sector_gics=None, solo_activos=True)`: evaluar si
    filtro va en la query pgvector (IVFFlat soporta WHERE) o post-filtrado en Python.

### Tareas — Parte B: Implementación
- [ ] **T13.1** Migraciones BD + constantes: `sector_gics`, `activo` en `DocumentoLocal`;
      `PAPER_ACADEMICO` en `TipoDocumento`. Tests de migración.
- [ ] **T13.2** `PdfIngestor.ingest_batched()`: añadir `sector_gics: str | None` a firma;
      propagar a `metadatos` de cada chunk.
- [ ] **T13.3** `PGVectorStore.search()` con filtros: `sector_gics` + `solo_activos`.
      Actualizar todos los callers (use cases N1/N2). Tests unitarios con mocks.
- [ ] **T13.4** Panel "Repositorio" en app.py (nueva pestaña):
      subida PDF + metadatos (sector GICS, tipo, año, autor, empresa opcional);
      listado con toggle activo/inactivo y borrado con confirmación.
- [ ] **T13.5** Script `scripts/ingest_batch.py`: lee `indice.csv`, procesa cada PDF con
      `PdfIngestor`, loguea resultados. Para carga masiva inicial de los 26+ docs.
- [ ] **T13.6** Generalizar `_run_pdf` en `generate_informe.py` (DT-017): de PDF
      hardcodeado a "cargar documentos activos del sector GICS del informe".
- [ ] **T13.7** Evaluación: con 2–3 empresas, comparar nº de fuentes sectoriales citadas
      vs. línea base sin corpus. Reportar en FASE13_HALLAZGOS.md.
- [ ] **T13.8** *(Opcional)* Estudiar RAG de `~/Test/RepositorioRN`: documentar si hay
      chunking, reranking o filtros aprovechables. Registrar en ADR si cambia diseño.

### Entregables
- `DocumentoLocal` con `sector_gics` y `activo`; migración idempotente.
- `PdfIngestor` y `PGVectorStore` con filtrado sectorial.
- Panel Streamlit "Repositorio": subir, listar, activar/desactivar, borrar.
- Script `ingest_batch.py` para carga masiva con CSV.
- `_run_pdf` generalizado (DT-017 cerrado).
- `docs/decisions/FASE13_HALLAZGOS.md` + ADR-012 (filtrado sectorial).

### Criterios de aceptación
1. Un informe de sector X prioriza chunks de documentos con `sector_gics=X` (test/log).
2. Desactivar un documento excluye sus chunks del siguiente informe (test o demo).
3. Los 26+ PDFs ingestados con metadata correcta (verificar n_chunks en panel).
4. `_run_pdf` ya no hardcodea nombre de archivo.
5. Gate ruff + pytest verde. Tablero, deuda técnica y ADR actualizados.

### Riesgos
- Volumen de PDFs: ingesta larga (~5–30 min para 26 docs). Ejecutar script fuera del
  pipeline de informe con nohup o tmux.
- Calidad de extracción de texto en PDFs con tablas/OCR → validar muestra antes de ingestar todo.
- Filtro sectorial en pgvector: benchmarkear JOIN vs. JSONB vs. columna TEXT antes de decidir.

### PROMPT DE ARRANQUE — Fase 13
```text
Estás ejecutando la FASE 13 (Repositorio Sectorial RAG) del sistema de Informes de IC.
Trabaja según CLAUDE.md y PRIME_DIRECTIVE.md.

ANTES DE EMPEZAR — pídeme al usuario:
1. La ruta de la carpeta con los PDFs sectoriales (ej. ~/documentos_sectoriales/)
2. Si existe, la ruta del CSV de índice (archivo, sector_gics, tipo, autor, año, empresa)
   Si no existe, lo crearemos juntos en el PASO A3.
3. Si quieres que revise el RAG del equipo en ~/Test/RepositorioRN (opcional).

DECISIONES YA TOMADAS (no re-discutir, vienen del cierre de Fase 11):
- Tipos: PDFs sectoriales + papers académicos (mismo flujo de ingesta).
- Metadatos: sector_gics + empresa_nombre opcional. Retrieval filtra por sector_gics.
- Ingesta: UI Streamlit (panel "Repositorio") + script CLI para lote inicial.
- Ciclo de vida: activo:bool en DocumentoLocal. Toggle en UI sin borrar chunks.

PASO 0 — Ramas:
  git log --oneline -5  (confirma merge de Fase 12)
  git checkout develop && git checkout -b feature/fase13-rag-sectorial

PASO 1 — Gate de entrada:
  uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q

PASO 2 — LEE el esquema actual (OBLIGATORIO antes de planificar):
  - docs/architecture/ROADMAP_FASE9+.md → sección "FASE 13" (decisiones ya tomadas + tareas)
  - src/ic/data/models/documento_local.py (DocumentoLocal — base)
  - src/ic/data/models/embedding_vectorial.py (EmbeddingVectorial)
  - src/ic/shared/constants/__init__.py (TipoDocumento, FuenteTipo)
  - src/ic/infrastructure/sources/pdf_ingestor.py (ingest_batched firma actual)
  - src/ic/infrastructure/retrieval/pgvector_store.py (search — sin filtros hoy)
  - src/ic/data/repositories/embedding_repo.py (search_similar)
  - src/ic/shared/constants/gics_groups.py
  - src/ic/presentation/app.py (pestaña Historial — patrón UI a replicar)
  - src/ic/domain/use_cases/generate_informe.py (_run_pdf hardcodeado — DT-017)

PASO 3 — Entra en Plan Mode (PARTE A — solo diseño, sin código):
  Propón T13.A: cambios al esquema (sector_gics, activo, PAPER_ACADEMICO),
  estrategia de filtrado en pgvector (columna vs. JSONB — justificar con query plan),
  y firma nueva de PGVectorStore.search(). Incluye ADR-012 como entregable.
  Espera aprobación.

PASO 4 — Ejecuta T13.1–T13.7 en orden (Parte B). Gate ruff+pytest tras cada tarea.
  Nota: T13.5 (ingest_batch.py) puede requerir una corrida larga fuera del pipeline;
  usar nohup o tmux si hay muchos docs.

PASO 5 — Gate final + evaluación T13.7: comparar cobertura de fuentes vs. línea base.

PASO 6 — Documenta en docs/decisions/FASE13_HALLAZGOS.md + ADR-012.

PASO 7 — Actualiza ROADMAP_FASE9+.md: tablero §4 (Fase 13), deuda §5 (DT-011, DT-017,
DT-019), lista de ADR, changelog §8. Marca tareas T13.x.

PASO 8 — Confirma el commit conmigo (Conventional Commits). Commitea y mergea a
`develop` con --no-ff.

Pregunta si algo no está claro antes de empezar.
```

---

## 6. Roadmap posterior (re-secuenciado 2026-07-24, v3.0: auditoría → calidad → fuentes → HITL → estilo)

Tras 18 fases cerradas se hizo un **"alto en el camino"** (sesión 2026-07-24): antes de seguir
añadiendo funcionalidad, auditar que la infraestructura, el código y la documentación estén
alineados con la necesidad del producto y las buenas prácticas del proyecto, y medir la brecha
de calidad contra el informe patrón manual (`InformeSectoryCompetitivoNoel.docx`, en la raíz).
Con ese diagnóstico se ejecutan las fases de contenido y robustez ya diseñadas, se amplía la
base de evidencia, se implementa el HITL aprobado en ADR-015 y se cierra con el pulido visual:

- **Fase 19 — Auditoría de Arquitectura, Código y Documentación.** SoC/wrappers, red flags de
  tamaño (gateway 503 L, app 487 L, generate_informe 438 L), coherencia ADRs/RN ↔ código,
  revalidación de la deuda §5. Su salida re-prioriza las fases 20–26.
- **Fase 20 — Gap Analysis de Calidad vs Informe Patrón (Noel).** Rúbrica de calidad por
  capítulo derivada del patrón, evaluación de ≥3 informes generados, auditoría de fidelidad
  chains ↔ `source_prompts/` (13 docx; `docs/prompts/` solo tiene 4 migrados).
- **Fase 21 — Calidad de Contenido — Sprint A + A'** (ex-F19). ✅ Cerrada: DT-035 competidores,
  DT-036 casos locales off-topic, runbook ecuaciones de búsqueda (Sprint A) + DT-043 des-sesgo,
  DT-044 Cap 2.3 Mercado, DT-045 Metodología/Aviso IA, DT-046 rediseño Cap 4 (Sprint A').
- **Fase 22 — Coherencia y Robustez del Informe** (ex-F20: Q1 contexto caps previos, DT-027
  radar dedicado, DT-030 checkpoint/--resume, + T22.5 enriquecimiento dirigido post-N1:
  entidades halladas en un capítulo alimentan búsquedas de contraste para otros).
- **Fase 23 — Fuentes: Corpus EMIS completo + Servicios de búsqueda pagos.** DT-034 (lote 250
  PDFs) + matriz de proveedores pagos con techo ≤ 20 USD/mes y piloto A/B medible → ADR-016.
- **Fase 24 — HITL Módulo 1: Gap Auditor** (ex-F21, ADR-015).
- **Fase 25 — HITL Módulo 2: Consistency Checker + pruebas de UI HITL** (ex-F22, ADR-015).
- **Fase 26 — Estilo y Visualización del Documento Final** (Q7 + rúbrica visual de F20):
  plantilla de estilos Word más rica, callouts, colores corporativos, tablas estilizadas,
  jerarquía tipográfica, transiciones narrativas, QA visual sistemático .docx/.pdf.
- **Fase 27+** — Operación continua: actualización programada del corpus (cron de re-ingesta y
  frescura), multi-tenant / control de acceso, exportación a portal web / API (FastAPI).

> **Nota de numeración:** ADR-015 y documentos previos a v3.0 referencian el HITL como
> "Fases 21–22" (numeración v2.5). En v3.0 corresponden a las Fases 24–25. Los ADR no se
> reescriben (son inmutables); esta nota es el mapeo oficial.

---

# FASE 14 — Calidad de Retrieval y Evaluación

**Prioridad:** P1 · **Estado:** ✅ Completada (2026-07-22, `1fbe8a1`) · **Deuda:** DT-020/022/023 cerradas

> **Cierre T14.x:** T14.1 ✅ harness+gold set · T14.2 ✅ MMR medido y **revertido** (λ=1.0
> default; degrada con evidencia mono-documento) · T14.3 ✅ chunk_size 1000/200 (neutral, se
> mantiene por eficiencia) · T14.4 ✅ índice **descartado** (SQL 15ms) · T14.5 ✅ persistencia
> web "solo lo citado" (ADR-013) + purga 1202→0 · T14.6 ✅ CIIU→GICS. Ver `FASE14_HALLAZGOS.md`.

### Objetivo
Elevar la calidad y el rigor del retrieval RAG con evidencia medible. Fase 13 dejó tres
hallazgos concretos: (a) el backlog de chunks web sin ciclo de vida compite con el corpus
sectorial, (b) los scores sectoriales son bajos (~0.68–0.78) con `chunk_size=500`, y (c) la
clasificación GICS por LLM puede desviarse del sector real. Se introduce evaluación
cuantitativa (RAGAS) para no optimizar a ciegas.

### Tareas
- **T14.1 (DT-022) — Evaluación de retrieval.** Harness reproducible (RAGAS o métricas
  propias: context precision/recall) con un set de consultas por sector. Línea base actual.
- **T14.2 (DT-022) — MMR completo.** Portar el reranking por diversidad de documento de
  RepositorioRN (`services/rag/mmr.py`) al `PGVectorStore`, reemplazando el cap simple.
  Comparar contra la línea base de T14.1.
- **T14.3 (DT-022) — `chunk_size` 500→1000 / overlap 200.** Re-chunking del corpus;
  medir impacto en scores y recall. Decidir con datos de T14.1.
- **T14.4 (DT-022) — Índice parcial/GIN.** Evaluar `hnsw` + índice sobre
  `metadatos->>'sector_gics'`; medir latencia con el corpus completo.
- **T14.5 (DT-020) — Persistencia web "solo lo usado".** Rediseñar el flujo: los resultados
  web dejan de persistirse **al buscar**; se usan para el retrieval de la corrida y, al
  ensamblar, **solo se persisten los chunks web efectivamente citados** (presentes en
  `chunks_usados`, los que alimentan `build_references_section`). **Purga única** del backlog
  web histórico no usado (~2024 chunks). Referencia de borrado por lote:
  `DocumentoRepository.delete_with_chunks`. Evita que el ruido web crezca sin control y
  conserva solo la evidencia aplicada.
- **T14.6 (DT-023) — CIIU→GICS para enfocar búsquedas y validar la clasificación.** Cargar
  `documentos_sectoriales/Comparacion_GICS_CIIU.csv` (versionado en git; datos, no binario).
  Añadir en `shared/` un mapeo CIIU numérico → Sección CIIU Rev4 (divisiones: 01-03=A, 05-09=B,
  10-33=C, 35=D, 36-39=E, 41-43=F, 45-47=G, 49-53=H, 55-56=I, 58-63=J, 64-66=K, 68=L, 69-75=M,
  77-82=N, 84=O, 85=P, 86-88=Q, 90-93=R, 94-96=S, 97-98=T, 99=U) → conjunto de **códigos GICS
  candidatos** (resolviendo los nombres del CSV a códigos con matching tolerante, estilo
  `extract_gics_code`). Usarlo para (a) **acotar** la clasificación del LLM a los candidatos
  cuando se conoce el CIIU y (b) validar/corregir `sector_gics` antes del filtro. Mantener el
  fallback por nombre y endurecer `chain_02_gics` para emitir "(GICS XXXX)".
  > Nota: la tabla es gruesa y multivaluada (1 Sección → varios GICS). Ej.: Comfama CIIU 8430 →
  > división 84 → Sección O → candidato "Servicios comerciales y profesionales".

### Criterios de cierre
- Métricas de retrieval antes/después documentadas en `FASE14_HALLAZGOS.md` (mejora medible).
- Gate verde (ruff 0 + `pytest -m "not slow"`); tests para MMR, persistencia "solo usado" y
  el mapeo CIIU→GICS.
- Decisiones de `chunk_size`/índice/persistencia registradas (actualizar ADR-005/ADR-012 si
  aplica).

### Prompt de arranque — Fase 14

```
# ROL Y MISIÓN
Eres el ingeniero a cargo de la FASE 14 (Calidad de Retrieval y Evaluación) del sistema de
Informes de Inteligencia Competitiva. Tu misión: elevar la calidad del retrieval RAG con
evidencia MEDIBLE, no por intuición. Trabajas según CLAUDE.md y docs/architecture/PRIME_DIRECTIVE.md.

# MÉTODO DE TRABAJO (obligatorio)
Dos partes: PARTE A (diseño en Plan Mode, esperar aprobación) → PARTE B (ejecución).
El plan es la especificación: si la realidad diverge del plan, DETENTE y vuelve a Plan Mode.
Cambios atómicos (cada entrega compila y corre). Tests en el mismo PR que el código.

# RESTRICCIONES DURAS (no negociables)
- Modelos solo en .env (nunca hardcodear nombres). Sin secretos en git.
- Dependency Agnosticism: domain NO importa SQLAlchemy ni Streamlit; todo acceso externo por
  wrapper en infrastructure/.
- NO re-discutir ADR-012 (filtrado sectorial, reserva de cupos, fallback por nombre). Se
  construye SOBRE él.
- Política de datos acordada: la información web solo persiste si fue EFECTIVAMENTE CITADA en
  un informe. No re-litigar.

# ESTADO DE ENTRADA (Fase 13 cerrada)
Branch develop (merge 62fe327). Corpus: 25 docs / 1746 chunks (sector_gics +
tipo_fuente=informe_compilado, activos). Backlog web: ~2024 chunks sin ciclo de vida.
181 tests fast, ruff 0.

# PASO 0 — GATE DE ENTRADA
Ejecuta: uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q
Debe dar 0 errores / verde. Si no, arréglalo antes de continuar.

# PASO 1 — LECTURA OBLIGATORIA (antes de planificar)
docs/decisions/FASE13_HALLAZGOS.md · docs/architecture/ADR-012-filtrado-sectorial.md ·
ROADMAP_FASE9+.md (sección FASE 14) · ~/Test/RepositorioRN/app/backend/services/rag/mmr.py ·
src/ic/infrastructure/retrieval/{pgvector_store,embedder,chunker}.py ·
src/ic/data/repositories/embedding_repo.py · src/ic/infrastructure/sources/web_connector.py ·
use cases N1/N2 (patrón self._store.ingest(..., fuente_tipo="web") al buscar) ·
src/ic/domain/use_cases/generate_informe.py (chunks_usados → build_references_section) ·
documentos_sectoriales/Comparacion_GICS_CIIU.csv (Sección CIIU → GICS).

# PASO 2 — PLAN MODE (Parte A). Diseña las tareas EN ORDEN, cada una con su criterio de éxito:

T14.1 — Harness de evaluación (PRIMERO; sin métricas no se optimiza).
  Entrega: script reproducible + set de consultas etiquetadas por sector (gold set) que
  reporta context precision / context recall / cross-sector contamination por consulta.
  ÉXITO: corre con un comando, fija la LÍNEA BASE actual en números, y es determinista.

T14.2 — MMR completo (portar de RepositorioRN mmr.py), reemplazando el cap simple por doc.
  ÉXITO: en el harness T14.1, mejora la diversidad de documentos SIN degradar precision/recall
  frente a la línea base; parametrizable (mmr_lambda en config). Test unitario del reranking.

T14.3 — chunk_size 500→1000 / overlap 200 (re-chunking del corpus).
  ÉXITO: decisión basada en datos de T14.1 (recall/score antes vs después). Si no mejora, se
  documenta y se revierte. Reproducible (re-ingesta idempotente).

T14.4 — Índice parcial/GIN sobre metadatos->>'sector_gics' (evaluar hnsw + índice).
  ÉXITO: latencia de búsqueda medida antes/después con el corpus completo; sin regresión de
  resultados. Decisión registrada.

T14.5 (DT-020) — Persistencia web "solo lo citado".
  Rediseña: los resultados web NO se persisten al buscar; se usan para el retrieval de la
  corrida y, al ensamblar, SOLO se persisten los chunks web presentes en chunks_usados. Purga
  ÚNICA del backlog web histórico no usado (~2024 chunks).
  ÉXITO: tras generar un informe, en BD solo quedan chunks web que fueron citados; el conteo de
  chunks web no crece con búsquedas descartadas. Tests de la lógica de "promover solo lo usado"
  y del borrado por lote. Referencia: DocumentoRepository.delete_with_chunks.

T14.6 (DT-023) — CIIU→GICS para acotar/validar la clasificación.
  Carga Comparacion_GICS_CIIU.csv; mapea CIIU numérico → Sección CIIU Rev4 → códigos GICS
  candidatos (matching tolerante de nombres, estilo extract_gics_code). Úsalo para acotar la
  clasificación del LLM cuando se conoce el CIIU y validar/corregir sector_gics antes del filtro.
  Endurece chain_02_gics para emitir "(GICS XXXX)"; conserva el fallback por nombre.
  ÉXITO: con CIIU conocido, sector_gics resuelto ∈ candidatos del CSV; test con ≥5 CIIU reales
  (incl. Comfama 8430→Sección O). No rompe empresas sin CIIU.

Espera aprobación del plan antes de escribir código.

# PASO 3 — EJECUCIÓN (Parte B)
Implementa T14.1→T14.6 en orden. CADA cambio de T14.2–T14.6 se justifica con números del
harness T14.1 (antes/después). No optimizar a ciegas.

# CRITERIOS DE ÉXITO GLOBALES (Definition of Done)
1. Gate verde: ruff 0 + pytest -m "not slow". Cobertura de domain ≥ 80%.
2. Mejora MEDIBLE del retrieval sobre la línea base T14.1 (precision/recall y/o menor
   contaminación cross-sector), documentada con la tabla antes/después.
3. Persistencia web: verificado en BD que solo persiste lo citado; backlog no usado purgado.
4. CIIU→GICS operativo y probado; clasificación más robusta sin romper el flujo sin-CIIU.
5. Tests nuevos para MMR, persistencia "solo usado" y mapeo CIIU→GICS.

# PASO 4 — VERIFICACIÓN
Corre el gate. Ejecuta el harness T14.1 y adjunta la tabla de métricas antes/después.
Genera 1 informe E2E (empresa con CIIU conocido) y confirma: sector correcto filtrado, solo
fuentes citadas persistidas.

# PASO 5 — DOCUMENTACIÓN (obligatoria al cierre)
Actualiza la documentación del proyecto con AVANCES, RETOS y RECOMENDACIONES:
- docs/decisions/FASE14_HALLAZGOS.md: qué se logró (métricas antes/después), retos
  encontrados y cómo se resolvieron, y recomendaciones/follow-ups para fases siguientes.
- ROADMAP_FASE9+.md: tablero §4 (Fase 14 ✅ + hash), deuda §5 (DT-020/022/023 cerrados o
  actualizados), changelog §8. Marca T14.x.
- ADR nuevo/actualizado si cambió una decisión estructural (MMR, chunk_size, índice, persistencia).
- Confirma el commit conmigo antes de mergear a develop.
```

---

# FASE 15 — Resiliencia y Costo

**Prioridad:** P1 · **Estado:** ⬜ Pendiente · **Deuda:** DT-021, T12.1, T12.2

### Objetivo
Reducir latencia y costo del pipeline y hacerlo resiliente a rate-limits, **explotando los
hallazgos cuantitativos de Fase 14**. Fase 14 dejó el retrieval en buen estado y —sobre todo—
**instrumentación medible** (harness T14.1 con `--bench`/`--bench-sql`) que ahora se usa como
gate de latencia/costo, no solo de calidad.

### Hallazgos de Fase 14 que motivan esta fase (leer `FASE14_HALLAZGOS.md`)
1. **El embedding domina el ~99% de la latencia** (~1320 ms por consulta; el SQL es ~15 ms).
   Causa: `nomic-embed-text` con `keep_alive:0` **recarga el modelo en cada llamada**
   (`infrastructure/retrieval/embedder.py`). Es la **mayor palanca de rendimiento** del sistema
   (afecta re-ingesta, harness, y cada búsqueda N1/N2). Reconciliar con la política de VRAM de
   ADR-006 (por eso está en `keep_alive:0`): buscar un *toggle de lote* seguro.
2. **Sin caché de retrieval** (T12.1): web/OpenAlex se re-consultan en cada corrida; con la nueva
   persistencia "solo lo citado" (ADR-013) tiene aún más sentido cachear la *búsqueda*, no el
   *chunk*.
3. **Rate-limits OpenRouter free** (DT-021): el gateway usa `tenacity @retry` con
   `wait_exponential` genérico, pero **no detecta el 429/rate-limit del free-tier** (llega en el
   body sin disparar `raise_for_status`, ver `gateway.py:233`). Falta backoff dedicado + fallback
   de tier.
4. **Higiene de tests**: `purge_unused_web_backlog()` es global (borra todo el backlog legacy);
   seguro en régimen permanente (legacy=0) pero conviene un scoping opcional para tests.

### Tareas
- **T15.1 (hallazgo Fase 14, mayor palanca) — Estrategia de embedding.** Introducir un modo de
  lote con `keep_alive` positivo (o servidor de embeddings persistente) para re-ingesta/harness/
  N1, manteniendo `keep_alive:0` como default seguro de VRAM. Medir el antes/después con el
  harness T14.1 `--bench` (objetivo: colapsar el 99% de latencia en lotes). Wrapper en
  `infrastructure/`, parametrizado por `.env` (nunca hardcodear).
- **T15.2 (T12.1) — Caché de retrieval.** Cachear resultados web/OpenAlex por `(query, ttl)` en
  una tabla del esquema `informes_ic` para no re-consultar en cada corrida. Invalidación por TTL.
  Medir hit-rate y ahorro de latencia/llamadas.
- **T15.3 (DT-021, T12.2) — Resiliencia free-tier.** Detectar 429/rate-limit del body de
  OpenRouter (no solo HTTP status), backoff dedicado + fallback de tier (free→free_alt→synth→
  paid) con logging. Timeouts/paralelismo por tier configurables en `.env`.
- **T15.4 — Gate de costo/latencia.** Extender el harness T14.1 (o un check de CI) para fijar un
  presupuesto de latencia/costo y detectar regresiones (aprovecha `latency_ms`/`latency_sql_ms`
  ya en los snapshots). Integrar con `CostTracker.within_budget`.
- **T15.5 — Higiene y deuda menor.** Scoping opcional de `purge_unused_web_backlog` para tests;
  revisar el `POST /api/generate` observado en la ingesta; reconciliar `keep_alive` con ADR-006.

### Criterios de cierre
- Reducción **medible** de latencia (harness `--bench`) y/o de llamadas (caché) documentada en
  `FASE15_HALLAZGOS.md` antes/después.
- Resiliencia demostrada: una corrida sobrevive a un 429 simulado sin abortar (fallback de tier).
- Gate verde (ruff 0 + `pytest -m "not slow"`); tests para caché, backoff/fallback y el modo de
  embedding en lote. Cobertura `domain/` ≥ 80%.
- Decisiones estructurales en ADR (caché, keep_alive de lote) si aplica.

### Prompt de arranque — Fase 15

```
# ROL Y MISIÓN
Eres el ingeniero a cargo de la FASE 15 (Resiliencia y Costo) del sistema de Informes de
Inteligencia Competitiva. Tu misión: reducir latencia y costo y hacer el pipeline resiliente a
rate-limits, con evidencia MEDIBLE usando el harness T14.1 ya existente. Trabajas según CLAUDE.md
y docs/architecture/PRIME_DIRECTIVE.md.

# MÉTODO DE TRABAJO (obligatorio)
Dos partes: PARTE A (diseño en Plan Mode, esperar aprobación) → PARTE B (ejecución).
El plan es la especificación: si la realidad diverge del plan, DETENTE y vuelve a Plan Mode.
Cambios atómicos (cada entrega compila y corre). Tests en el mismo PR que el código.

# RESTRICCIONES DURAS (no negociables)
- Modelos y parámetros de infra (keep_alive, timeouts, TTL) solo en .env / config (nunca
  hardcodear nombres ni valores mágicos en código de aplicación). Sin secretos en git.
- Dependency Agnosticism: domain NO importa SQLAlchemy/httpx/Streamlit; todo acceso externo por
  wrapper en infrastructure/.
- NO re-litigar decisiones cerradas: ADR-012 (filtrado sectorial), ADR-013 (persistencia web
  solo-citado), MMR desactivado por defecto, chunk_size 1000/200. Se construye SOBRE ellas.
- keep_alive:0 es el default de VRAM por ADR-006; cualquier keep_alive positivo debe ser un modo
  de LOTE explícito y acotado, no el default.

# ESTADO DE ENTRADA (Fase 14 cerrada)
Branch develop (merge de feature/fase14-retrieval-eval, 1fbe8a1). Corpus: 25 docs / 998 chunks
(chunk_size 1000/200). Backlog web purgado (0). 223 tests fast, ruff 0. Harness de evaluación
operativo (scripts/eval_retrieval.py con --bench/--bench-sql; snapshots en docs/decisions/).

# PASO 0 — GATE DE ENTRADA
uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q  → 0 errores / verde.

# PASO 1 — LECTURA OBLIGATORIA (antes de planificar)
docs/decisions/FASE14_HALLAZGOS.md (§4/§5/§9: latencia embed, índice, follow-ups) ·
docs/architecture/ADR-013-persistencia-web-solo-citado.md · ADR-006 (keep_alive/VRAM) ·
src/ic/infrastructure/llm/gateway.py (tenacity @retry, within_budget, tiers, gateway.py:233
rate-limit en body) · src/ic/infrastructure/retrieval/embedder.py (keep_alive:0, _RETRY_WAITS) ·
src/ic/infrastructure/sources/{web_connector,openalex_connector}.py · scripts/eval_retrieval.py
(--bench/--bench-sql, snapshots) · Fase 12 T12.1/T12.2 (pospuestos) · DT-021 en §5.

# PASO 2 — PLAN MODE (Parte A). Diseña las tareas EN ORDEN, cada una con criterio de éxito:

T15.1 — Estrategia de embedding (MAYOR PALANCA; el embed es ~99% de la latencia).
  Modo de lote con keep_alive positivo/servidor persistente para re-ingesta/harness/N1;
  keep_alive:0 sigue siendo el default seguro. Parametrizado en .env.
  ÉXITO: colapso medible de la latencia en lotes (harness --bench antes/después); sin regresión
  funcional; reconciliado con ADR-006. Test del wrapper de embedding en modo lote.

T15.2 (T12.1) — Caché de retrieval web/OpenAlex por (query, ttl) en el esquema informes_ic.
  ÉXITO: hit-rate medido; una segunda corrida idéntica no re-consulta la web (assert de llamadas
  al connector); invalidación por TTL probada.

T15.3 (DT-021) — Resiliencia free-tier: detectar 429 en el body, backoff dedicado + fallback de
  tier (free→free_alt→synth→paid) con logging; timeouts/paralelismo por tier en .env.
  ÉXITO: una corrida sobrevive a un 429 simulado sin abortar (fallback); test del detector 429 y
  del fallback de tier.

T15.4 — Gate de costo/latencia sobre el harness (o CI): presupuesto configurable, detecta
  regresiones usando latency_ms/latency_sql_ms de los snapshots + CostTracker.within_budget.
  ÉXITO: el gate falla ante una regresión inyectada y pasa en la línea base.

T15.5 — Higiene: scoping opcional de purge_unused_web_backlog para tests; investigar el
  POST /api/generate en la ingesta; reconciliar keep_alive con ADR-006.
  ÉXITO: tests de persistencia sin efecto colateral global; nota de decisión.

Espera aprobación del plan antes de escribir código.

# PASO 3 — EJECUCIÓN (Parte B)
Implementa T15.1→T15.5 en orden. CADA cambio se justifica con números del harness (latencia/
llamadas antes/después). No optimizar a ciegas.

# CRITERIOS DE ÉXITO GLOBALES (Definition of Done)
1. Gate verde: ruff 0 + pytest -m "not slow". Cobertura de domain ≥ 80%.
2. Reducción MEDIBLE de latencia (harness --bench) y/o de llamadas (caché), con tabla antes/
   después en FASE15_HALLAZGOS.md.
3. Resiliencia demostrada ante 429 (fallback de tier), probada.
4. Gate de costo/latencia operativo.
5. Tests nuevos para embedding-en-lote, caché y backoff/fallback.

# PASO 4 — VERIFICACIÓN
Corre el gate. Ejecuta el harness --bench antes/después de T15.1 y adjunta la tabla. Genera 1
informe E2E y confirma tiempo total reducido y supervivencia a rate-limits.

# PASO 5 — DOCUMENTACIÓN (obligatoria al cierre)
- docs/decisions/FASE15_HALLAZGOS.md: logros (latencia/costo antes/después), retos y
  recomendaciones/follow-ups para fases siguientes (énfasis en oportunidades detectadas).
- ROADMAP_FASE9+.md: tablero §4 (Fase 15 ✅ + hash), deuda §5 (DT-021/T12.1/T12.2), changelog §8.
- ADR nuevo/actualizado si cambió una decisión estructural (caché, keep_alive de lote).
- Confirma el commit conmigo antes de mergear a develop.
```

---

# FASE 16 — Presentación del Contenido

**Prioridad:** P1 · **Estado:** ⬜ Pendiente · **Deuda:** DT-019, DT-024 + cableado E2E Fase 15

### Objetivo

Cerrar la brecha entre el pipeline funcional y un **entregable visualmente profesional**: radar
chart alimentado por datos reales del LLM, estilo tipográfico correcto en el .docx y tablas Word
para las fichas de competidores. También incorpora el **cableado E2E de Fase 15** (caché de
retrieval y ResilientChatModel) que quedó pendiente.

### Contexto / por qué

- **DT-019:** El radar chart en Cap 2 usa datos placeholder generados aleatoriamente
  (`generate_placeholder_radar`). Para que sea útil, los scores deben provenir del análisis
  real del LLM sobre los competidores identificados.
- **DT-024:** `docx_renderer.py` aplica estilos de título/párrafo pero no fija el estilo
  Normal del documento (fuente, tamaño, interlineado, espaciado, viudas/huérfanas). El
  documento resultante hereda los defaults de Word/LibreOffice en lugar de la tipografía
  corporativa acordada.
- **Cableado Fase 15 (pendiente):** `generate_n1.py` y `generate_informe.py` construyen
  `WebConnector`/`OpenAlexConnector` directos (sin caché) y los tiers LLM se instancian
  individualmente (sin fallback resiliente). Las clases `CachedWebConnector`,
  `CachedOpenAlexConnector` y `build_resilient_api_llm` existen pero no están conectadas
  al pipeline E2E.

### Tareas

- [x] **T16.0 ✅ — Cableado E2E de Fase 15 (prerequisito)**
  - [x] `generate_n1.py`: `_store` inyecta `CachedWebConnector`/`CachedOpenAlexConnector` por thread.
  - [x] `generate_informe._setup_infra`: un solo `build_resilient_api_llm` reemplaza 3 tiers.
  - [x] `_run_n0`/`_run_n2`: `CachedWebConnector` con sesión local propia.
  - [ ] `--bench --warm` con Ollama activo: pendiente ejecución manual (Ollama no disponible en sesión).
  - [x] Test: `test_cached_pipeline.py` verifica que la 2ª búsqueda usa caché (1 sola llamada real).

- [x] **T16.1 ✅ — Datos reales del LLM para el radar chart (DT-019)**
  - [x] `chain_03_benchmarking.py`: instrucción `\`\`\`radar_json` al final del prompt.
  - [x] `generate_benchmarking.py`: `_extract_radar()` extrae y limpia; `radar_data` en `CapBenchmarking`.
  - [x] `generate_informe._run_n3`: usa `generate_radar_chart` con datos reales; fallback garantizado.
  - [x] Tests: 5 tests en `test_radar_extract.py` (válido, inválido, ausente, whitespace, claves).

- [x] **T16.2 ✅ — Estilo Normal del .docx (DT-024)**
  - [x] `docx_renderer._apply_normal_style()`: Calibri 11pt, justificado, 1.16x, 8pt after, viudas.
  - [x] Tests: 5 tests en `test_docx_style.py` verifican cada propiedad del estilo Normal.

- [x] **T16.3 ✅ — Tablas Word para fichas de competidores**
  - [x] `SYSTEM_PROMPT_03`: instrucción explícita de formato markdown pipe para fichas.
  - [x] Tests: `test_docx_table_block_rendered` y `test_docx_multiple_tables_rendered`.

### Criterios de cierre

- Gate verde: `ruff 0` + `pytest -m "not slow"`.
- `--bench --warm` ejecutado y tabla antes/después en `FASE15_HALLAZGOS.md`.
- Radar chart con datos reales en un informe E2E (verificado visualmente).
- Estilo Normal correcto en el .docx + test de sanidad verde.
- Fichas de competidores como tablas Word visibles.
- `docs/decisions/FASE16_HALLAZGOS.md` creado.
- Tablero §4 y deuda §5 actualizados.

### PROMPT DE ARRANQUE — Fase 16

```text
# ROL Y MISIÓN
Eres el ingeniero a cargo de la FASE 16 (Presentación del Contenido) del sistema de
Informes de Inteligencia Competitiva. Tu misión: (a) cablear en el pipeline E2E el caché de
retrieval y ResilientChatModel implementados en Fase 15, y (b) mejorar el entregable visual:
radar chart con datos reales, estilo Normal correcto en .docx y tablas Word para fichas de
competidores. Trabajas según CLAUDE.md y docs/architecture/PRIME_DIRECTIVE.md.

# MÉTODO DE TRABAJO (obligatorio)
Dos partes: PARTE A (Plan Mode — leer → proponer → esperar aprobación) → PARTE B (ejecución).
El plan es la especificación. Cambios atómicos. Tests en el mismo commit que el código.

# RESTRICCIONES DURAS
- Modelos y parámetros solo en .env (nunca hardcodear nombres ni valores mágicos en código).
- Dependency Agnosticism: domain/ NO importa SQLAlchemy/httpx/matplotlib/Streamlit.
- No re-litigar ADR-006 (keep_alive:0 default), ADR-012 (filtrado sectorial), ADR-013
  (persistencia web solo-citado). Se construye SOBRE ellos.
- El fallback a placeholder en T16.1 es obligatorio: si el LLM no emite JSON parseable, el
  informe sigue generándose (no abortar).

# ESTADO DE ENTRADA (Fase 15 cerrada)
Branch develop (merge 46f5748). 262 tests fast, ruff 0.
Implementado en Fase 15 pero NO cableado en el pipeline E2E:
  - CachedWebConnector / CachedOpenAlexConnector (src/ic/infrastructure/sources/cached_connector.py)
  - build_resilient_api_llm() (src/ic/infrastructure/llm/gateway.py)
  - Medición real --bench --warm pendiente (FASE15_HALLAZGOS.md §2 tiene solo estimados teóricos)
Radar chart: generate_placeholder_radar() en generate_informe.py:333 (datos hardcodeados).
Estilo Normal: no fijado en DocxRenderer (DT-024).

# PASO 0 — GATE DE ENTRADA
uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q  → 0 errores / verde.

# PASO 1 — LECTURA OBLIGATORIA (antes de planificar)
docs/decisions/FASE15_HALLAZGOS.md (§8 recomendaciones — cableado pendiente) ·
docs/architecture/ADR-014-cache-retrieval-batch-keep-alive.md ·
src/ic/infrastructure/sources/cached_connector.py ·
src/ic/infrastructure/llm/gateway.py (build_resilient_api_llm, ResilientChatModel) ·
src/ic/domain/use_cases/generate_informe.py (líneas 94–130 _setup_infra; 327–335 radar) ·
src/ic/domain/use_cases/generate_n1.py (cómo construye WebConnector/OpenAlexConnector) ·
src/ic/infrastructure/charts/radar_chart.py (generate_radar_chart, generate_placeholder_radar) ·
src/ic/domain/chains/chain_03_benchmarking.py (prompt actual — dónde insertar JSON de scores) ·
src/ic/infrastructure/render/docx_renderer.py (DocxRenderer.render — estilos actuales) ·
docs/architecture/ROADMAP_FASE9+.md → sección FASE 16 (tareas T16.0–T16.3, criterios).

# PASO 2 — PLAN MODE (Parte A)
Diseña las tareas EN ORDEN, cada una con su criterio de éxito:

T16.0 — Cableado E2E de Fase 15 (PREREQUISITO).
  - generate_n1.py y generate_informe.py: inyectar CachedWebConnector/CachedOpenAlexConnector.
  - generate_informe._setup_infra: reemplazar tiers individuales por build_resilient_api_llm.
  - Ejecutar --bench --warm con Ollama activo y actualizar FASE15_HALLAZGOS.md §2 con datos reales.
  ÉXITO: segunda corrida idéntica no llama al connector real (test con mock 0 llamadas).

T16.1 (DT-019) — Datos reales del LLM para radar chart.
  - Añadir instrucción JSON al final del prompt de chain_03 (scores 5 dimensiones × N competidores).
  - Extraer JSON en generate_informe.py; llamar generate_radar_chart con datos reales.
  - Fallback a generate_placeholder_radar si parse falla (log WARNING, no abort).
  ÉXITO: radar en E2E usa datos del LLM; test del fallback verde.

T16.2 (DT-024) — Estilo Normal del .docx.
  - DocxRenderer: fijar fuente (Source Sans Pro o Calibri), 11 pt, justificado,
    interlineado múltiple 1,16, espacio después 8 pt, viudas/huérfanas activo.
  ÉXITO: test abre .docx y verifica propiedades del estilo Normal.

T16.3 — Tablas Word para fichas de competidores.
  - Verificar que el markdown_parser detecte las tablas del Cap 2 y el renderer las emita
    como tablas Word nativas.
  ÉXITO: .docx E2E contiene ≥1 tabla Word con columnas visibles (assert en test).

Espera aprobación antes de escribir código.

# PASO 3 — EJECUCIÓN (Parte B)
Implementa T16.0→T16.3 en orden. Después de T16.0 ejecutar --bench --warm y añadir tabla
a FASE15_HALLAZGOS.md (actualizar con datos reales).

# CRITERIOS DE ÉXITO GLOBALES (Definition of Done)
1. Gate verde: ruff 0 + pytest -m "not slow". Cobertura domain/ ≥ 80%.
2. Segunda corrida del pipeline no llama a WebConnector/OpenAlexConnector (caché activo).
3. Rate-limit simulado → pipeline no aborta (ResilientChatModel fallback activo).
4. Radar chart en E2E con datos LLM reales (no placeholder).
5. Estilo Normal verificado en .docx (test de sanidad).
6. ≥1 tabla Word de ficha de competidor en el .docx E2E.

# PASO 4 — DOCUMENTACIÓN (obligatoria al cierre)
- docs/decisions/FASE16_HALLAZGOS.md: logros, retos, recomendaciones.
- FASE15_HALLAZGOS.md §2: actualizar con medición real --bench --warm.
- ROADMAP_FASE9+.md: tablero §4 (Fase 16 ✅ + hash), deuda §5 (DT-019/024), changelog §8.
- Confirma el commit conmigo antes de mergear a develop.
```

---

# FASE 17 — Instrumentación, Calidad de Radar y Pulido E2E

**Prioridad:** P1 · **Estado:** ✅ Completada (2026-07-23) · **Deuda:** DT-026 ✅, DT-024 ✅, DT-029 ✅ · **Rama:** `feature/fase17-instrumentacion`

### Resumen de cierre (detalle en `FASE17_HALLAZGOS.md`)

- **T17.1 (DT-026) ✅** — `CacheCounter` thread-safe compartido, inyectado en las 5
  construcciones de `Cached*Connector` (n0, n2, ×3 n1); log de hits/misses al cierre de
  `_run_n3`; campos en `InformeResult`; +3 tests (`7e6ec20`).
- **T17.2 (DT-027) 🔴→Fase 19** — N=5 corridas completas (Nestlé, Alpina 762 s, Bancolombia
  555 s, Avianca 1088 s; EPM abortó pre-fix). Radar observable: Nestlé ✅ / Avianca ❌ → tasa
  50% < 80% → **decisión: cadena dedicada de extracción** (Fase 19).
- **T17.3 ✅** — Cross-sector validado: EPM → GICS 5510 (Utilities), filtrado
  `sector_gics='5510'` operativo en pgvector.
- **T17.4 (DT-024) ✅** — Open Sans 11 pt en estilo Normal (`NORMAL_FONT_NAME`).
- **DT-029 ✅ (no planificada, crítica)** — Incidente EPM (`RemoteProtocolError` abortó el
  pipeline en Cap 6). Fix: `is_transient_network_error()` + fallback de tier ante red
  transitoria; **validado en producción** en la corrida de Alpina (`7c1fec1`).
- **Extra:** fix logging `run_pilot.py` (ic.* a INFO); fix ruff `eval_gate.py`; E501
  pre-existente en `models/__init__.py`.
- **Gate de cierre:** 289 tests fast, ruff 0.

### Hallazgos que definen las fases siguientes (Q1–Q7, ver `FASE17_HALLAZGOS.md` §7)

Las corridas E2E revelaron 7 problemas de calidad del documento → reordenaron el roadmap
posterior (§6): Fase 18 (evidencia/citación), Fase 19 (coherencia/radar/checkpoint),
Fase 20 (estilo y visualización).

---

# FASE 18 — Evidencia y Citación

**Prioridad:** P0 (mayor palanca de calidad del contenido) · **Estimación:** ~3–4 días · **Estado:** ⬜ Pendiente · **Deuda:** DT-031, DT-032, DT-033 + Q5/Q6

### Objetivo

Que el contenido de los informes esté **anclado en más y mejor evidencia, citada
correctamente**: documentos globales cross-sector para Cap 5/6, documentos extra por
empresa/sector (EMIS), citación APA real para PDFs locales, menos secciones en "información
no disponible" y numeración de capítulos correcta.

### Contexto / por qué (hallazgos de Fase 17)

- **Cap 5 (Convergencia) y Cap 6 (Accionables) salen inconclusos.** El documento
  `InformeConvergenciaLocal2026RvADAA.pdf` contiene elementos aplicables a cualquier sector,
  pero el filtrado sectorial (ADR-012) lo excluye cuando el informe es de otro sector. Falta
  el concepto de **documento global** (DT-031).
- **Citación rota para PDFs locales:** el texto dice "El InformeConvergenciaLocal2026V3RvADAA.pdf
  destaca que…" en lugar de (Autor, año). El bloque de fuentes inyectado al prompt usa el
  nombre de archivo cuando el documento no tiene metadatos APA (DT-033).
- **Muchos "información no disponible" (Q5):** el corpus por sector es delgado fuera de 3020.
  Alpina/Bancolombia citaron solo 4 refs; Avianca 13 (mejor cobertura web). Más documentos
  por sector (EMIS, Q6) + revisión del umbral de retrieval.
- **Numeración (DT-032):** tras el Cap 4 aparecen subcapítulos `5.x` — bug del renderer o del
  modelo de documento que resta credibilidad inmediata al entregable.

### Tareas

- [x] **T18.1 (DT-031) — Documentos globales cross-sector.** `es_global=True` en
      `PdfIngestor.ingest_batched()` + reserva global `rag_global_reserve=2` en
      `PGVectorStore.search()` + `scripts/ingest_global.py`. 594 chunks ingestados del
      `InformeConvergenciaLocal2026V3RvADAA.pdf`. Addendum ADR-012 Fase 18. ✅
- [x] **T18.2 (DT-033) — Citación APA de PDFs locales.** `format_chunks_with_meta` omite
      rutas locales; chains 04-07 unificadas; `_apa_report` solo emite URLs `http`; fallback
      "Ruta N"; 8 tests de contrato. ✅
- [x] **T18.3 (Q6) — Documentos extra por empresa.** `empresa_id` resuelto en `_run_n0`
      y propagado a N1/N2; reserva empresa `rag_empresa_reserve=2`; selectbox empresa en UI;
      `EmpresaRepository.list_all()`. ✅
- [x] **T18.4 (Q5) — Reducir "información no disponible".** `build_emis_index.py` genera
      `indice_emis.csv` (250 PDFs, 25 sectores); soporte multi-sector via `sectores_adicionales`
      + `jsonb_exists`; tabla de cobertura en `FASE18_HALLAZGOS.md §5`. ✅
- [x] **T18.5 (DT-032) — Fix numeración de subcapítulos.** `chain_05` corregido a 4.1/4.2/4.3;
      `renumber_subheadings()` en `markdown_parser.py` + aplicado en `PilotAssembler`; 6 tests. ✅
- [x] **T18.6 — Corrida E2E de validación.** Alpina S.A.S. sector 3020, corrida completa.
      ResilientChatModel manejó RemoteProtocolError automáticamente (DT-029). Criterios
      de aceptación verificados sobre el .docx generado (ver `FASE18_HALLAZGOS.md §7`). ✅

### Criterios de aceptación

1. Cap 5/6 de un informe de cualquier sector citan `InformeConvergenciaLocal2026` (log/refs).
2. Ninguna cita en el cuerpo usa un nombre de archivo (test de contrato + inspección E2E).
3. Un documento asociado a una empresa aparece priorizado en su informe (test).
4. Tabla de cobertura por sector documentada (qué % de consultas bajo umbral).
5. Numeración de capítulos/subcapítulos correcta en el .docx E2E.
6. Gate verde: ruff 0 + `pytest -m "not slow"`. Tablero §4 y deuda §5 actualizados.

### Riesgos

- El cupo de documentos globales puede desplazar evidencia sectorial → calibrar con el
  harness (patrón reserva ADR-012), no a ciegas.
- Metadatos APA de PDFs existentes pueden estar incompletos → migración/backfill del índice
  (`indice.csv`) antes de exigirlos.
- Prompts más largos (bloque de fuentes con APA) pueden degradar los modelos free → medir.

### PROMPT DE ARRANQUE — Fase 18

(Ver bloque copiable al final de esta sección en el chat de cierre de Fase 17; el prompt
autocontenido vive también en `FASE17_HALLAZGOS.md` §9.)

---

# FASE 19 — Auditoría de Arquitectura, Código y Documentación

**Prioridad:** P0 (el "alto en el camino" — su salida re-prioriza F20–F26) · **Estimación:** ~1–2 días · **Estado:** ✅ Completada (2026-07-24) · **Hallazgos:** `docs/decisions/FASE19_HALLAZGOS.md`

### Objetivo

Tras 18 fases incrementales, verificar de una sola vez que la infraestructura y el código
están alineados con la necesidad del producto y con las reglas del proyecto (CLAUDE.md,
PRIME DIRECTIVE), y que la documentación (ADRs, reglas de negocio, deuda §5) refleja el
comportamiento real del sistema. La salida es un informe de auditoría con acciones
priorizadas que ajusta las fases siguientes de este roadmap.

### Contexto / por qué

- Tres archivos superan la red flag de 300 líneas (CLAUDE.md): `gateway.py` (503 L),
  `presentation/app.py` (487 L), `generate_informe.py` (438 L).
- 15 ADRs + 13 RN acumulados en 18 fases: riesgo de discrepancia docs↔código (red flag
  explícita de CLAUDE.md).
- La deuda §5 tiene 36 entradas; conviene revalidar cuáles siguen vivas (DT-018 lleva 🟡
  desde Fase 9).
- El sistema creció fase a fase; nadie ha revisado el conjunto completo de una vez.

### Tareas

- [x] **T19.1 — Inventario y métricas.** ✅ 3 archivos > 300 L (gateway 503, app 487,
      generate_informe 438); `_run_n3`=157 L. Cobertura `domain/` (gate rápido) = **69%**
      (< 80%; pytest-cov añadido). Sin ciclos reales (38 imports diferidos = smell aceptado).
      SoC: `app.py`→`data/` y chains→`langchain_core` (divergencias, DT-038/042).
- [x] **T19.2 — Red flags de tamaño.** ✅ Plan de partición documentado (FASE19 §4):
      DT-037 (gateway→paquete `llm/`, F22), DT-039 (generate_n3, F22), DT-038 (app.py→views + SoC, F26).
      Ninguna ejecutada (riesgo Medio+); todas agendadas.
- [x] **T19.3 — Coherencia docs↔código.** ✅ 15 ADR + 13 RN con veredicto y evidencia
      `archivo:línea` (FASE19 §5). Divergencias: ADR-004 (LCEL en domain), ADR-009 (regresión
      tamaño), ADR-014 (tabla obsoleta), RN-013 (`search_depth` no implementado).
- [x] **T19.4 — Revalidación de deuda §5.** ✅ DT-018 cerrado; DT-027 retarget→F22;
      DT-030/034/035/036 confirmadas; colisión DT-035 (Fase 18 §9) documentada.
- [x] **T19.5 — Higiene de repo.** ✅ `check-ruff` cableado; hook models con puntos ciegos
      (DT-040); `output/`+raíz gitignored; `docs/prompts/` 4 de 17 (alcance F20).
- [x] **T19.6 — Informe y re-priorización.** ✅ `FASE19_HALLAZGOS.md` + tablero §4, deuda §5,
      changelog §8 actualizados; F20–F26 re-priorizadas (FASE19 §10).

### Criterios de aceptación

1. Tabla de violaciones SoC/wrappers con evidencia `archivo:línea` (o constancia de cero).
2. Cada ADR y RN con veredicto documentado (fiel / divergente / obsoleto).
3. Plan de partición para los 3 archivos >300 L con fase destino asignada.
4. Deuda §5 revalidada; tablero §4 y changelog §8 actualizados.
5. Gate verde: ruff 0 + `pytest -m "not slow"` (≥305 fast tests).

### PROMPT DE ARRANQUE — Fase 19

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase19-auditoria (crear desde develop).
Esta fase es de AUDITORÍA: lees y mides mucho, cambias poco (solo higiene de bajo riesgo).

ESTADO DE ENTRADA (Fase 18 cerrada, 305 tests fast, ruff 0):
- 18 fases cerradas; roadmap v3.0 re-secuenciado tras el "alto en el camino" (2026-07-24).
- Señales ya detectadas: gateway.py 503 L, app.py 487 L, generate_informe.py 438 L
  (red flag 300 L); docs/prompts/ tiene 4 de 13 source_prompts; DT-018 en 🟡 desde Fase 9.

OBJETIVOS (T19.1–T19.6):
- Inventario y métricas: tamaños, cobertura domain/, grafo de imports, violaciones SoC.
- Plan de partición de los 3 archivos >300 L (ejecutar solo lo de bajo riesgo).
- Coherencia docs↔código: veredicto por cada ADR-001..015 y RN-001..013 con archivo:línea.
- Revalidar deuda §5 (estados reales).
- Higiene de repo (hooks, output/, docs/prompts incompleto).
- FASE19_HALLAZGOS.md (hallazgo → severidad → acción → fase destino) + actualizar F20–F26.

REGLAS DURAS (CLAUDE.md TIER 1): no hardcodear modelos, no secretos, no tocar BD compartida
fuera del esquema, Ollama en host, wrappers en infrastructure/. Los ADR NO se reescriben.
NO hagas refactors grandes en esta fase: se proponen y se agendan.

MÉTODO: Plan Mode antes de tocar archivos. Gate tras cada cambio: ruff 0 + pytest verde.

LECTURAS OBLIGATORIAS al arrancar:
- CLAUDE.md + docs/architecture/PRIME DIRECTIVE.md + docs/architecture/ARQUITECTURA.md
- docs/architecture/ROADMAP_FASE9+.md §FASE19 (esta sección) + §5 deuda técnica
- docs/architecture/ADR-001..ADR-015 (para T19.3)
- docs/business-rules/REGLAS_NEGOCIO.md
- docs/decisions/FASE17_HALLAZGOS.md y FASE18_HALLAZGOS.md (estado reciente)

CIERRE: documenta FASE19_HALLAZGOS.md, actualiza tablero §4 / deuda §5 / changelog §8 y las
fases F20–F26 con lo encontrado. Propón el PROMPT DE ARRANQUE ajustado de la FASE 20.
Confirma el mensaje de commit conmigo; mergea a develop con --no-ff.
```

---

# FASE 20 — Gap Analysis de Calidad vs Informe Patrón (Noel)

**Prioridad:** P0 · **Estimación:** ~1–2 días · **Estado:** ⬜ Pendiente

### Objetivo

Convertir "el informe generado todavía no se parece al que quiero" en una **rúbrica
medible**: comparar sistemáticamente los informes generados contra el patrón manual
`InformeSectoryCompetitivoNoel.docx` (raíz del proyecto) y contra los `source_prompts/`
originales, y derivar brechas concretas que alimentan F21 (contenido), F22 (coherencia),
F23 (fuentes) y F26 (estilo).

### Contexto / por qué

- El patrón Noel tiene estructura más rica que la salida actual: Cap 2 con 5 subcaps (2.1
  líderes … 2.5 análisis de brechas), Cap 3 con tendencias M.E.C.E. y casos de éxito, Cap 4
  con 5 subcaps de movimientos del ecosistema (inversiones, integraciones, M&A, joint
  ventures, alianzas), Cap 5 por áreas estratégicas del distrito, **Metodología + aviso de
  uso de IA**, y 10 tablas.
- Los prompts operativos viven en las chains; `docs/prompts/` solo tiene 4 md (prompts
  01, 02, 03, 05) frente a **17 archivos** en `source_prompts/` (los 13 prompts numerados
  1–13 + `0. Ecuaciones de búsqueda` + 3 variantes de `4. Mercado`) → no hay verificación
  de fidelidad chain↔prompt original. *(Conteo confirmado en Fase 19; el roadmap v3.0 decía
  "4 de 13" — la cifra correcta es 4 de 17 archivos.)*
- En `output/` hay ≥6 informes generados para evaluar sin nuevas corridas. Rutas verificadas:
  `output/alpina_informe.docx`, `output/avianca_informe.docx`, `output/bancolombia_informe.docx`,
  `output/comfama_informe.docx`, `output/nestle_colombia_informe.docx`, `output/noel_sas_informe.docx`.

### Tareas

- [ ] **T20.1 — Rúbrica de calidad por capítulo.** Derivada del patrón Noel: estructura
      (subcaps esperados), profundidad (datos concretos vs generalidades), evidencia
      (nº citas por sección), elementos visuales (tablas/figuras), tono. Formato evaluable
      de forma repetible (manual y/o LLM-judge). Versionarla en `docs/business-rules/` o
      `docs/eval/`.
- [ ] **T20.2 — Evaluación de ≥3 informes generados** (Alpina, Avianca, Bancolombia)
      contra la rúbrica. Matriz de brechas por capítulo con severidad.
- [ ] **T20.3 — Auditoría de fidelidad de prompts.** Comparar cada chain contra su
      source_prompt (17 docx: 13 numerados + Ecuaciones + 3 variantes Mercado): qué
      instrucciones se perdieron en la migración, qué divergencias son deliberadas.
      Completar `docs/prompts/` como espejo versionado en markdown de los prompts numerados.
- [ ] **T20.4 — Secciones faltantes del patrón.** Verificar en el ensamblado actual:
      ¿existen Metodología + aviso de IA? ¿subcaps 2.x/4.x completos? Registrar faltantes
      como tareas en F21/F26.
- [ ] **T20.5 — Cierre.** `FASE20_HALLAZGOS.md` (rúbrica + matriz de brechas + fase destino
      de cada brecha) y actualización de F21/F22/F23/F26 en este roadmap.

### Criterios de aceptación

1. Rúbrica versionada y aplicable de forma repetible.
2. Matriz de brechas de ≥3 informes con severidad y fase destino para cada brecha.
3. `docs/prompts/` contiene los 13 prompts en markdown con nota de divergencias vs chains.
4. Toda brecha detectada quedó asignada a una fase (ninguna huérfana).
5. Gate verde: ruff 0 + `pytest -m "not slow"`.

### PROMPT DE ARRANQUE — Fase 20

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase20-gap-analysis (crear desde develop).
Fase de ANÁLISIS: produces rúbrica + matriz de brechas + docs/prompts completo; el código
de aplicación casi no se toca.

ESTADO DE ENTRADA (Fase 19 cerrada — leer FASE19_HALLAZGOS.md):
- Auditoría de arquitectura/código/docs hecha; deuda §5 revalidada.

OBJETIVOS (T20.1–T20.5): rúbrica por capítulo derivada del patrón Noel; evaluación de ≥3
informes de output/; fidelidad chains ↔ source_prompts (17 docx) + completar docs/prompts/;
secciones faltantes del patrón (Metodología, aviso IA, subcaps 2.x/4.x); hallazgos +
actualización de F21+.

HERRAMIENTA: para leer los .docx usa python-docx (ya en el entorno, vía uv run python).

REGLAS DURAS: no hardcodear modelos; los prompts de las chains NO se modifican en esta fase
(solo se documentan divergencias — los cambios se agendan en F21/F26).

CONTEXTO DE FASE 19 (leer FASE19_HALLAZGOS.md primero): auditoría cerrada. NO abrir refactors
agendados en F22/F26 (DT-037..042); F20 es solo análisis. La brecha docs/prompts (4 de 17
archivos) y las secciones faltantes del patrón son el foco. Gate de entrada: ruff 0 + 305 fast.

LECTURAS OBLIGATORIAS al arrancar:
- docs/architecture/ROADMAP_FASE9+.md §FASE20 (esta sección)
- docs/decisions/FASE19_HALLAZGOS.md
- InformeSectoryCompetitivoNoel.docx (patrón, raíz) — extraer estructura y tablas
- output/alpina_informe.docx, output/avianca_informe.docx, output/bancolombia_informe.docx
- source_prompts/*.docx (17 archivos: 13 numerados + Ecuaciones + 3 variantes Mercado)
  y docs/prompts/*.md (4 migrados: 01, 02, 03, 05)
- src/ic/domain/chains/ (prompts operativos actuales)
- docs/business-rules/REGLAS_NEGOCIO.md (RN-001 datos ausentes, RN-002 trazabilidad)

CIERRE: FASE20_HALLAZGOS.md + tablero §4 / changelog §8 + actualizar F21/F22/F23/F26 con
las brechas. Propón el PROMPT DE ARRANQUE ajustado de la FASE 21.
Confirma el mensaje de commit conmigo; mergea a develop con --no-ff.
```

---

# FASE 21 — Calidad de Contenido — Sprint A (ex-F19 en v2.5)

**Prioridad:** P0 · **Estimación:** ~1 día (Sprint A) + ~2 días (Sprint A' contenido) · **Estado:** ⬜ Pendiente
**Deuda:** DT-035 (competidores Cap 2 sin datos), DT-036 (casos locales off-topic Cap 3),
**DT-043** (sesgo sectorial), **DT-044** (2.3 Mercado), **DT-045** (Metodología+Aviso IA),
**DT-046** (rediseño Cap 4) — estas cuatro añadidas por Fase 20

### Objetivo

Corregir dos deficiencias de contenido identificadas en la comparativa Alpina (mañana vs Fase 18):
Cap 2 devuelve tablas vacías de competidores porque el web search usa modo `basic` con queries
genéricas de sector; Cap 3 cita casos locales off-topic (KPO, turismo) traídos por los 594 chunks
globales sin filtro sectorial en el prompt. Además, documentar las ecuaciones de búsqueda EMIS.

### Contexto / causa raíz

- **DT-035 (Cap 2):** `generate_benchmarking.py` lanza queries del tipo
  `"{sector_gics} competidores líderes globales"` → Tavily devuelve overviews de sector, no perfiles
  de empresas individuales. Con `search_depth="basic"` solo se reciben snippets de ~200 chars.
  El LLM ve fichas vacías y aplica correctamente la política "Dato no disponible". La versión de
  la mañana usaba datos de entrenamiento del LLM (prohibido por política de no-alucinación).
- **DT-036 (Cap 3):** Los 594 chunks globales del InformeConvergenciaLocal2026 son cross-sector:
  contienen casos Medellín/Antioquia de KPO, turismo inteligente, etc. Al recuperarse para la
  query de "casos locales" de una empresa de alimentos, el LLM los usa porque no hay constraint
  sectorial en el prompt de casos locales.
- **Ecuaciones de búsqueda:** `source_prompts/0. Ecuaciones de búsqueda.docx` contiene las
  instrucciones para el analista que construye el corpus EMIS; no están documentadas como runbook.

### Tareas

- [ ] **T21.1 (DT-035) — `WebConnector.search()` con `search_depth` parametrizable.**
      Añadir `search_depth: str = "basic"` a `WebConnector.search()` y `_search_tavily()`.
      Actualizar `generate_benchmarking.py`: pasar `search_depth="advanced"` + queries más
      específicas (p.ej. `"{competidor} cuota mercado Colombia LatAm 2025"`). Los queries
      genéricos de sector siguen siendo `"basic"`; el `advanced` se usa solo donde se necesitan
      perfiles detallados.
      Wrapper en `infrastructure/sources/web_connector.py` — no tocar `domain/`.
- [ ] **T21.2 (DT-036) — Constraint sectorial en Cap 3 casos locales.**
      En `chain_04_tendencias.py` (sistema/usuario prompt de casos locales): añadir instrucción
      explícita "Los casos locales deben pertenecer al sector GICS {sector_gics} de la empresa
      analizada. Si no hay casos locales del mismo sector, indicar 'Dato no disponible en fuentes
      consultadas.' — NO usar casos de otros sectores aunque sean de Medellín o Colombia."
      En `generate_tendencias.py`: añadir query web dedicada a casos locales sectoriales
      (ej. `"{sector_gics} caso éxito empresa Colombia Medellín Antioquia"`).
- [ ] **T21.3 — `docs/runbooks/BUSQUEDA_FUENTES.md`.**
      Extraer y documentar las ecuaciones de búsqueda del `source_prompts/0. Ecuaciones de
      búsqueda.docx` como guía de analista para enriquecer el corpus EMIS. Incluir: motores
      (EMIS, Scopus, Web of Science), operadores booleanos por sector GICS, criterios de
      selección de PDFs, proceso de ingesta (`ingest_batch.py` con `indice_emis.csv`).
- [ ] **T21.4 — E2E de validación Sprint A.**
      Corrida con Alpina S.A.S. (sector 3020): verificar que Cap 2 tiene al menos 1 tabla de
      competidor con datos reales (no "Dato no disponible"); Cap 3 no cita KPO ni turismo.

#### Sprint A' — Acercamiento al patrón Noel (añadido en Fase 20)

- [ ] **T21.5 (DT-043) — Des-sesgar los prompts por sector.** Parametrizar el rol y el
      vocabulario sectorial de `chain_03`/`chain_04` (y las ecuaciones de búsqueda) por el
      `{sector_gics}` en lugar de "bienes de consumo/FoodTech/agroindustrial". El rol pasa a ser
      genérico ("consultor senior en el sector {sector_gics}"). Verificar con avianca (2030) y
      bancolombia (4010) que el Cap 2 deja de salir food-céntrico. Sin hardcodear modelos.
- [ ] **T21.6 (DT-044) — Implementar Cap 2.3 Mercado.** Nueva chain (`chain_03b_mercado` o
      sección en `chain_03`) que genere 2.3 Mercado a partir de los `source_prompts 4/5`
      (tamaño de mercado, segmentos, tabla de mercado por región tipo Noel T10). Ensamblar entre
      2.2 y 2.4 en `assembler.py`. Documentar en `docs/prompts/`.
- [ ] **T21.7 (DT-045) — Metodología + Aviso de uso de IA.** Añadir en `assembler.py` una sección
      "Metodología" (fuentes consultadas, proceso, alcance) y elevar el disclaimer a una sección
      formal "Aviso sobre el uso de inteligencia artificial", como en el patrón Noel.
- [ ] **T21.8 (DT-046) — Rediseñar Cap 4 al patrón.** Reescribir `chain_05_ecosistema` para
      producir 4.1 Inversiones / 4.2 Integraciones verticales / 4.3 M&A / 4.4 Joint ventures /
      4.5 Alianzas, con 3 eventos por subcap (Título + ejecución + capacidad estratégica adquirida
      + vulnerabilidad mitigada). Actualizar `prompt-05-ecosistema.md`. Plan Mode obligatorio.

> **Nota de alcance (Fase 20):** T21.5–T21.8 elevan F21 de "2 arreglos" a "Sprint de contenido".
> Si el tamaño lo justifica, dividir en F21 (T21.1–T21.4, arreglos rápidos) y F21b (T21.5–T21.8,
> contenido) al planificar. Detalle en `FASE20_HALLAZGOS.md §5–§7`.

### Criterios de aceptación

1. `WebConnector.search()` acepta `search_depth` sin cambio de firma pública (default `"basic"`).
2. Cap 2 de la corrida E2E tiene ≥1 ficha de competidor con datos (no solo "no disponible").
3. Cap 3 de la corrida E2E no menciona sectores ajenos a la empresa analizada en casos locales.
4. (T21.5–T21.8) El informe de una empresa **no alimentaria** alcanza ≥ 11/15 en Cap 2 y Cap 4
   según `docs/eval/RUBRICA_CALIDAD.md`; el ensamblado incluye 2.3 Mercado + Metodología + Aviso IA.
5. Gate verde: ruff 0 + `pytest -m "not slow"` (≥305 fast tests).

### PROMPT DE ARRANQUE — Fase 21

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase21-calidad-contenido (crear desde develop).

ESTADO DE ENTRADA (Fases 19–20 cerradas: auditoría y gap analysis — leer
FASE19_HALLAZGOS.md y FASE20_HALLAZGOS.md; base Fase 18: 305 tests fast, ruff 0):
- 594 chunks globales ingestados (InformeConvergenciaLocal2026).
- DT-031/032/033 cerrados. Reservas empresa/sector/global operativas.
- Deuda nueva: DT-035 (Cap 2 competidores vacíos), DT-036 (Cap 3 casos off-topic).

CONTEXTO CRÍTICO — comparativa Alpina (identificado en sesión 2026-07-23):
- La versión de la mañana tenía datos de competidores ricos → procedían del conocimiento
  de entrenamiento del LLM (PROHIBIDO: política de no-alucinación).
- La versión Fase 18 tiene tablas vacías → CORRECTO comportamiento, pero el RAG no
  tiene perfiles de competidores reales porque Tavily basic + queries genéricas no los capturan.
- Cap 3 version Fase 18 cita "KPO en Medellín" y "Turismo Inteligente" para Alpina (alimentos)
  → chunks globales cross-sector recuperados sin constraint de sector GICS en el prompt.

OBJETIVOS DE FASE 21 (Sprint A — arreglos rápidos):
- T21.1 (DT-035): WebConnector.search() con search_depth="advanced" para queries de competidores.
- T21.2 (DT-036): constraint sectorial en prompt de casos locales Cap 3.
- T21.3: docs/runbooks/BUSQUEDA_FUENTES.md (ecuaciones de búsqueda EMIS → analista).
- T21.4: E2E Alpina S.A.S. validando Cap 2 y Cap 3.

OBJETIVOS DE FASE 21 (Sprint A' — acercamiento al patrón Noel, añadido por Fase 20):
- T21.5 (DT-043): des-sesgar prompts por {sector_gics} (quitar "FoodTech/agroindustrial").
- T21.6 (DT-044): implementar Cap 2.3 Mercado (source_prompts 4/5) + tabla mercado por región.
- T21.7 (DT-045): sección Metodología + Aviso de uso de IA en assembler.py.
- T21.8 (DT-046): rediseñar Cap 4 a 4.1–4.5 (Inversiones/Integraciones/M&A/JV/Alianzas con eventos).
- Validar con una empresa NO alimentaria (avianca 2030 o bancolombia 4010) contra
  docs/eval/RUBRICA_CALIDAD.md (Cap 2 y Cap 4 ≥ 11/15).
- Rúbrica y matriz de brechas de partida: docs/eval/RUBRICA_CALIDAD.md + FASE20_HALLAZGOS.md §3.

REGLAS DURAS (CLAUDE.md TIER 1):
- No hardcodear nombres de modelo (van en .env).
- No credenciales en código.
- domain/ no importa httpx/SQLAlchemy/Streamlit directamente.
- No re-litigar ADR-012, ADR-013, ADR-014, ADR-015.
- NUNCA usar datos de entrenamiento del LLM como fuente de afirmaciones en el informe.

MÉTODO: Plan Mode antes de tocar archivos. Un commit atómico por tarea.
Gate tras cada tarea: ruff 0 + pytest -m "not slow" verde.

LECTURAS OBLIGATORIAS al arrancar:
- docs/architecture/ROADMAP_FASE9+.md §FASE21 (esta sección)
- docs/decisions/FASE18_HALLAZGOS.md (estado y comparativa)
- docs/decisions/FASE19_HALLAZGOS.md y FASE20_HALLAZGOS.md (auditoría + rúbrica de calidad)
- docs/architecture/ADR-015-hitl.md (arquitectura HITL — contexto futuro)
- src/ic/infrastructure/sources/web_connector.py (Tavily actual)
- src/ic/domain/use_cases/generate_benchmarking.py (queries actuales)
- src/ic/domain/chains/chain_04_tendencias.py (prompt casos locales)
- src/ic/domain/use_cases/generate_tendencias.py (queries web tendencias)
- source_prompts/0. Ecuaciones de búsqueda.docx (guía analista EMIS)
```

---

# FASE 22 — Evidencia, Retrieval y Coherencia (re-scoped 2026-07-24)

**Prioridad:** P0 · **Estimación:** ~3–4 días (2 sprints) · **Estado:** ⬜ Pendiente
**Deuda:** **DT-049 (breadth/diversidad de retrieval), DT-052 (citación no sigue al corpus)** —
Sprint A prioritario; DT-027 (radar), DT-030 (checkpoint), DT-047 (áreas Cap 5), DT-048 (LLM-judge),
Q1 (coherencia) — Sprint B.

> **Re-scoping (2026-07-24):** la prueba A/B post-ingesta EMIS (`FASE21_HALLAZGOS.md §5.2`) mostró
> que enriquecer el corpus **mejora mucho el contenido pero no la citación** (referencias planas en
> 3, fuentes EMIS no citadas, cita huérfana). El cuello de botella ahora es **retrieval + citación**,
> no el corpus. Por eso F22 lidera con **Sprint A — Evidencia y Retrieval** (DT-049/052), que corre
> en **paralelo a la indexación EMIS de fondo** (código puro + harness, sin Ollama/E2E). El bloque
> original de coherencia/robustez pasa a **Sprint B**.

---

## SPRINT A — Evidencia y Retrieval (prioritario, hoy; paralelo a la indexación EMIS)

### Objetivo Sprint A

Que el corpus enriquecido se traduzca en **fuentes diversas y trazables** en el informe. Hoy, con
286 chunks / 14 docs en el sector 3020, el retrieval por capítulo concentra los chunks en ~2-3
documentos (el compilado) → solo 3 referencias, y las fuentes EMIS usadas para el contenido **no se
citan** (riesgo RN-001: no se puede verificar el anclaje). Es problema de retrieval + citación, no
de disponibilidad.

### Contexto / causa raíz (verificado en código 2026-07-24)

- `PGVectorStore.search()` usa `rag_top_k` + `rag_max_chunks_per_doc=4` + reservas
  (sector 3, global 2, empresa 2) + MMR. Con top_k≈10 y cap 4/doc, el resultado abarca ~2-3
  documentos → poca diversidad de fuentes. Palancas: `rag_top_k`, `rag_max_chunks_per_doc`,
  reservas, y/o garantía de "mínimo N documentos distintos" en el ensamblado del retrieval.
- `build_references_section(todos_chunks)` (apa_formatter) es **fiel**: emite 1 ref por documento
  presente en `chunks_usados`. Si solo hay 3 refs es porque `chunks_usados` solo tiene 3 docs.
- `find_orphan_citations()` ya detecta huérfanas; en el A/B apareció `(Alpina, Carvajal, 2019)`.

### Tareas Sprint A

- [x] **T22.A1 (DT-049) — Diversidad de retrieval.** ✅ Código commiteado (`4c342c4`): MMR 0.7, cap 2/doc, piso `rag_min_distinct_docs=5`, `_enforce_doc_diversity`. Medición con harness pendiente (BD estable). Con el harness `scripts/eval_retrieval.py`
      (Fase 14, T14.1), medir nº de documentos distintos por consulta ANTES y ajustar palancas
      (`rag_max_chunks_per_doc`, `rag_top_k`, reservas) y/o añadir una garantía de "≥ N docs
      distintos" en `PGVectorStore.search()`. Objetivo: subir la diversidad sin degradar precisión
      (usar el gold set del harness). No re-litigar ADR-012/014; tuning dentro de sus parámetros.
      Tests unitarios con mocks del repo.
- [x] **T22.A2 (DT-052) — La citación sigue al corpus + huérfanas.** ✅ Código commiteado (`e364a52`): `strip_orphan_citations` (RN-001), saneo por capítulo, prompt chain_03 a una fuente por cita. Validación E2E pendiente. Verificar que los chunks
      efectivamente usados (`chunks_usados`) lleguen a `build_references_section` y aparezcan en
      Referencias; endurecer el prompt para que el LLM cite (Autor, año) de las fuentes del
      contexto; y tratar huérfanas (mapear a la referencia real o suprimir la cita). Preservar
      RN-001 (sin inventar atribuciones). Tests de contrato (chunks → refs; huérfanas = 0).
- [x] **T22.A3 — Validación E2E sobre sectores COMPLETOS (≥2) + anti-mezcla.** ✅ **2026-07-29.**
      Paso 0 (DT-053 medición multi-sector) commiteado `04604cf`; anti-mezcla instrumentado
      `aeb4482` (`coherence.sector_histogram`, +3 tests). Harness A/B: precisión 1.0 y
      contaminación 0.0 sin regresión, `avg_correct` 3.2→3.76 (snapshots `fase22_baseline.json` /
      `fase22_nomm.json`). E2E 2 sectores: **Alpina 3020** (8 refs, 0 huérfanas, Cap5 4 áreas,
      Cap6 cruza Cap2/3/5, anti-mezcla doc 1/7/0) y **Sofasa 2510** (14 refs, 0 huérfanas, Cap5
      4 áreas, Cap6 cruza Tendencias/Convergencia, **anti-mezcla chunks 17/33/ajeno=0**). Los 6
      criterios demostrados (`FASE22_HALLAZGOS.md §5/§6`). Deuda nueva DT-054 (EMIS individuales
      sub-citados) y DT-055 (fuga de intro Cap6 en Sofasa) → F23/Sprint B. Detalle histórico ↓
      <details><summary>plan original T22.A3</summary>
      0. **Mini-ajuste de medición multi-sector (DT-053), previo al harness/E2E.** Que la
         medición trate un chunk como on-sector si el sector pedido está en `metadatos["sectores"]`
         O `== metadatos["sector_gics"]`:
         - `src/ic/domain/eval/retrieval_metrics.py`: `RetrievedChunk` gana `sectores: list[str]`
           (o campo equivalente); `context_precision`/`cross_sector_contamination`/`sectoral_hit`
           consideran pertenencia al array, no solo igualdad con el primario.
         - `scripts/eval_retrieval.py::_to_retrieved`: leer `metadatos.get("sectores")` además de
           `sector_gics`.
         - El chequeo anti-mezcla del paso 3 usa el mismo criterio (array o primario).
         Tests mockeados. Hoy la columna `sectores_adicionales` del CSV está vacía → el resultado
         no cambia, pero deja la medición lista para cuando se pueble (curación F23). Cambio de
         código pequeño, testeable sin Ollama; se puede adelantar antes de que termine la ingesta.
      1. **Identificar sectores completos**: comparar los documentos ingestados por sector en BD
         contra el nº de filas por sector en `indice_emis.csv`. Sector completo = todos sus docs
         presentes. Helper SQL:
         ```sql
         SELECT metadatos->>'sector_gics' AS s, count(DISTINCT metadatos->>'titulo') AS docs
         FROM informes_ic.embeddings_vectoriales
         WHERE metadatos ? 'sector_gics' GROUP BY 1 ORDER BY 1;
         ```
         y comparar con `cut -d, -f2 indice_emis.csv | sort | uniq -c`. Por orden del CSV, los
         primeros completos serán **3020 (Alimentos)** y **2510 (Automóviles y Componentes)**.
      2. **Correr una empresa por sector, en ≥2 sectores DISTINTOS y completos** (p. ej. 3020 →
         Alpina S.A.S. o Grupo Nutresa; 2510 → una empresa automotriz colombiana, p. ej. Sofasa
         S.A. / Colmotores — confirmar antes que su GICS resuelto por `chain_02` cae en el sector
         completo elegido; si no, elegir otra empresa/sector completo).
      3. **Verificar por informe**:
         - referencias 3 → **≥ 8 fuentes distintas** citadas, **0 huérfanas**, fuentes EMIS del
           sector presentes en Referencias;
         - **NO mezcla de sectores**: los chunks **sectoriales** citados pertenecen al `sector_gics`
           de la empresa. Los documentos **globales** (`es_global=true`, InformeConvergenciaLocal)
           SÍ están permitidos por diseño (ADR-012/018) → **exclúyelos** del chequeo anti-mezcla.
           Comprobar el `sector_gics` de los `chunks_usados` citados: no debe aparecer un sector
           específico ajeno (p. ej. el informe de Alpina no cita fuentes marcadas 2510/4010).
      > **Multi-sector (DT-053):** un doc es on-sector si el sector pedido está en su array
      > `metadatos["sectores"]`, no solo si `== sector_gics`. Hoy la columna `sectores_adicionales`
      > del CSV está vacía (ningún doc multi-etiquetado), por lo que el chequeo por `sector_gics`
      > basta; en cuanto se pueble, el anti-mezcla y el harness deben honrar `sectores` para no
      > marcar contaminación falsa.
      </details>

### Criterios de aceptación Sprint A ✅ (todos demostrados 2026-07-29)

1. El retrieval de una consulta sectorial devuelve chunks de **≥ 5 documentos distintos** cuando
   existen (medido con el harness).
2. Referencias del informe: de 3 → **≥ 8 fuentes distintas** en cada corrida de validación.
3. **0 citas huérfanas** en el `.docx` de validación (o todas mapeadas a una referencia real).
4. **Anti-mezcla**: en ≥2 sectores completos, los chunks sectoriales citados son del sector de la
   empresa (globales exentos); ningún sector específico ajeno aparece citado.
5. Sin regresión de precisión del retrieval (gold set del harness) ni de RN-001.
6. Gate verde: ruff 0 + `pytest -m "not slow"` (≥322 fast tests).

---

## SPRINT B — Coherencia y Robustez (después del Sprint A)

### Objetivo Sprint B

Mejorar la coherencia interna del informe generado y la robustez del pipeline ante fallos tardíos.
Las corridas de Fase 17/18 evidencian tres problemas que requieren código, no solo corpus:

- **Q1 — Coherencia post-generación**: Cap 6 (Accionables) no referencia explícitamente
  hallazgos de Caps 2/3/4. El Resumen Ejecutivo es independiente de la narrativa de los caps.
- **DT-027 — Cadena radar dedicada**: el bloque `radar_json` falla el 50% de las corridas
  (N=2 observables de 5; umbral 80% no alcanzado). Un LLM separado en temperatura 0 es la
  solución aprobada en Fase 17.
- **DT-030 — Checkpoint antes de barreras de sincronización**: un fallo en Cap 6 o en el
  Resumen Ejecutivo descarta ~13 min de trabajo (Caps 1–5). Persistir estado en BD y permitir
  reanudar.

### Contexto / por qué (hallazgos de Fase 17/18)

- **Q1:** La estructura DAG del pipeline (Cap 6 consume informe completo) es correcta, pero
  el prompt del Cap 6 no recibe los textos de Caps 2/3/4 como contexto — solo recibe el
  retrieval. Agregar un "contexto de caps previos" (resumen) al prompt de Cap 6 y N3.
- **DT-027:** El LLM free emite el JSON del radar embedido en texto narrativo; el regex
  `_extract_radar()` lo captura solo cuando el formato es limpio. Una cadena dedicada con
  prompt estricto y temperatura 0 resuelve el 50% restante.
- **DT-030:** El CLAUDE.md Tier 3 exige persistir estado antes de las barreras Cap 6 / N3.
  Un fallo de red en el Resumen Ejecutivo hoy descarta todo. Implementar snapshot a BD de
  los caps N0/N1/N2 + función de reanudación (`--resume <session_id>`).

### Tareas Sprint B

- [x] **T22.1 (Q1) — Contexto de caps previos para Cap 6 y N3.** ✅ Adelantado (`6e6e220`):
      `domain/coherence.py::build_caps_summary`; Cap 6 (`chain_07`/`generate_accionables`) recibe
      `hallazgos_caps_previos` (resumen de Caps 2/3/4/5) + instrucción de referenciar un hallazgo
      concreto; `_run_n3` añade Cap 2.3 Mercado al contexto del Resumen (ya recibía los demás).
      Pendiente: verificación E2E (Cap 6 cita hallazgo de Cap 2/3 en el `.docx`) tras indexación.
- [ ] **T22.2 (DT-027) — Cadena radar dedicada.** Cadena LCEL separada para extraer los 5
      scores del radar: LLM con temperatura 0, prompt estructurado, sin texto narrativo.
      Wrapper en `generate_benchmarking.py`; fallback al placeholder garantizado. Test: 5
      corridas con el mismo texto → 5/5 JSON parseables.
      **NOTA (2026-07-24):** con el corpus 3020 enriquecido, la corrida A/B de Alpina emitió el
      radar con **datos reales** (6 competidores, 5 dims), no placeholder. Antes de construir la
      cadena dedicada, **re-medir el hit-rate** (N=5) sobre corpus enriquecido: puede que el
      problema se atenúe y DT-027 baje de prioridad o se cierre con solo el endurecimiento del prompt.
- [ ] **T22.3 (DT-030) — Checkpoint de caps N0/N1/N2 a BD.** Persistir el texto de cada
      capítulo completado (columna JSONB en `historial_informes` o tabla `caps_cache`).
      Flag `--resume <session_id>` en `run_pilot.py` que recarga los caps cacheados y salta
      su generación. Gate: si Cap 6 falla, relanzar solo Cap 6 sin perder Caps 1–5.
- [ ] **T22.4 (visión producto + DT-049) — Enriquecimiento dirigido post-N1 y breadth de
      retrieval.** Tras completar los caps N1, extraer las entidades clave halladas
      (competidores del Cap 2, tendencias del Cap 3) y lanzar búsquedas dirigidas de contraste
      cuyo resultado alimente el contexto de Cap 5/6 y el pase de coherencia. Diseñar en Plan
      Mode: alcance mínimo viable, sin romper la paralelización de N1 (el pase corre DESPUÉS
      de la barrera N1, antes de N2).
      **Incluir el diagnóstico DT-049** (E2E de cierre F21): investigar por qué de 122 chunks
      web ingestados solo 1 se cita (Alpina) — ¿ranking domina la reserva sectorial?, ¿las
      queries web no traen perfiles de competidor?, ¿la purga ADR-013 "solo citado" es
      demasiado agresiva con corpus concentrado? Medir nº de fuentes distintas citadas antes/
      después. Objetivo: subir la diversidad de fuentes citadas sin violar RN-001. La parte de
      **corpus** (documentos diversos por sector) es F23.
- [ ] **T22.5 — E2E de validación.** 2 corridas: una exitosa (verifica coherencia y radar),
      una con fallo simulado en Cap 6 → reanudación sin regenerar caps previos.
- [x] **T22.6 (DT-047) — Fijar 4 áreas en Cap 5.** ✅ Adelantado (`71d67d2`): prompt de síntesis
      `chain_06_convergencia` endurecido a EXACTAMENTE 4 áreas + `coherence.py::enforce_cap5_areas`
      elimina subsecciones `## 5.N` con N>4 (defensa en profundidad, RN-safe), aplicado en ambas
      rutas de `generate_convergencia`. +4 tests de estructura. Verificación E2E tras indexación.
- [ ] **T22.7 (DT-048) — LLM-judge de la rúbrica.** Cadena que aplica
      `docs/eval/RUBRICA_CALIDAD.md` (temperatura 0) sobre el `.docx` generado y emite el score
      por capítulo. Sirve como métrica de regresión de calidad entre fases. Fallback si no hay LLM.

### Criterios de aceptación

1. Cap 6 cita al menos un hallazgo específico de Cap 2 o Cap 3 (inspección manual del .docx).
2. Radar: 5/5 corridas del mismo texto emiten JSON parseable (test automatizable).
3. `--resume <session_id>` restaura caps 1–5 y regenera solo el cap fallido (<2 min vs ~13 min).
4. Gate verde: ruff 0 + `pytest -m "not slow"` (≥305 fast tests, ajustar según lo añadido en F21).

### PROMPT DE ARRANQUE — Fase 22

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase22-evidencia-retrieval (crear desde develop).

FASE 22 — SPRINT A: Evidencia y Retrieval (DT-049 + DT-052). Corre EN PARALELO a la
indexación EMIS de fondo. El Sprint B (coherencia/robustez) va después.

PASO 0 — Lanzar la indexación EMIS de fondo (una sola vez, ANTES de empezar a codear):
  nohup uv run python scripts/ingest_batch.py \
    --dir documentos_sectoriales \
    --csv documentos_sectoriales/FuentesEMIS/indice_emis.csv > /tmp/ingest_emis_full.log 2>&1 &
  (250 docs, ~2–4 h; idempotente — el sector 3020 ya está y se salta. El fix de bytes NUL
   DT-051 ya está mergeado, así que los Euromonitor ahora entran.)
  IMPORTANTE: mientras la indexación corre, NO ejecutes E2E (`run_pilot.py`) ni tests `@slow`:
  compiten por Ollama/VRAM y la BD está cambiando. El trabajo de Sprint A es código + ruff +
  `pytest -m "not slow"` (mockeado, sin Ollama) → no hay conflicto. La validación E2E (T22.A3)
  se hace AL TERMINAR la indexación.

PASO 1 — Ramas: git checkout develop && git checkout -b feature/fase22-evidencia-retrieval
PASO 2 — Gate de entrada: uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q

ESTADO DE ENTRADA (Fase 21 cerrada + post: merge 307ec4b; 322 tests fast, ruff 0):
- F21 completa (6 DT de contenido). DT-051 cerrado (fix bytes NUL en ingesta de PDF).
- PRUEBA A/B (FASE21_HALLAZGOS §5.2): tras ingestar el sector 3020 (44→286 chunks / 14 docs),
  el contenido mejoró MUCHO (Cap 2.1 ausente → 14 fichas de competidor en tabla; radar
  placeholder → datos reales; 1→16 tablas) PERO la citación NO: referencias siguen en 3, las
  14 fuentes EMIS no se citan, 0 chunks web citados, 1 cita huérfana. => cuello de botella =
  retrieval + citación, NO corpus.
- CAUSA RAÍZ VERIFICADA EN CÓDIGO:
  * `PGVectorStore.search()` (src/ic/infrastructure/retrieval/pgvector_store.py): rag_top_k +
    rag_max_chunks_per_doc=4 + reservas (sector 3, global 2, empresa 2) + MMR → los chunks
    abarcan solo ~2-3 documentos aunque existan 14.
  * `build_references_section()` (apa_formatter) es FIEL: 1 ref por doc en chunks_usados. Solo
    hay 3 refs porque chunks_usados solo tiene 3 docs → hay que diversificar el retrieval.
  * `find_orphan_citations()` ya detecta huérfanas.

OBJETIVOS SPRINT A (hoy):
- T22.A1 (DT-049): diversificar el retrieval (≥5 docs distintos por consulta cuando existan).
  Medir con el harness scripts/eval_retrieval.py (gold set) ANTES/DESPUÉS; ajustar
  rag_max_chunks_per_doc / rag_top_k / reservas y/o garantizar "≥N docs distintos" en search().
  Sin degradar precisión. Tuning dentro de ADR-012/014 (no re-litigar).
- T22.A2 (DT-052): que los chunks usados lleguen a Referencias; endurecer el prompt para citar
  (Autor, año) de las fuentes del contexto; resolver citas huérfanas. Preservar RN-001.
- T22.A3: validación E2E sobre sectores COMPLETOS (≥2) + anti-mezcla. Identificar sectores
  completos comparando docs/sector en BD vs filas/sector en indice_emis.csv (los primeros
  completos por orden del CSV: 3020 Alimentos y 2510 Automóviles). Correr una empresa por sector
  en ≥2 sectores distintos y completos (p. ej. 3020→Alpina; 2510→empresa automotriz colombiana,
  confirmando que su GICS cae en el sector completo). Verificar por informe: referencias 3 → ≥8
  distintas, 0 huérfanas, fuentes EMIS del sector presentes, y NO mezcla de sectores (los chunks
  SECTORIALES citados son del sector de la empresa; los globales es_global=true están permitidos
  por ADR-012/018 y se excluyen del chequeo anti-mezcla).

REGLAS DURAS (CLAUDE.md TIER 1):
- No hardcodear nombres de modelo (van en .env). No credenciales en código.
- domain/ no importa SQLAlchemy/httpx/Streamlit; I/O externo por wrapper en infrastructure/.
- No re-litigar ADR-012, ADR-013, ADR-014, ADR-015. RN-001: nunca inventar atribuciones.

MÉTODO: Plan Mode antes de tocar archivos. Un commit atómico por tarea.
Gate tras cada tarea: ruff 0 + pytest -m "not slow" verde. Al cerrar Sprint A: FASE22_HALLAZGOS.md
+ tablero/deuda/changelog; luego seguir con Sprint B (T22.1/2/3/6/7) o cerrar y abrir F22-Sprint B.

LECTURAS OBLIGATORIAS al arrancar:
- docs/architecture/ROADMAP_FASE9+.md §FASE22 (Sprint A) + §5 deuda (DT-049/052)
- docs/decisions/FASE21_HALLAZGOS.md §5.1 y §5.2 (prueba A/B y diagnóstico)
- src/ic/infrastructure/retrieval/pgvector_store.py (search + reservas + MMR + max_chunks_per_doc)
- src/ic/infrastructure/citation/apa_formatter.py (build_references_section, find_orphan_citations)
- src/ic/domain/use_cases/generate_informe.py (todos_chunks → refs; _promote_cited_web; orphans)
- scripts/eval_retrieval.py (harness de evaluación, Fase 14 T14.1) + docs/eval/RUBRICA_CALIDAD.md
- src/ic/shared/config.py (rag_top_k, rag_max_chunks_per_doc, rag_*_reserve, rag_mmr_lambda)
```

> _Los dos prompts de arranque anteriores son **históricos**: el primero (Sprint A, ejecutado
> 2026-07-27) y el segundo (cierre parcial, ejecutado 2026-07-28: DT-053 medición multi-sector
> commiteado `04604cf` + monitoreo de la ingesta). El **vigente** para retomar en ventana limpia
> es el siguiente (T22.A3 E2E + cierre), pensado para el 2026-07-29._

### PROMPT DE ARRANQUE — Fase 22: T22.A3 E2E + Cierre (2026-07-29, ventana limpia)

```
## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto), sistema de informes
de inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas).
Branch de trabajo: feature/fase22-evidencia-retrieval (YA existe, NO recrear).
Hoy ejecutas T22.A3 (validación E2E del Sprint A de Fase 22) y CIERRAS el Sprint (docs + merge).
El plan detallado y aprobado está en ~/.claude/plans/refactored-bouncing-cocoa.md — LÉELO PRIMERO,
junto con el memory project_fase22_sprintA_estado y docs/decisions/FASE22_HALLAZGOS.md.

ESTADO AL ARRANCAR (verificado 2026-07-28):
- Ingesta EMIS TERMINADA (11:39): "Lote completado: 250 documentos, 21982 chunks nuevos, 5 errores".
- 7 commits en rama, gate verde (ruff 0, 348 fast tests). Último: 04604cf T22.A3 paso 0 (DT-053
  medición multi-sector). Antes: A1 4c342c4, A2 e364a52, T22.1 6e6e220, T22.6 71d67d2, docs 517fc54/3d6a9c4.
- Sectores COMPLETOS en BD: 3020 Alimentos (14 docs), 2510 Automóviles (12), 2010 Bienes de capital (11).
- 5 docs fallidos (FUERA de esos sectores, NO bloquean): Deloitte Retail, CBRE U.S. Real Estate ×2,
  FDA Novel Drug 2025, EY Desafíos LatAm 2025.

## RESTRICCIONES (CLAUDE.md TIER 1 — no negociables)
- Sin nombres de modelo en código (van en .env y tabla de routing).
- domain/ NO importa SQLAlchemy/httpx/Streamlit (Dependency Agnosticism).
- No re-litigar ADR-012/013/014/015 (filtro sectorial, reserva global, es_global exento).
- RN-001: nunca inventar atribuciones; el anti-mezcla solo MIDE y REPORTA.
- Cambios atómicos: cada entrega compila y corre; 1 commit por tarea; gate tras cada uno.
- E2E solo con Ollama libre; un pilot a la vez (VRAM WSL 8GB). NO correr E2E con ingesta viva.
- Plan Mode NO hace falta (el plan ya está aprobado); si la realidad no coincide, DETENERSE.

## PASO 0 — PRE-CHECK (read-only, imprescindible antes de E2E/harness)
  curl -s http://127.0.0.1:11434/api/tags            # Ollama responde
  curl -s http://127.0.0.1:11434/api/ps              # libre: {"models":[]}
  ps -o pid,cmd $(pgrep -f ingest_batch) 2>/dev/null # NO debe haber ingesta REAL (pgrep se caza a sí mismo)
  git branch --show-current                          # feature/fase22-evidencia-retrieval
  uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q   # ≥348
  Si algo ocupa VRAM, esperar. Si el log ya no existe / ingesta a medias → relanzar (idempotente):
    nohup uv run python scripts/ingest_batch.py --dir documentos_sectoriales \
      --csv documentos_sectoriales/FuentesEMIS/indice_emis.csv > /tmp/ingest_emis_full.log 2>&1 &

## TAREAS Y CRITERIOS DE ÉXITO

T1 — HARNESS A/B (criterios de aceptación 1 y 5)
  uv run python scripts/eval_retrieval.py --mode filtered --save docs/decisions/fase22_baseline.json
  uv run python scripts/eval_retrieval.py --mode filtered --mmr-lambda 1.0   # contraste sin MMR
  Éxito: avg_correct_chunks sube claramente vs 3.2 (baseline F14) y refleja ≥5 docs distintos donde
  existen; precision ≥ baseline F14 (1.0) sin regresión; contamination ~0.

T2 — INSTRUMENTACIÓN ANTI-MEZCLA (código pequeño permanente, TIER 4 trazabilidad)
  En generate_informe.py, tras construir `todos_chunks` (paso 10, ~L340), logger.info con el
  histograma de sectores de los chunks CITADOS. Por chunk: leer metadatos → (titulo, sector_gics,
  sectores[], es_global) y clasificar con criterio DT-053: on-sector si sector_empresa==sector_gics
  O sector_empresa in sectores; exento si es_global=='true' o sector_gics None; ajeno en otro caso.
  Loguear {on_sector, exento, ajeno} y, si hay ajenos, (titulo → sector).
  Éxito: helper puro testeable; el log aparece en cada corrida; no rompe reglas de capas.

T3 — E2E EN 2 SECTORES COMPLETOS (criterios 2, 3, 4 + T22.1 + T22.6)
  uv run python scripts/run_pilot.py --empresa "Alpina S.A.S."   # esperado GICS 3020
  uv run python scripts/run_pilot.py --empresa "Sofasa S.A."     # verificar GICS 2510 en el banner;
    si chain_02 NO resuelve 2510, reintentar con "Compañía Colombiana Automotriz".
  Éxito por informe: n_referencias/n_fuentes_total ≥ 8 (antes 3); n_citas_huerfanas = 0; fuentes
  EMIS del sector en Referencias del .docx; anti-mezcla ajeno=0 (globales/web exentos); Cap 6
  referencia un hallazgo concreto de Cap 2/3 (T22.1); Cap 5 tiene EXACTAMENTE 4 áreas (T22.6).

T4 — DOCS FALLIDOS (A3-d, no bloqueante)
  Diagnosticar la causa de los 5 errores (traceback en /tmp/ingest_emis_full.log; probable PDF
  escaneado/corrupto). Éxito: causa identificada + decisión (re-ingesta puntual o deuda → F23).

T5 — CIERRE SPRINT A
  Completar FASE22_HALLAZGOS.md §5 (harness+E2E) y §6 (métricas antes/después); actualizar tablero/
  deuda en este roadmap (T22.A3 hecho; DT-053 medición ✅, datos→F23; DT-049/052 validados);
  actualizar memory project_fase22_sprintA_estado. CONFIRMAR mensaje de commit con el humano.
  MERGE a develop --no-ff. Éxito: Sprint A cerrado y mergeado.

SPRINT B (tras el merge, o rama nueva feature/fase22-sprintB desde develop):
  T22.2 (DT-027) radar — PRIMERO re-medir hit-rate N=5 sobre corpus enriquecido (puede bastar
  endurecer prompt, sin cadena dedicada); T22.3 (DT-030) checkpoint --resume; T22.7 (DT-048) LLM-judge.

## PRUEBAS POR TAREA (gate = ruff 0 + pytest -m "not slow" tras cada commit)
- T1: dos snapshots JSON en docs/decisions/ comparados contra fase14_baseline.json; sin regresión.
- T2: test fast mockeado del helper de clasificación (on_sector/exento/ajeno), estilo test_fase14_eval.
- T3: 2 .docx en output/; leer con python-docx Cap5 (4 áreas), Cap6 (referencia a Cap2/3), Referencias;
  BD historial_informes.metricas_fiabilidad (n_fuentes_total, n_citas_huerfanas); log anti-mezcla ajeno=0.
- T4: cita del traceback + línea de decisión en FASE22_HALLAZGOS.
- T5: gate verde final; FASE22_HALLAZGOS §5/§6 completos; git log muestra merge --no-ff en develop.

## DEFINICIÓN DE "DONE" GLOBAL (Sprint A cerrado)
1. Los 6 criterios de aceptación del Sprint A demostrados con evidencia reproducible (snapshots + 2 .docx).
2. Gate verde: ruff 0 + pytest -m "not slow" ≥349.
3. FASE22_HALLAZGOS.md §5/§6 completos con métricas antes/después (refs 3→N, avg_correct 3.2→N, huérfanas 0).
4. Tablero/deuda del roadmap y memory actualizados (DT-049/052/053 resueltos o reasignados a F23).
5. Rama mergeada a develop --no-ff con mensaje aprobado por el humano.

## CIERRE DOCUMENTADO (obligatorio al terminar la sesión)
Redactar en FASE22_HALLAZGOS.md §5/§6 y en el memory, en prosa breve:
- AVANCES: qué criterios se cumplieron, con números concretos (harness, refs, huérfanas, anti-mezcla).
- RETOS: qué costó o falló (docs de ingesta fallidos, empresas que no resolvieron GICS, atascos).
- RECOMENDACIONES: siguientes pasos priorizados (curación sectores_adicionales F23, Sprint B, deuda abierta).
Y dejar el PROMPT DE ARRANQUE de la siguiente ventana (Sprint B) con esta misma estructura.

## LECTURAS
~/.claude/plans/refactored-bouncing-cocoa.md (plan A3), este roadmap §FASE22, FASE22_HALLAZGOS.md,
memory project_fase22_sprintA_estado, scripts/eval_retrieval.py, scripts/run_pilot.py,
src/ic/domain/eval/retrieval_metrics.py, src/ic/domain/use_cases/generate_informe.py (paso 10),
src/ic/domain/coherence.py.
```

---

# FASE 23 — Fuentes: Corpus EMIS completo + Servicios de búsqueda pagos

**Prioridad:** P1 · **Estimación:** ~2–3 días (incluye corrida larga de ingesta) · **Estado:** ⬜ Pendiente
**Deuda:** DT-034 (lote EMIS 250 PDFs) · **Presupuesto aprobado:** ≤ 20 USD/mes (2026-07-24)

### Objetivo

Subir la densidad de evidencia disponible por las dos vías de ADR-003: (a) completar la
ingesta del corpus EMIS (250 PDFs, 25 sectores) y (b) evaluar con datos si un servicio de
búsqueda pago (techo 20 USD/mes) mejora de forma medible la cobertura donde los servicios
gratuitos se quedan cortos (perfiles de competidores, noticias LatAm, datos de mercado).

### Contexto / por qué

- DT-034: el índice `documentos_sectoriales/FuentesEMIS/indice_emis.csv` está listo; la
  corrida completa (~2–4 h) sigue pendiente. Es la palanca directa contra los "información
  no disponible" (Q5).
- **DT-049 (E2E de cierre F21):** el problema no es solo el *volumen* de chunks (3020 ya tiene
  44 sectoriales + 594 globales) sino la **diversidad de fuentes**: esos 44 provienen de UN
  documento compilado por sector, así que el informe cita 2-3 fuentes distintas y deja 18
  "Dato no disponible" (fichas de competidor, cifras de mercado, eventos M&A/JV). La ingesta
  EMIS debe priorizar **documentos atribuibles y variados** (perfiles de competidor reales,
  informes de mercado con cifras, trackers de M&A), no solo más chunks del mismo compilado.
- Tavily free con `search_depth="basic"` fue causa raíz de DT-035 (Cap 2 vacío). F21 mitiga
  con `advanced` y mejores queries; el E2E de cierre mostró que aún así el web trae resultados
  poco relevantes (todolicitaciones.cl) y solo 1/122 chunks se cita → esta fase mide si un
  proveedor pago aporta perfiles de competidor y datos de mercado citables.
- Decisión de sesión 2026-07-24: evaluar proveedores pagos "no muy costosos"; techo inicial
  acordado 20 USD/mes.

### Tareas

- [ ] **T23.1 (DT-034 + mitad de DT-049) — Ingesta del lote EMIS completo.** El corpus **ya
      está en disco**: `documentos_sectoriales/FuentesEMIS/<Sector>/` (25 carpetas de sector) +
      índice `documentos_sectoriales/FuentesEMIS/indice_emis.csv` (**250 documentos**; columnas
      archivo/sector_gics/sectores_adicionales/tipo/autor/año/titulo/empresa). Cada sector GICS
      tiene múltiples fuentes distintas y atribuibles (p. ej. 3020: CFA, EMIS H2 2025,
      Euromonitor Sector Capsules, GlobalData) — esto ataca directamente la **baja diversidad
      de fuentes** de DT-049. Corrida larga (nohup/tmux, fuera del pipeline, ~2–4 h):
      ```bash
      uv run python scripts/ingest_batch.py \
        --dir documentos_sectoriales \
        --csv documentos_sectoriales/FuentesEMIS/indice_emis.csv
      ```
      Idempotente por título (no colisiona con los compilados de Fase 13; conviven). Nota: la
      columna `tipo="INFORME_EMIS"` cae a `PDF_SECTORIAL` si el enum no la tiene — evaluar añadir
      `INFORME_EMIS` a `TipoDocumento` para trazabilidad. Verificar conteos por sector (panel
      Repositorio + SQL sobre `informes_ic.embeddings_vectoriales`); medir cobertura y nº de
      fuentes distintas citadas antes/después (harness `scripts/eval_retrieval.py` + rúbrica F20).
      **Re-correr el E2E de Alpina** tras la ingesta y comparar contra `FASE21_HALLAZGOS.md §5`
      (objetivo: bajar los 18 "Dato no disponible" y subir de 3 a >8 fuentes citadas).
      **Estado 2026-07-24:** el **sector 3020 ya está ingestado** (44→286 chunks / 14 docs) y sirvió
      para la prueba A/B (§5.2). El **lote completo (250 docs)** se lanza HOY como tarea de fondo,
      en paralelo al Sprint A de F22 (evidencia/retrieval). Idempotente: 3020 se salta.
- [ ] **T23.2 — Matriz de proveedores de búsqueda.** Candidatos mínimos: Tavily tier pago,
      Serper.dev, Brave Search API, Exa, SerpAPI; opcional APIs de datos empresariales.
      Columnas: costo por 1k consultas, tier gratuito, cobertura noticias/LatAm/español,
      profundidad de contenido, ToS (¿permite almacenar resultados? — requisito ADR-013),
      latencia. Dimensionar el techo de 20 USD/mes con volumen real (CacheCounter +
      CostTracker: consultas/informe × informes/mes estimados).
- [ ] **T23.3 — Piloto A/B medible.** 1–2 proveedores elegidos, integrados vía wrapper en
      `infrastructure/sources/` (mismo contrato que `WebConnector`; API key en `.env`).
      Misma empresa/corrida con proveedor gratuito vs pago → comparar nº de fichas de
      competidores con datos, refs citadas por cap y % de secciones en ausencia.
- [ ] **T23.4 — Decisión → ADR-016.** Proveedor(es), presupuesto mensual, routing de
      búsqueda por tipo de query (genérica → gratuito/caché; perfil de competidor →
      pago/advanced). Config en `.env` + tabla de routing; nunca hardcodear.
- [ ] **T23.5 (DT-050) — Base de conocimiento de empresas (directorio + acumulación).**
      Diseño completo en `docs/architecture/PROPUESTA_BASE_EMPRESAS.md`. Plan Mode obligatorio.
      Alcance mínimo sugerido: (a) tabla `informes_ic.empresas_directorio` + migración idempotente;
      (b) `scripts/seed_empresas_directorio.py` que siembra del corpus
      `documentos_sectoriales/FuentesEMIS/EmpresasColombia/` (~98k empresas; header en fila 8;
      dedup por NIT) con mapeo Sector-Local→GICS (reutilizar `ciiu_gics.py` o tabla de mapeo);
      (c) gancho de **lectura** en Cap 2/4 que inyecta jugadores locales del sector como contexto
      estructurado. La **escritura automática** (nutrir el directorio con hallazgos del informe) y
      la **curación humana** (`curado` bool + panel UI → HITL F24/F25) son iteraciones siguientes.
      Verificar ToS de los datos (ISI Markets/WVB) antes de persistir/usar.

### Criterios de aceptación

1. Corpus EMIS completo ingestado; conteos por sector verificados (DT-034 ✅).
2. Matriz de proveedores con costos reales y veredicto de ToS.
3. Piloto A/B con tabla antes/después (rúbrica F20 y/o métricas del harness).
4. ADR-016 registrado; el proveedor pago (si se adopta) opera tras wrapper con caché
   (`CachedWebConnector`) y presupuesto en `CostTracker`.
5. (T23.5/DT-050) Directorio sembrado y consultable por sector; Cap 2/4 reciben jugadores
   locales del directorio (demo/test). Curación humana pospuesta.
6. Gate verde: ruff 0 + `pytest -m "not slow"`.

### PROMPT DE ARRANQUE — Fase 23

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase23-fuentes (crear desde develop).

ESTADO DE ENTRADA (Fases 19–22 cerradas):
- Auditoría y gap analysis hechos (FASE19/20_HALLAZGOS.md); Sprint A de contenido y
  coherencia/robustez cerrados (FASE21/22_HALLAZGOS.md).
- DT-034 pendiente: índice EMIS listo (documentos_sectoriales/FuentesEMIS/indice_emis.csv),
  falta la corrida larga (~2–4 h).
- Presupuesto aprobado para búsqueda paga: ≤ 20 USD/mes.

OBJETIVOS (T23.1–T23.4): ingesta lote EMIS completo + verificación de cobertura; matriz de
proveedores pagos (Tavily pago, Serper, Brave, Exa, SerpAPI…); piloto A/B medible tras
wrapper; decisión en ADR-016 con routing de búsqueda por tipo de query.

REGLAS DURAS: API keys solo en .env; todo proveedor nuevo entra por wrapper en
infrastructure/sources/ con el contrato de WebConnector y detrás de CachedWebConnector;
respetar ADR-013 (persistir solo lo citado) y verificar que los ToS del proveedor lo
permiten; no re-litigar ADR-012/013/014.

MÉTODO: Plan Mode. La corrida de ingesta va en nohup/tmux y se monitorea; no bloquear la
sesión. Gate tras cada tarea: ruff 0 + pytest -m "not slow" verde.

LECTURAS OBLIGATORIAS al arrancar:
- docs/architecture/ROADMAP_FASE9+.md §FASE23 (esta sección)
- docs/decisions/FASE20_HALLAZGOS.md (rúbrica) y FASE21/22_HALLAZGOS.md (estado)
- docs/architecture/ADR-003 (doble vía) y ADR-013 (persistencia solo-citado)
- docs/runbooks/BUSQUEDA_FUENTES.md (runbook creado en F21)
- scripts/ingest_batch.py + documentos_sectoriales/FuentesEMIS/indice_emis.csv
- src/ic/infrastructure/sources/web_connector.py y cached_connector.py

CIERRE: FASE23_HALLAZGOS.md + ADR-016 + tablero §4 / deuda §5 (DT-034) / changelog §8.
Propón el PROMPT DE ARRANQUE ajustado de la FASE 24 (HITL Gap Auditor).
Confirma el mensaje de commit conmigo; mergea a develop con --no-ff.
```

---

# FASE 24 — HITL Módulo 1: Gap Auditor (ex-F21 en v2.5)

**Prioridad:** P1 · **Estimación:** ~3–4 días · **Estado:** ⬜ Pendiente
**ADR:** ADR-015 (HITL Post-Generación, aprobado 2026-07-23; el ADR usa la numeración
v2.5: sus "Fases 21–22" son las actuales F24–F25)

### Objetivo

Implementar la primera capa de revisión post-generación: el **Gap Auditor**. Tras generar un
informe, el usuario puede auditarlo con un LLM que identifica brechas de información, solicita
documentos adicionales, y desencadena una regeneración completa con los nuevos insumos.

El Gap Auditor convierte el sistema de "pipeline one-shot" a "loop de calidad controlado
por el usuario" sin abrir el pipeline a mid-gen HITL (que se reserva para fases futuras).

### Decisiones arquitectónicas aprobadas (2026-07-23)

1. **Punto de intervención:** Post-generación (no mid-pipeline). El usuario ve el informe
   completo antes de decidir si auditarlo.
2. **Regeneración:** Full pipeline cuando se añaden nuevos documentos. Los nuevos docs se
   ingresan al índice RAG (con deduplicación SHA-256) → regeneración completa → el nuevo
   contenido impacta en todos los caps.
3. **Lógica "complement-not-replace":** La regeneración recibe el texto del informe anterior
   como contexto adicional en los prompts para guiar al LLM a complementar, no contradecir.
   Evita partir de cero y preserva hallazgos previos válidos.
4. **Aprobación:** El usuario controla cuándo termina el loop. Botón "Aprobar informe" en UI.
   Futuro: notificaciones cuando haya cambios pendientes de aprobación.
5. **UI:** Integrado en el tab Historial (por informe). Botón "Auditar" abre panel lateral
   con: gaps priorizados (Alta/Media/Baja), tipo de dato faltante, fuentes recomendadas,
   upload de documentos adicionales, botón "Regenerar con nuevos insumos".

### Base: `source_prompts/13. Prompt (Opcional) - Evaluar Informe.docx`

El prompt de auditoría ya existe como template en `source_prompts/`. La fase lo adapta a
`chain_evaluar.py` con la estructura requerida:
- Sección 1: Gaps identificados con prioridad (Alta/Media/Baja) y tipo (datos de mercado,
  perfiles competidores, marco regulatorio, etc.)
- Sección 2: Fuentes recomendadas para cada gap
- Sección 3: Plan de mejora priorizado

### Tareas

- [ ] **T24.1 — `chain_evaluar.py` (domain/chains/).** Adaptar `source_prompts/13` a LCEL.
      Inputs: texto completo del informe (caps 1–6 + resumen). Output: `EvaluacionResult`
      (lista de `Gap(prioridad, tipo, descripcion, fuente_recomendada)`).
- [ ] **T24.2 — `generate_evaluacion.py` (domain/use_cases/).** Use case que invoca
      `chain_evaluar.py` y persiste el resultado en BD (tabla `evaluaciones_informe`).
- [ ] **T24.3 — Deduplicación de documentos.** Antes de ingestar un documento nuevo,
      verificar SHA-256 del texto contra los existentes en BD. Si ya existe (mismo contenido),
      notificar al usuario y no duplicar chunks. Implementar en `PdfIngestor` (ya tiene
      chunk-level SHA; este es doc-level SHA del contenido completo).
- [ ] **T24.4 — UI: panel Auditar en tab Historial (`app.py`).**
      Por cada informe en el historial: botón "Auditar" → llama a `generate_evaluacion.py` →
      muestra panel con gaps priorizados + upload de docs + botón "Regenerar".
      Botón "Aprobar informe" para cerrar el loop.
- [ ] **T24.5 — Regeneración completa con complement context.**
      `GenerateInforme.execute()` acepta `complement_context: str | None` (texto del informe
      anterior). Si presente, se inyecta como contexto adicional en todos los prompts N1/N2/N3
      con instrucción: "El análisis previo concluyó: {complement_context[:500]}. Complementar
      con los nuevos insumos; no contradecir conclusiones válidas salvo evidencia explícita."
- [ ] **T24.6 — Tests y E2E.** Tests unitarios de `chain_evaluar` (fixtures de informe con
      gaps conocidos). Test de deduplicación. E2E: auditar informe Alpina → subir 1 PDF nuevo
      → regenerar → verificar que el nuevo PDF es citado en el informe regenerado.

### Criterios de aceptación

1. El Gap Auditor identifica ≥1 gap real en un informe E2E (inspección manual).
2. Subir un PDF ya ingestado muestra advertencia de duplicado sin ingestar de nuevo.
3. El informe regenerado con nuevo PDF cita el nuevo documento (trazable en referencias).
4. "Aprobar informe" marca el informe como aprobado en la BD (campo `aprobado=True`).
5. Gate verde: ruff 0 + `pytest -m "not slow"` (≥305 + tests nuevos de fases previas).

### PROMPT DE ARRANQUE — Fase 24

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase24-hitl-gap-auditor (crear desde develop).

ESTADO DE ENTRADA (Fases 21, 22 y 23 cerradas):
- DT-035/036 cerrados (Sprint A). DT-027/030/Q1 cerrados (coherencia).
- El sistema genera informes completos con citación APA, retrieval priorizado y checkpoint.
- HITL no existe aún: el analista solo puede ver el informe final.

CONTEXTO DE LA DECISIÓN (ADR-015, aprobado 2026-07-23):
- Gap Auditor: post-generación, loop controlado por usuario.
- Regeneración: full pipeline (nuevos docs → RAG → todos los caps se benefician).
- Deduplicación: check SHA-256 a nivel documento antes de ingestar.
- Complement-not-replace: texto previo como contexto para no partir de cero.
- UI: panel en tab Historial, botón "Auditar" por informe, botón "Aprobar informe".
- Template base: source_prompts/13. Prompt (Opcional) - Evaluar Informe.docx

OBJETIVOS DE FASE 24:
- T24.1: chain_evaluar.py (LCEL, adaptar source_prompts/13).
- T24.2: generate_evaluacion.py + tabla evaluaciones_informe en BD.
- T24.3: deduplicación doc-level SHA-256 en PdfIngestor.
- T24.4: UI panel Auditar en historial.
- T24.5: GenerateInforme.execute() acepta complement_context.
- T24.6: tests + E2E con nuevo PDF.

REGLAS DURAS:
- No hardcodear modelos. domain/ no importa librerías externas.
- No re-litigar ADR-012, ADR-013, ADR-014, ADR-015.
- La regeneración es SIEMPRE full pipeline (no selectiva por cap).
- El deduplicador verifica doc-level SHA ANTES de ingestar.

LECTURAS OBLIGATORIAS al arrancar:
- docs/architecture/ROADMAP_FASE9+.md §FASE24 (esta sección)
- docs/architecture/ADR-015-hitl.md (todas las decisiones)
- docs/decisions/FASE23_HALLAZGOS.md (estado)
- source_prompts/13. Prompt (Opcional) - Evaluar Informe.docx (template)
- src/ic/domain/use_cases/generate_informe.py (pipeline actual)
- src/ic/presentation/app.py (UI actual — historial tab)
- src/ic/infrastructure/sources/pdf_ingestor.py (deduplicación chunk-level existente)
```

---

# FASE 25 — HITL Módulo 2: Consistency Checker + Pruebas UI HITL (ex-F22 en v2.5)

**Prioridad:** P1 · **Estimación:** ~2–3 días · **Estado:** ⬜ Pendiente
**ADR:** ADR-015 (HITL Post-Generación, aprobado 2026-07-23; numeración v2.5:
"Fases 21–22" = actuales F24–F25)
**Prerequisito:** Fase 24 (Módulo 1 operativo)

### Objetivo

Implementar la segunda capa de revisión post-generación: el **Consistency Checker**. Detecta
contradicciones entre capítulos y las resuelve automáticamente (contradicciones factuales) o
las presenta al usuario para resolución manual (claims estratégicos).

### Decisiones arquitectónicas aprobadas (2026-07-23)

- **Detección:** LLM lee pares de capítulos y genera un reporte de inconsistencias tipadas.
- **Resolución auto:** Inconsistencias **factuales** (cifras, porcentajes, años, nombres de
  empresas) — el sistema las resuelve usando Tavily `basic` para verificar el dato correcto.
- **Resolución manual:** Inconsistencias **estratégicas** (interpretaciones, recomendaciones,
  prioridades) — se presentan al usuario en un panel con las dos versiones para que elija.
- **UI:** Panel en historial, integrado con el Gap Auditor (Fase 24). El analista ve:
  inconsistencia, tipo (factual/estratégica), caps involucrados, propuesta de resolución.

### Tareas

- [ ] **T25.1 — `chain_consistencia.py`.** LLM compara caps por pares y genera lista de
      `Inconsistencia(tipo, cap_a, cap_b, texto_a, texto_b, descripcion)`.
- [ ] **T25.2 — `generate_consistencia.py`.** Orquesta la comparación: N1 caps vs N2/N3;
      persiste resultado en BD.
- [ ] **T25.3 — Resolución automática de inconsistencias factuales.** Para cada
      inconsistencia factual: buscar con Tavily `basic` → determinar valor correcto →
      aplicar patch al texto del cap afectado.
- [ ] **T25.4 — UI: panel de inconsistencias.** Complementa el panel de gaps de Fase 24.
      Lista de inconsistencias con tipo + botón "Resolver auto" para factuales + formulario
      de selección para estratégicas.
- [ ] **T25.5 — Tests y E2E.** Fixture con informe que tiene inconsistencia conocida;
      verificar que el checker la detecta y la resolución auto la corrige.
- [ ] **T25.6 — Pruebas de UI del flujo HITL completo.** Cubrir con
      `streamlit.testing.AppTest` el flujo Auditar → subir docs → Regenerar → Aprobar
      (Módulos 1 y 2) y cerrar con una sesión manual guiada con el usuario (primera
      prueba real de la UI HITL). Registrar hallazgos de UX en FASE25_HALLAZGOS.md.

### Criterios de aceptación

1. El checker detecta una inconsistencia factual introducida deliberadamente en un fixture.
2. La resolución auto corrige la inconsistencia y el cambio es trazable en logs.
3. Una inconsistencia estratégica se presenta al usuario con las dos versiones.
4. Flujo HITL completo probado en UI (AppTest verde + sesión manual con el usuario).
5. Gate verde: ruff 0 + `pytest -m "not slow"`.

### PROMPT DE ARRANQUE — Fase 25

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase25-hitl-consistency (crear desde develop).

ESTADO DE ENTRADA (Fases 21–24 cerradas):
- Gap Auditor operativo (chain_evaluar, generate_evaluacion, complement_context, UI panel).
- Deduplicación doc-level en PdfIngestor.

CONTEXTO (ADR-015):
- Factual: auto-resolve con Tavily basic.
- Estratégico: presentar al usuario para selección.
- UI integrado en el panel de historial junto al Gap Auditor.

OBJETIVOS DE FASE 25:
- T25.1: chain_consistencia.py (comparación por pares).
- T25.2: generate_consistencia.py.
- T25.3: resolución auto factuales (Tavily basic).
- T25.4: UI panel inconsistencias.
- T25.5: tests + E2E.
- T25.6: pruebas de UI del flujo HITL (AppTest + sesión manual guiada).

LECTURAS OBLIGATORIAS:
- docs/architecture/ROADMAP_FASE9+.md §FASE25
- docs/architecture/ADR-015-hitl.md
- docs/decisions/FASE24_HALLAZGOS.md
- src/ic/presentation/app.py (UI panel gap auditor de Fase 24)
```

---

# FASE 26 — Estilo y Visualización del Documento Final

**Prioridad:** P1 (cierra el ciclo "producto comercial") · **Estimación:** ~3–4 días · **Estado:** ⬜ Pendiente
**Entrada clave:** rúbrica visual y brechas de formato de `FASE20_HALLAZGOS.md` (Q7)

### Objetivo

Llevar el .docx/.pdf generado al nivel visual del informe patrón: plantilla de estilos Word
más rica, callouts, colores corporativos, tablas estilizadas, jerarquía tipográfica,
transiciones narrativas, figuras adicionales y QA visual sistemático.

### Tareas

- [ ] **T26.1 — Plantilla de estilos enriquecida.** Estilos de tabla corporativos, callouts
      con color (datos ausentes / accionables), colores de headings, portada pulida. Todo
      en `infrastructure/render/` (domain/ no conoce python-docx).
- [ ] **T26.2 — Secciones del patrón pendientes de F20.** Metodología + aviso de uso de IA
      (si F21/T21.7 no las dejó ya con estilo final) y cualquier subcap estructural que F20 haya
      asignado aquí.
- [ ] **T26.6 — Brechas de formato de FASE20 (§5).** (a) Fichas de competidor 2.1 como **tablas
      reales** de 7 columnas (patrón Noel T3–T8), no markdown pipe suelto; (b) nivel de headings
      consistente (los subcaps de Cap 4/5 se renderizaban a veces como `##` en vez de `###`);
      (c) reforzar prohibiciones de estilo del Resumen Ejecutivo ("es importante", "se recomienda",
      "se observa", "hay oportunidades"). Todo en `infrastructure/render/` + `assembler.py`.
- [ ] **T26.3 — Figuras adicionales.** Según brechas de F20 (p. ej. gráfico de tendencias,
      mapa de ecosistema), con el patrón de `radar_chart.py` (matplotlib Agg vía
      infrastructure/charts/).
- [ ] **T26.4 — Transiciones narrativas.** Párrafos puente entre capítulos (plantillas en
      shared/ o generación ligera), según lo que la rúbrica de F20 marque como brusco.
- [ ] **T26.5 — QA visual sistemático.** Checklist .docx/.pdf (fuentes, numeración, TOC,
      sangría francesa, tablas, figuras, saltos) + comparación lado a lado contra el patrón
      Noel con la rúbrica visual. Corrida E2E de validación final.

### Criterios de aceptación

1. Comparación lado a lado informe generado vs patrón Noel: rúbrica visual de F20 en verde
   (o brechas restantes documentadas y aceptadas por el usuario).
2. Checklist de QA visual pasada sobre el E2E final (.docx y .pdf).
3. domain/ sigue sin importar librerías de render (verificable por grep).
4. Gate verde: ruff 0 + `pytest -m "not slow"`.

### PROMPT DE ARRANQUE — Fase 26

```
Eres Claude Code trabajando en el proyecto InformesAuto (~/Test/InformesAuto).
Branch de trabajo: feature/fase26-estilo (crear desde develop).

ESTADO DE ENTRADA (Fases 19–25 cerradas): pipeline auditado, contenido y coherencia
mejorados, corpus EMIS completo, HITL operativo y probado en UI. Queda el pulido visual.

OBJETIVOS (T26.1–T26.5): plantilla de estilos enriquecida; secciones del patrón pendientes
(Metodología + aviso IA); figuras adicionales; transiciones narrativas; QA visual
sistemático contra el patrón Noel.

REGLAS DURAS: domain/ no importa python-docx/matplotlib (todo en infrastructure/render e
infrastructure/charts); no hardcodear modelos; fuentes del sistema documentadas (Open Sans
— ver DT-024 en §5).

LECTURAS OBLIGATORIAS al arrancar:
- docs/architecture/ROADMAP_FASE9+.md §FASE26 (esta sección)
- docs/decisions/FASE20_HALLAZGOS.md (rúbrica visual y brechas asignadas a F26)
- docs/decisions/FASE25_HALLAZGOS.md (estado)
- docs/architecture/ADR-011 (modelo de documento y PDF)
- src/ic/infrastructure/render/docx_renderer.py y pdf_renderer.py
- src/ic/domain/report_model.py y src/ic/domain/markdown_parser.py
- InformeSectoryCompetitivoNoel.docx (patrón visual)

CIERRE: FASE26_HALLAZGOS.md + tablero §4 / changelog §8. Propón el plan de la Fase 27+
(operación continua) según lo aprendido. Confirma el commit; mergea a develop con --no-ff.
```

---

## 7. Decisiones abiertas / preguntas al humano

Se resuelven en la fase indicada (o antes si se puede).

- **Q1 (Fase 9) — Ramas y CI. ✅ RESUELTO (2026-07-21).** Se adopta el flujo GitHub del
  PRIME DIRECTIVE §4.3: `main` protegida, `develop` como base, una rama por fase. CI corre
  **solo local** (no hay remoto GitHub); se implementa como hook/script local en la Fase 9.
- **Q2 (Fase 11) — Motor de PDF. ✅ RESUELTO (2026-07-21).** LibreOffice headless
  (`/usr/bin/soffice`). Documentado en ADR-011.
- **Q3 (Fase 13) — Repositorio sectorial y RAG del equipo. ✅ RESUELTO (2026-07-22).**
  - Proyecto RAG del equipo estudiado (`~/Test/RepositorioRN`): se adopta cap por documento
    (inspirado en su MMR). Ver `FASE13_HALLAZGOS.md` §3.
  - PDFs sectoriales: `documentos_sectoriales/*.pdf` (25, gitignored); índice reconciliado en
    `documentos_sectoriales/indice.csv`.
  - Identificador sectorial canónico: **código GICS numérico** vía `extract_gics_code`
    (ADR-012), en lugar de una tabla CIIU/GICS.
- **Q4 (Fase 18) — HITL: arquitectura y 4 decisiones. ✅ RESUELTO (2026-07-23).**
  Sesión de análisis comparativo de informes Alpina reveló que:
  - Cap 2 vacío en competidores = comportamiento correcto (no alucinación), pero el RAG
    necesita queries específicas + Tavily `advanced` (DT-035 → Fase 19).
  - Cap 3 off-topic = contaminación de chunks globales sin filtro sectorial (DT-036 → Fase 19).
  - Source prompt #13 (Evaluar Informe) no estaba implementado → base del Gap Auditor.
  Decisiones HITL aprobadas: (1) post-generación; (2) full pipeline al añadir docs +
  deduplicación SHA-256 + complement-not-replace; (3) usuario controla el cierre del loop;
  (4) UI en tab Historial. Documentadas en ADR-015.

**ADRs vigentes:** ADR-001 … ADR-015 (15 ADR). Auditados en Fase 19 (ver `FASE19_HALLAZGOS.md §5`):
todos fieles salvo divergencias registradas como deuda (ADR-004 LCEL→DT-042; ADR-009 regresión
de tamaño→DT-039; ADR-014 tabla de estado obsoleta→corrección documental).

---

## 8. Changelog del roadmap

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-07-24 | 3.4 | **Post-F21: hallazgos de ingesta EMIS + re-scoping de F22.** Prueba A/B (sector 3020 ingestado, 44→286 chunks/14 docs): el contenido mejora mucho (Cap 2.1 ausente→14 fichas en tabla; radar placeholder→real; 1→16 tablas) pero la citación no (refs planas en 3, fuentes EMIS no citadas, 1 huérfana). Nuevas deudas: **DT-051** (bytes NUL en ingesta de PDF — ✅ cerrada, `_sanitize_text`, merge `3256403`), **DT-052** (citación no sigue al corpus → F22 Sprint A), **DT-050** (base de conocimiento de empresas desde EmpresasColombia ~98k → propuesta `PROPUESTA_BASE_EMPRESAS.md`, diferida). **F22 re-scoped** a "Evidencia, Retrieval y Coherencia": **Sprint A** (hoy, paralelo a la indexación EMIS de fondo) = DT-049 (diversidad de retrieval) + DT-052 (citación); **Sprint B** = coherencia/checkpoint/áreas/LLM-judge (T22.1/3/6/7); DT-027 radar a re-medir sobre corpus enriquecido. T23.1: 3020 ingestado, lote completo (250) lanzado hoy en background. |
| 2026-07-24 | 3.3 | **Fase 21 (Calidad de Contenido — Sprint A + A') cerrada** (`1a96d7b`..`9a27820`). T21.1 (DT-035): `search_depth` parametrizable en WebConnector + CachedWebConnector, queries de competidor `advanced` (firma pública intacta). T21.2 (DT-036): constraint sectorial en casos locales `chain_04` + query web dedicada en `generate_tendencias`. T21.5 (DT-043): `chain_03`/`chain_04` **des-sesgados** por `{sector_gics}` (fuera FoodTech/agroindustrial). T21.7 (DT-045): secciones formales **Metodología** + **Aviso de uso de IA** en `assembler`. T21.8 (DT-046): **Cap 4 reescrito** a 4.1–4.5 (movimientos corporativos, 3 eventos/subcap). T21.6 (DT-044): **Cap 2.3 Mercado** — `chain_03b_mercado` + `CapMercado` + `GenerateMercado` + cableado N1 (max_workers=4) + interleave 2.2↔2.4. T21.3: runbook `BUSQUEDA_FUENTES.md` reconciliado con scripts reales. Las 6 DT de contenido (035/036/043/044/045/046) **cerradas**. `docs/prompts/` = 9/9 chains. **321 fast tests** (+16), ruff 0. **E2E Alpina** validó los 5 criterios estructurales (2.3 Mercado+tabla, Metodología, Aviso IA, Cap 4 en 4.1–4.5, Cap 3 sin KPO/turismo). **Hallazgo nuevo DT-049**: evidencia RAG delgada (Alpina citó 3 refs, 18 "Dato no disponible", 1/122 chunks web citados) por baja diversidad de fuentes en el corpus compilado → retrieval/breadth a F22 (T22.4), corpus diverso + búsqueda paga a F23. `FASE21_HALLAZGOS.md`. |
| 2026-07-24 | 3.2 | **Fase 20 (Gap Analysis vs patrón Noel) cerrada.** T20.1: rúbrica versionada `docs/eval/RUBRICA_CALIDAD.md` v1.0 (5 dimensiones E/P/V/F/T × 0–3 por capítulo, manual + LLM-judge). T20.2: matriz de brechas de 3 informes — hallazgo raíz: **variabilidad brutal por sector** (Alpina food ≈11–13/cap dentro del corpus; Avianca/Bancolombia fuera del corpus ≈5–7/cap y **0 tablas**). T20.3: auditoría de fidelidad — `docs/prompts/` completado a **8/8 chains + README** (mapa de los 17 source_prompts); `prompt-05-convergencia`→`prompt-06`. Divergencias: `chain_05` reescribió Cap 4 (🔴), sesgo "FoodTech/agroindustrial" hardcodeado (🔴), 2.3 Mercado nunca implementado (🔴). T20.4: **Metodología + Aviso de uso de IA ausentes** del ensamblado. Bug numeración 5.x confirmado **pre-fix** (DT-032 cerrado). Nuevas DT-043..048. F21 ampliada a Sprint A' de contenido (T21.5–T21.8: des-sesgo, 2.3 Mercado, Metodología/Aviso IA, rediseño Cap 4); F22 +T22.6/T22.7 (áreas Cap 5, LLM-judge); F26 +T26.6 (fichas-tabla, headings, estilo). Sin cambios en `src/`; gate verde (305 fast, ruff 0). `FASE20_HALLAZGOS.md`. |
| 2026-07-24 | 3.1 | **Fase 19 (Auditoría) cerrada.** T19.1: 3 archivos > 300 L confirmados + `_run_n3`=157 L; cobertura `domain/` (gate rápido) = **69%** (< 80%; pytest-cov añadido como dev-dep). T19.3: 15 ADR + 13 RN auditados con evidencia `archivo:línea` — divergencias ADR-004 (LCEL en domain), ADR-009 (regresión tamaño), ADR-014 (tabla obsoleta), RN-013 (`search_depth` no implementado). T19.4: **DT-018 cerrado** (`check-ruff.sh` cableado en `settings.json`); DT-027 retarget→F22; colisión DT-035 documentada. Nuevas DT-037..042 (particiones + pricing/hook + cobertura + LCEL). Re-priorización: F22 absorbe DT-027/037/039/040/041/042; F26 absorbe DT-038. Sin cambios en código de aplicación; gate verde (305 fast, ruff 0). `FASE19_HALLAZGOS.md`. |
| 2026-07-24 | 3.0 | **Re-secuenciación completa post-Fase 18 ("alto en el camino").** Nuevas fases: F19 Auditoría de arquitectura/código/docs (señales: gateway.py 503 L, app.py 487 L, generate_informe.py 438 L > red flag 300 L; docs/prompts con 4/13 source_prompts) y F20 Gap Analysis vs informe patrón Noel (rúbrica medible por capítulo). Renumeradas: F21=Sprint A (ex-F19), F22=Coherencia (ex-F20, +T22.4 enriquecimiento dirigido post-N1: entidades de Cap 2/3 → búsquedas de contraste para Cap 5/6), F24=HITL Gap Auditor (ex-F21), F25=HITL Consistency (ex-F22, +T25.6 pruebas UI HITL con AppTest + sesión manual). Nuevas: F23 Fuentes (DT-034 lote EMIS completo + evaluación servicios de búsqueda pagos, techo ≤20 USD/mes → ADR-016) y F26 Estilo y Visualización (Q7). ADR-015 conserva numeración v2.5 (nota de mapeo en §6). DT-030→F22, DT-034→F23, DT-035/036→F21. |
| 2026-07-23 | 2.3 | Fase 17 cerrada (`7e6ec20`..`6927063`): T17.1 CacheCounter ✅ (DT-026), T17.4 Open Sans ✅ (DT-024), DT-029 fallback red transitoria ✅ (validado en prod, corrida Alpina), T17.3 cross-sector EPM→5510 ✅, T17.2 N=5 corridas → radar 50% → DT-027 🔴 cadena dedicada. Nuevas DT-030..033 (checkpoint, doc global convergencia, numeración, citación APA PDFs). §6 reordenado: F18 Evidencia y Citación → F19 Coherencia y Robustez → F20 Estilo y Visualización → F21+ operación. Sección FASE 18 detallada. 289 tests fast, ruff 0. |
| 2026-07-21 | 1.0 | Creación del roadmap Fase 9–13 con prompts de arranque autocontenidos. |
| 2026-07-21 | 1.1 | Resueltas Q1 (flujo GitHub PRIME DIRECTIVE + CI local), Q3 parcial (RAG del equipo en `~/Test/RepositorioRN`). Añadido paso de rama por fase; prompt Fase 9 actualizado. |
| 2026-07-21 | 1.2 | Fase 9 cerrada: T9.1 ruff 0 errores ✅, T9.4 E2E 165.87 s ✅, T9.3 Makefile+ci.yml ✅, T9.2 check-ruff.sh ✅ (settings.json pendiente manual). DT-005 ✅, DT-018 🟡. |
| 2026-07-21 | 1.3 | Fase 10 cerrada: T10.1 CJK en 6 use cases ✅, T10.2 orphan checker + contexto con meta ✅, T10.3/T10.4 APA 7 fiel ✅, T10.5 panel fiabilidad JSONB ✅, T10.6 disclaimer parametrizable ✅. 137 tests, DT-009/015/017(parcial) cerrados. |
| 2026-07-21 | 1.4 | Fase 11 cerrada: T11.1 report_model ✅, T11.2 docx_renderer+assembler refactor ✅, T11.3 markdown_parser+TableBlock ✅, T11.4 radar chart ✅, T11.5 PDF LibreOffice ✅, T11.7 callouts ✅. 162 tests fast, ADR-011 creado, DT-016 cerrado, DT-019 nuevo. Q2 resuelta. |
| 2026-07-21 | 1.5 | Fase 12 cerrada: T12.3 DT-004 ✅ (generate_n1.py, 345 L), T12.4 DT-010 ✅ (tokens reales Ollama + tiempo_ollama_s), T12.5 DT-012 ✅ (paginación+filtro+CSV). 168 tests fast. T12.1/T12.2 (caché/resiliencia) pospuestos a Fase 14. |
| 2026-07-22 | 2.2 | Fase 16 cerrada (`aadd99e`): T16.0 CachedWebConnector/OpenAlexConnector cableados en N0/N1/N2 (thread-safe por sesión propia por thread) + ResilientChatModel único reemplaza 3 tiers individuales ✅; T16.1 `_extract_radar()` + instrucción radar_json en prompt + radar_data en CapBenchmarking + fallback garantizado (DT-019 ✅); T16.2 `_apply_normal_style()` Calibri 11pt justif 1.16x (DT-024 ✅); T16.3 instrucción pipe-table en SYSTEM_PROMPT_03 + test E2E tabla Word ✅. 277 tests fast, ruff 0. |
| 2026-07-22 | 2.1 | Fase 16 planificada: T16.0 cableado E2E (CachedConnector+ResilientChatModel), T16.1 radar real (DT-019), T16.2 estilo Normal .docx (DT-024), T16.3 tablas Word fichas competidores. Sección FASE 16 y fila tablero §4 añadidas al roadmap. |
| 2026-07-22 | 2.0 | Fase 15 cerrada: T15.1 batch_mode() Embedder (keep_alive de lote + flag --warm) ✅; T15.2 CachedWebConnector/OpenAlexConnector + tabla retrieval_cache ✅; T15.3 is_rate_limit_error + ResilientChatModel (free→free_alt→synth→paid) + timeouts por tier (DT-021 ✅); T15.4 eval_gate.py + fase15_budget.json ✅; T15.5 purge scoping + nota /api/generate ✅. 262 tests fast, ruff 0. Pendiente cablear caché+resiliencia en pipeline E2E (ver §8 recomendaciones FASE15_HALLAZGOS). |
| 2026-07-22 | 1.9 | Fase 14 cerrada (`1fbe8a1`): T14.1 harness de evaluación + gold set (línea base filtered ya óptima: precision 1.0/contam 0.0/hit 1.0) ✅; T14.2 MMR portado **medido y revertido** (degrada con evidencia mono-documento; λ=1.0 por defecto) ✅; T14.3 chunk_size 1000/200 (retrieval-neutral, se mantiene por eficiencia: 998 vs 1746 chunks) ✅; T14.4 índice **descartado** (SQL 15ms, embed domina 99%) ✅; T14.5 persistencia web "solo lo citado" (ADR-013) + purga backlog 1202→0 → evidencia sectorial 3.20→3.68 ✅; T14.6 CIIU→GICS (`ciiu_gics.py`) ✅. DT-020/022/023 cerradas. 223 tests fast, E2E Comfama verificado. FASE14_HALLAZGOS + ADR-013 + addendum ADR-012. |
| 2026-07-22 | 1.7 | Fase 13 cerrada (`62fe327`). Roadmap reordenado (deuda técnica primero, decisión del usuario): Fase 14 Calidad de Retrieval (DT-022/020/023, detallada + prompt de arranque), Fase 15 Resiliencia y Costo (DT-021+T12.1/2), Fase 16 Presentación (DT-019+tablas), luego cron/multi-tenant/API. |
| 2026-07-23 | 2.4 | Fase 18 cerrada (`8c6b8c2`..`7dcd676`): T18.1 documentos globales cross-sector (es_global + reserva rag_global_reserve=2 + ingest_global.py; 594 chunks) ✅; T18.2 citación APA PDFs locales (format_chunks_with_meta + _apa_report sin rutas; 8 tests) ✅; T18.3 empresa_id temprano + reserva empresa (rag_empresa_reserve=2 + UI selector) ✅; T18.4 build_emis_index.py + multi-sector jsonb_exists (DT-034 pendiente lote completo) ✅; T18.5 renumber_subheadings + chain_05 corregido (6 tests) ✅; T18.6 E2E Alpina S.A.S. ✅. 305 tests fast, ruff 0. DT-031/032/033 cerrados. Addendum ADR-012 Fase 18. |
| 2026-07-23 | 2.5 | Post-Fase 18: análisis comparativo informes Alpina (mañana vs Fase 18). Diagnosticadas causas raíz DT-035 (Tavily basic + queries genéricas → Cap 2 vacío) y DT-036 (chunks globales sin filtro sectorial → Cap 3 off-topic). Decisiones HITL (Q4) aprobadas: 4 decisiones arquitectónicas documentadas en ADR-015. Roadmap reordenado: F19 Sprint A (DT-035+036) → F20 Coherencia (ex-F19) → F21 HITL Gap Auditor → F22 HITL Consistency. REGLAS_NEGOCIO.md +RN-011/012/013. |
| 2026-07-22 | 1.6 | Fase 13 en curso: T13.1 esquema (sector_gics/activo + PAPER_ACADEMICO) ✅, T13.2 PdfIngestor (documento_id + fuente_tipo pdf) ✅, T13.3 filtrado sectorial + cap por doc ✅, T13.4 panel Repositorio + DocumentoRepository ✅, T13.5 lote 25 PDFs ingestado (1746 chunks, 0 errores) ✅, T13.6 `_run_pdf` retirado (DT-017) ✅, T13.7 APA informe_compilado + evaluación 3 empresas ✅ (Fase 13: 3/0 sect/cross vs base 0-1/2-4; añadida reserva sectorial tras hallazgo de backlog web), T13.8 ADR-012 + hallazgos RepositorioRN ✅. 179 tests fast. DT-011/DT-017 cerrados. |
