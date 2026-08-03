# 🗺️ ROADMAP — canónico

> **Roadmap vivo y ÚNICO** (consolidación 2026-08-03). Unidad de trabajo = **DT-NNN**; las "Fases"
> son historia. No es inmutable (a diferencia de los ADR).
>
> - **Historia detallada de fases y DT:** `docs/decisions/FASEN_HALLAZGOS.md` + el tracker
>   pormenorizado `ROADMAP_FASE9+.md` (congelado ~F22/DT-064; tabla completa de DT-004..064).
> - **Estado/decisiones activas:** memoria `project_roadmap_ago2026` + `project_historial_fases`.

## Estado actual (2026-08-03)

Rama `develop`. Últimos hitos (esta línea de trabajo, DT-050→):
- **Competidores/KB** (cerrado): DT-050 (local EMIS/StartIA), DT-056 (KB entidades), DT-059 (auto-revisión),
  DT-061/062/063 (descubrimiento producto-driven, 0 tabaco/cerveza), DT-064 (fichas ancladas), DT-065
  (data local → campos de ficha + **fix del bucle de veneno**: parser de ausencia robusto + purga 189).
- **Modularidad Fase 1** (cerrado): caché durable por capítulo con keep-best + fallback (`commit_best`,
  `domain/kb/completitud.py`) → un capítulo degradado cae al cacheado bueno.
- **Robustez LLM** (cerrado, pendiente `.env`): guard `content=None`/`finish_reason` + `max_tokens` 32k;
  **síntesis por Gemini** (provider por tier) + fallback `openrouter/free`. Cambiar en `.env`
  `LLM_API_SYNTH_MODEL=gemini-3.5-flash-lite` (500 RPD; 2.5-flash tenía 20). Ver
  `project_llm_robustez_modelos`.

## Pruebas pendientes (validaciones que faltan)
1. **E2E Gemini síntesis** (tras el cambio de `.env`): Cap 6/Resumen por Gemini, sin crash (exit 0).
2. **E2E Fase 1**: un capítulo degradado cae al cacheado bueno (fallback); re-corrida reusa.
3. **E2E DT-064/065 con KB limpio**: Alpina 1040 + Emtelco full → fichas con datos reales, 0 veneno,
   0 cerveza/tabaco, tiers regional/startup pre-llenados por data local.
4. **Re-medir cobertura `domain/`** (base F19 = 69%).
5. **Fix bug** empresa focal en su propia tabla de competidores (excluir por nombre normalizado).

## Frentes abiertos (prioridad)
- **Frente Evidencia (DT-049 / DT-034):** el lote EMIS diverso (250 PDFs) está en disco pero **sin
  ingestar** → la calidad cae fuera del sector 3020. Es la palanca directa de diversidad de fuentes.
- **HITL (F24/F25):** captura/aprobación humana; depende de **DT-050b** (reconciliación EMIS↔NER por NIT).
- **Estilo/documento (F26):** coherencia, Cap 5/6, numeración, estilo.

## Deuda estructural (auditoría externa 2026-08-03 — `auditoria_arquitectura.md`)
Abierta desde F19, **agravada esta línea de trabajo**:
| DT | Deuda | Nota |
|----|-------|------|
| DT-037 | `gateway.py` >300L → paquete `infrastructure/llm/` | +200L esta sesión (guard/Gemini/fallback) |
| DT-038 | `presentation/app.py` accede a `data/` directo | 🔴 crítico; **prereq de HITL** |
| DT-039 | `generate_informe.py` 576L → extraer `generate_n3.py` | sigue creciendo |
| DT-040 | `_PRICING` hardcodea IDs; hook con puntos ciegos | Gemini sin trackear → **costo $0** |
| DT-041 | cobertura `domain/` 69% < 80% | re-medir (P0) |
| DT-050b | reconciliación EMIS↔NER por NIT + HITL | duplicados inertes hoy |

**Triaje sugerido:** DT-037/039/040 (agravados aquí) antes de más features; DT-038 antes de HITL.

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
