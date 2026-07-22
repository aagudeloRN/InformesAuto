# 🗺️ ROADMAP — Fase 9 en adelante

> **Propósito:** Plan de trabajo vivo y pormenorizado para llevar el sistema de Informes
> de Inteligencia Competitiva desde su estado actual (pipeline E2E funcional) hasta un
> producto **fiable, bien formateado y anclado en evidencia sectorial**, útil para empresas
> en Colombia.
>
> **Este documento se consulta y se actualiza en cada ejecución.** No es inmutable (a
> diferencia de los ADR). Cada fase se refina con los hallazgos de la anterior.

**Versión del roadmap:** 2.0 · **Creado:** 2026-07-21 · **Última actualización:** 2026-07-22

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
| DT-018 | Hook check-ruff.sh creado; settings.json pendiente registro manual | 9 | 🟡 script listo; settings.json actualizado en Fase 10 |
| DT-020 | Persistencia web indiscriminada: se ingesta todo lo buscado (usado o no). Objetivo: persistir **solo lo citado** (`chunks_usados`) + purgar el backlog no usado | 14 | ✅ ADR-013: session ingest + `promote_cited_web` + `sweep_stale` + purga única (backlog 1202→0); la purga subió la evidencia sectorial 3.20→3.68 chunks/consulta |
| DT-021 | Resiliencia OpenRouter free: rate-limits transitorios (`ResourceExhausted 32/32`) sin backoff/reintento dedicado | 15 | ✅ `is_rate_limit_error` + `ResilientChatModel` (free→free_alt→synth→paid); timeouts por tier. Ver `FASE15_HALLAZGOS.md` §4 |
| DT-022 | Reranking/afinado de retrieval: MMR completo + evaluación, `chunk_size` 500→1000, índice parcial/GIN sobre `metadatos->>'sector_gics'` | 14 | ✅ harness T14.1 (métricas propias); MMR medido y **revertido** (degrada mono-doc); `chunk_size` 1000/200 (neutral, se mantiene por eficiencia); índice **descartado** (SQL 15ms). Ver `FASE14_HALLAZGOS.md` + addendum ADR-012 |
| DT-023 | Clasificación GICS: `chain_02_gics` no emite el código (mitigado por `extract_gics_code`). Usar `Comparacion_GICS_CIIU.csv` (CIIU→GICS) para acotar/validar candidatos y endurecer el prompt para emitir "(GICS XXXX)" | 14 | ✅ `ciiu_gics.py` (CIIU→Sección→candidatos); `ClassifyGICS` acota+valida/corrige; `chain_02` endurecido; fallback por nombre conservado; ≥5 CIIU probados |
| DT-024 | Estilo Normal del documento no fijado: objetivo Source Sans Pro 11 pt, justificado, interlineado 1,16, espacio después 8 pt, control de viudas/huérfanas | 16 | ✅ `_apply_normal_style()` en `docx_renderer`; Calibri 11 pt (Source Sans Pro como mejora futura) |
| DT-025 | Medición real de latencia `--bench --warm`: los números en `FASE15_HALLAZGOS.md §2` son estimados teóricos (Ollama no disponible en sesión de Fase 15/16) | 17 | ✅ cold 1527.8 ms / warm 158.3 ms → 9.6× mejora. FASE15_HALLAZGOS §2 actualizado con datos reales (E2E post-Fase 16, 2026-07-22) |
| DT-026 | Hit-rate de caché no instrumentado: `CachedWebConnector`/`CachedOpenAlexConnector` no emiten métricas de hits/misses en el log del informe | 17 | 🟡 E2E 2ª corrida: 0 INSERTs en retrieval_cache → 100% HITs verificados por SQL. Contador explícito en log pendiente (Fase 17) |
| DT-027 | Hit-rate del bloque `radar_json` desconocido: no se sabe qué % de corridas con modelos free-tier emiten el JSON parseable. Si < 50%, considerar cadena dedicada de extracción de scores | 17 | 🟡 1ª corrida real con qwen3:8b: bloque emitido y parseable (8 competidores). N=1. Continuar midiendo; decisión de cadena dedicada pendiente con N≥5 |
| DT-028 | `RetrievalCache` no importado en `models/__init__.py`: `create_schema.py` no creaba la tabla `retrieval_cache` (rompe arranque en BD vacía) | E2E post-16 | ✅ import añadido en `src/ic/data/models/__init__.py`. Fix en commit `e2e-post-fase16` |

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

## 6. Roadmap posterior (reordenado: deuda técnica primero — decisión 2026-07-22)

Orden acordado con el usuario: absorber la deuda técnica descubierta antes de features nuevas.
- **Fase 14** — Calidad de Retrieval y Evaluación (DT-022, DT-020, DT-023). MMR completo,
  evaluación RAGAS, `chunk_size` 500→1000, índice GIN sectorial, ciclo de vida de chunks web,
  endurecer prompt GICS. **Detallada abajo con prompt de arranque.**
- **Fase 15** — Resiliencia y Costo (DT-021 + T12.1/T12.2). Caché de retrieval, backoff/fallback
  de tier para rate-limits OpenRouter, control de presupuesto y **estrategia de embedding**
  (mayor palanca de latencia según Fase 14). **Detallada abajo con prompt de arranque.**
- **Fase 16** — Presentación del contenido (DT-019 + DT-024 + tablas). Radar con datos reales
  del LLM, tablas de benchmarking en Word, pulido de formato .docx/.pdf. **Criterio de
  aceptación del estilo Normal** (DT-024): Source Sans Pro 11 pt · justificado · interlineado
  múltiple 1,16 líneas · espacio después 8 pt · control de líneas viudas/huérfanas · estilo
  visible en la galería. Implementación vía plantilla `docx_template_path` y/o estilos en
  `infrastructure/render/docx_renderer.py` (ligado a DT-016).
- **Fase 17** — Actualización programada del corpus sectorial (cron de re-ingesta y frescura).
- **Fase 18** — Multi-tenant / control de acceso (si se ofrece a varias empresas).
- **Fase 19** — Exportación a portal web / API (FastAPI) además de Streamlit.

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

**ADRs vigentes:** ADR-001 … ADR-011 + **ADR-012** (filtrado sectorial en el retrieval y
ciclo de vida del corpus).

---

## 8. Changelog del roadmap

| Fecha | Versión | Cambio |
|-------|---------|--------|
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
| 2026-07-22 | 1.6 | Fase 13 en curso: T13.1 esquema (sector_gics/activo + PAPER_ACADEMICO) ✅, T13.2 PdfIngestor (documento_id + fuente_tipo pdf) ✅, T13.3 filtrado sectorial + cap por doc ✅, T13.4 panel Repositorio + DocumentoRepository ✅, T13.5 lote 25 PDFs ingestado (1746 chunks, 0 errores) ✅, T13.6 `_run_pdf` retirado (DT-017) ✅, T13.7 APA informe_compilado + evaluación 3 empresas ✅ (Fase 13: 3/0 sect/cross vs base 0-1/2-4; añadida reserva sectorial tras hallazgo de backlog web), T13.8 ADR-012 + hallazgos RepositorioRN ✅. 179 tests fast. DT-011/DT-017 cerrados. |
