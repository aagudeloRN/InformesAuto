# 🗺️ ROADMAP — Fase 9 en adelante

> **Propósito:** Plan de trabajo vivo y pormenorizado para llevar el sistema de Informes
> de Inteligencia Competitiva desde su estado actual (pipeline E2E funcional) hasta un
> producto **fiable, bien formateado y anclado en evidencia sectorial**, útil para empresas
> en Colombia.
>
> **Este documento se consulta y se actualiza en cada ejecución.** No es inmutable (a
> diferencia de los ADR). Cada fase se refina con los hallazgos de la anterior.

**Versión del roadmap:** 1.4 · **Creado:** 2026-07-21 · **Última actualización:** 2026-07-21

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
| 12 | Optimización de Operación | ⬜ | — | — | `FASE12_HALLAZGOS.md` |
| 13 | Repositorio Sectorial RAG | ⬜ | — | — | `FASE13_HALLAZGOS.md` |

> Cada fase, al cerrar, actualiza su fila (estado ✅, fecha, hash de commit) y marca sus
> tareas en la sección correspondiente.

---

## 5. Deuda técnica viva

Se arrastra y actualiza entre fases. (Fuente: `ARQUITECTURA.md` §5 + hallazgos.)

| ID | Descripción | Fase objetivo | Estado |
|----|-------------|---------------|--------|
| DT-004 | `generate_informe.py` ≥ 300 líneas (~400 L) | 12 | 🟡 separar en Fase 12 (T12.5) |
| DT-005 | E2E Cap5 con servicios reales (`test_convergencia_e2e.py`) | 9 | ✅ 165.87 s, verde |
| DT-009 | Gate ruff ✅; validación idioma (CJK) N1+ | 10 | ✅ CJK cerrado en todos los caps N1–N3 |
| DT-010 | CostTracker para Ollama (tiempo como proxy de tokens) | 12 | ⬜ |
| DT-011 | Ingesta de fuentes sectoriales / EMIS | 13 | ⬜ |
| DT-012 | Multi-empresa / cola + historial paginado | 12 | ⬜ |
| DT-015 | Citación APA 7 no fiel (sin sangría/cursiva) + sin cita inline trazable | 10 | ✅ APA 7 fiel (dispatch por tipo); cursiva→Fase 11; orphan checker operativo |
| DT-016 | Formato .docx pobre (sin tablas/imágenes/TOC/portada) + salida única | 11 | ✅ Cerrado — portada, TOC, tablas, figuras, PDF vía LibreOffice |
| DT-019 | Datos estructurados del LLM para radar chart real (actualmente placeholder) | 12 | ⬜ nuevo |
| DT-017 | Acoplamientos "piloto" (PDF hardcodeado en `_run_pdf`, footer NOEL) | 10 / 13 | 🟡 footer ✅ parametrizable; PDF hardcodeado→Fase 13 |
| DT-018 | Hook check-ruff.sh creado; settings.json pendiente registro manual | 9 | 🟡 script listo; settings.json actualizado en Fase 10 |

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
      (tabla en `informes_ic`) para no re-consultar en cada corrida.
- [ ] **T12.2** Resiliencia free-tier: timeouts/paralelismo por tier configurables; backoff
      explícito ante 429/rate-limit; métrica de latencia por cap.
- [ ] **T12.3** DT-010: registrar tiempo (y/o tokens estimados) como proxy de costo para
      llamadas Ollama en `HistorialInforme`.
- [ ] **T12.4** DT-012: cola / multi-empresa en la UI + historial paginado.
- [ ] **T12.5** *(si abierto de Fase 9)* separar `_run_n1` a módulo propio si `generate_informe.py`
      superó 300 líneas (DT-004).

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

# FASE 13 — Repositorio Sectorial RAG (26 sectores)

**Prioridad:** P1 (mayor palanca de calidad de evidencia) · **Estimación:** ~4–6 días · **Estado:** ⬜ Pendiente

### Objetivo
Integrar el **repositorio de vigilancias sectoriales de 26 sectores industriales** (PDFs)
como corpus curado del RAG, de modo que los informes se anclen en evidencia sectorial
específica para Colombia en vez de solo web genérica. Es la mayor palanca de **fiabilidad**
y el diferenciador comercial.

### Contexto / por qué
- La infraestructura ya existe: `PdfIngestor` (RN-010, ingesta por lotes anti-OOM), pgvector,
  doble vía RN-004. Falta curar, mapear a sector/GICS y **priorizar** ese corpus en el retrieval.
- El equipo tiene **otro proyecto con un sistema RAG "bastante bueno"**; en esta fase se
  estudia para incorporar elementos aprovechables (chunking, reranking, filtros, evaluación).
- Se limpia el acoplamiento del PDF hardcodeado en `_run_pdf` (DT-017) generalizándolo a
  "corpus sectorial".

### Lecturas requeridas al iniciar
- `docs/architecture/ROADMAP_FASE9+.md` → esta sección (Fase 13)
- `docs/architecture/ADR-001` (RAG propio), `ADR-003` (fuentes doble vía), `ADR-005` (retrieval)
- `docs/business-rules/REGLAS_NEGOCIO.md` (RN-004, RN-010)
- `src/ic/infrastructure/sources/pdf_ingestor.py`
- `src/ic/infrastructure/retrieval/pgvector_store.py`, `chunker.py`, `embedder.py`
- `src/ic/data/repositories/embedding_repo.py` (`search_similar`)
- `src/ic/shared/constants/gics_groups.py` (mapeo GICS existente)
- `src/ic/domain/use_cases/generate_informe.py` (`_run_pdf`, `_run_n1`, `_run_n2`)
- **Externo:** el proyecto RAG del equipo en **`~/Test/RepositorioRN`** + carpeta de PDFs
  sectoriales (el usuario la coloca al arrancar la fase) + CSV de equivalencia CIIU/GICS (§7-Q3)

### Tareas
- [ ] **T13.1** Estudiar el RAG del otro proyecto del equipo: documentar qué elementos vale la
      pena incorporar (chunking, reranking, filtros por metadatos, evaluación de retrieval).
      Registrar en un ADR si cambia el diseño de retrieval actual.
- [ ] **T13.2** Mapeo **sector → GICS/CIIU**: tabla en `shared/constants/` que asocie cada uno
      de los 26 sectores a su(s) grupo(s) GICS (reusa `gics_groups.py`).
- [ ] **T13.3** Ingesta curada de los 26 PDFs con `PdfIngestor`, metadata rica:
      `fuente_tipo="sectorial"`, `sector_codigo`, `año`, `fuente_nombre`, versión. Script/UI
      de gestión del corpus. Anti-duplicados SHA-256 ya existe.
- [ ] **T13.4** Retrieval con **prioridad sectorial**: tras GICS (Cap 2), seleccionar el/los
      dossier(s) del sector y hacer boost/filtrado de esos chunks en Caps 3/4/5. Extender
      `search_similar()` con filtro por `sector_codigo`.
- [ ] **T13.5** Generalizar `_run_pdf` (DT-017): de un PDF hardcodeado a "cargar corpus
      sectorial relevante según GICS".
- [ ] **T13.6** Citación de fuentes sectoriales en APA (coordina con Fase 10) + registro de
      vigencia/frescura del dossier.
- [ ] **T13.7** Evaluación: medir en 2–3 empresas si baja el % de "datos ausentes" y sube el
      nº de fuentes citadas frente a la línea base sin corpus sectorial.

### Entregables
- Corpus sectorial ingestado y consultable, con mapeo sector→GICS.
- Retrieval con prioridad sectorial + filtro por `sector_codigo`.
- Estudio del RAG del otro proyecto (doc/ADR) con elementos incorporados.
- `_run_pdf` generalizado (sin hardcodes).
- `docs/decisions/FASE13_HALLAZGOS.md` + posible ADR-012 (retrieval sectorial).

### Criterios de aceptación
1. Un informe de una empresa de sector X prioriza chunks del dossier de sector X (test/log).
2. Los 26 PDFs (o el subconjunto disponible) están ingestados con metadata correcta.
3. Comparación con línea base: mejora medible en cobertura de evidencia (T13.7).
4. `_run_pdf` ya no depende de un nombre de archivo hardcodeado.
5. Gate ruff + pytest verde. Tablero, deuda técnica y ADR actualizados.

### Riesgos
- Volumen: 26 PDFs pueden ser muchas páginas → ingesta por lotes y tiempos (RN-010). Puede
  requerir una corrida de ingesta larga fuera del pipeline de informe.
- El RAG del otro proyecto puede asumir infra distinta; incorporar solo lo compatible con
  ADR-001/005 (RAG propio pgvector local).
- Calidad heterogénea de los PDFs (OCR, tablas) → validar extracción de texto.

### PROMPT DE ARRANQUE — Fase 13
```text
Estás ejecutando la FASE 13 (Repositorio Sectorial RAG — 26 sectores) del roadmap del
sistema de Informes de Inteligencia Competitiva. Trabaja según CLAUDE.md y PRIME DIRECTIVE.

Antes de empezar, necesito de mí (el usuario) dos datos si no están en el roadmap: la ruta de
los 26 PDFs sectoriales y la ruta del proyecto RAG del equipo a estudiar. Pídemelos si faltan.

PASO 1 — LEE:
- docs/architecture/ROADMAP_FASE9+.md → sección "FASE 13"
- docs/decisions/FASE12_HALLAZGOS.md
- docs/architecture/ADR-001, ADR-003, ADR-005
- docs/business-rules/REGLAS_NEGOCIO.md (RN-004, RN-010)
- src/ic/infrastructure/sources/pdf_ingestor.py
- src/ic/infrastructure/retrieval/ (pgvector_store, chunker, embedder)
- src/ic/data/repositories/embedding_repo.py (search_similar)
- src/ic/shared/constants/gics_groups.py
- src/ic/domain/use_cases/generate_informe.py (_run_pdf, _run_n1/_run_n2)
- (externo) el proyecto RAG del equipo y la carpeta de los 26 PDFs

PASO 2 — Estudia el RAG del otro proyecto (T13.1) y documenta qué incorporar.

PASO 3 — Entra en Plan Mode. Propón: mapeo sector→GICS, esquema de metadata sectorial,
estrategia de ingesta, retrieval con prioridad sectorial, y generalización de _run_pdf.
Considera ADR-012. Espera aprobación.

PASO 4 — Ejecuta T13.2–T13.7. Ingesta el corpus (puede ser una corrida larga separada).

PASO 5 — Gate: ruff limpio + pytest -m "not slow" verde. Corre la evaluación T13.7 y reporta
la mejora frente a la línea base.

PASO 6 — Documenta en docs/decisions/FASE13_HALLAZGOS.md y, si aplica, ADR-012.

PASO 7 — Actualiza ROADMAP_FASE9+.md: tablero §4 (Fase 13), deuda técnica §5 (DT-011,
DT-017), lista de ADR, changelog §8. Marca tareas T13.x. Si surgen nuevas fases, añádelas.

Confirma el mensaje de commit conmigo. Pregunta si algo no está claro.
```

---

## 6. Roadmap posterior (candidatos, no planificados aún)

Se detallarán cuando toque, según hallazgos:
- **Fase 14** — Reranking y evaluación de retrieval (RAGAS o similar) sobre el corpus sectorial.
- **Fase 15** — Multi-tenant / control de acceso si el sistema se ofrece a varias empresas.
- **Fase 16** — Actualización programada del corpus sectorial (cron de re-ingesta y frescura).
- **Fase 17** — Exportación a portal web / API (FastAPI) además de Streamlit.

---

## 7. Decisiones abiertas / preguntas al humano

Se resuelven en la fase indicada (o antes si se puede).

- **Q1 (Fase 9) — Ramas y CI. ✅ RESUELTO (2026-07-21).** Se adopta el flujo GitHub del
  PRIME DIRECTIVE §4.3: `main` protegida, `develop` como base, una rama por fase. CI corre
  **solo local** (no hay remoto GitHub); se implementa como hook/script local en la Fase 9.
- **Q2 (Fase 11) — Motor de PDF. ✅ RESUELTO (2026-07-21).** LibreOffice headless
  (`/usr/bin/soffice`). Documentado en ADR-011.
- **Q3 (Fase 13) — Repositorio sectorial y RAG del equipo. 🟡 PARCIAL (2026-07-21).**
  - Proyecto RAG del equipo a estudiar: **`~/Test/RepositorioRN`**.
  - Carpeta con los PDFs sectoriales: **pendiente** (el usuario la colocará en el proyecto
    cuando arranque la Fase 13).
  - Equivalencia CIIU/GICS: **CSV pendiente** (el usuario lo aportará en la Fase 13).

---

## 8. Changelog del roadmap

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-07-21 | 1.0 | Creación del roadmap Fase 9–13 con prompts de arranque autocontenidos. |
| 2026-07-21 | 1.1 | Resueltas Q1 (flujo GitHub PRIME DIRECTIVE + CI local), Q3 parcial (RAG del equipo en `~/Test/RepositorioRN`). Añadido paso de rama por fase; prompt Fase 9 actualizado. |
| 2026-07-21 | 1.2 | Fase 9 cerrada: T9.1 ruff 0 errores ✅, T9.4 E2E 165.87 s ✅, T9.3 Makefile+ci.yml ✅, T9.2 check-ruff.sh ✅ (settings.json pendiente manual). DT-005 ✅, DT-018 🟡. |
| 2026-07-21 | 1.3 | Fase 10 cerrada: T10.1 CJK en 6 use cases ✅, T10.2 orphan checker + contexto con meta ✅, T10.3/T10.4 APA 7 fiel ✅, T10.5 panel fiabilidad JSONB ✅, T10.6 disclaimer parametrizable ✅. 137 tests, DT-009/015/017(parcial) cerrados. |
| 2026-07-21 | 1.4 | Fase 11 cerrada: T11.1 report_model ✅, T11.2 docx_renderer+assembler refactor ✅, T11.3 markdown_parser+TableBlock ✅, T11.4 radar chart ✅, T11.5 PDF LibreOffice ✅, T11.7 callouts ✅. 162 tests fast, ADR-011 creado, DT-016 cerrado, DT-019 nuevo. Q2 resuelta. |
