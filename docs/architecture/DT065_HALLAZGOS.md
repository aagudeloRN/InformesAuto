# DT-065 + Modularidad F1 + Robustez Gateway — Hallazgos (sesión 2026-08-03)

> Cierra la línea de trabajo del 2026-08-03 (rama `develop`). Sucesor de `DT064_HALLAZGOS.md`.
> Roadmap vivo: `ROADMAP.md`. Estado/decisiones: memoria `project_roadmap_ago2026`.

## DT-065 — La data local alimenta los campos de ficha + fix del bucle de veneno

**Contexto:** el E2E de Alpina (DT-064) dejó las fichas 2.1 vacías. Diagnóstico en dos hallazgos:

1. **La data local estructurada no alimentaba los campos de ficha.** StartIA (388) y EmpresasColombia
   (~98k) guardan `descripcion/actividad/verticales/tecnologias/ingresos` bajo claves que **no** son
   `FICHA_KEYS` → `list_ficha_atributos_by_sector` (T4) no las veía → tiers regional/startup vacíos.
   **Fix:** `SOURCE_ATTR_TO_FICHA` (alias 1:1 puro, RN-001) aplicado EN LECTURA (sin re-seed) +
   `ciudad→presencia_geografica`; `parse_startia` +TECNOLOGIAS/+VENTAS. **El pre-fill T4 ahora usa
   [globales + locales]** (antes solo globales). Validado: startups 4510 pasan de {} a 4 campos reales.
2. **Bucle de veneno del KB (bug desde DT-064).** El detector de ausencia del parser solo miraba
   `"dato no disponible"` (singular) → el PLURAL `"Datos no disponibles…"` y variantes pasaban → T3 las
   persistía como HECHO → el pre-fill se las devolvía al prompt → el modelo las reproducía → se
   re-persistían. **Degrada las tablas corrida-tras-corrida.** **Fix:** `_es_valor_util` por prefijo
   anclado (conserva parciales útiles como "B2B (Precios: No disponible)") + **purga de 189 atributos**.
3. **Pre-warm de globales por lotes:** arreglado `descubrir_globales_llm.py` (roto por la firma de
   DT-063) + `--ddg-only` (no gasta Tavily) + estado siempre candidato. Se decidió NO correr la siembra
   genérica en el piloto (redundante con la discovery del E2E + riesgo de mezcla); mecanismo listo.

## Modularidad Fase 1 — Caché durable por capítulo (keep-best + fallback)

La regresión del Cap 1 (salió casi vacío por variabilidad del modelo free, sin fallback) motivó reusar
la infra de checkpoint (DT-030). `domain/kb/completitud.py` (`score_capitulo` + `elegir_mejor`) +
`checkpoint_hooks.commit_best`: persiste el capítulo más completo (un degradado no pisa uno bueno) y
usa el cacheado si el fresco está **claramente degradado** (ratio 0.6). El caché ya NO se borra al
terminar (durable por `(empresa, ciiu)`); `--refresh` invalida, `--no-cache` desactiva. Invariante:
sin flags, comportamiento previo.

## Robustez del gateway LLM — guard None + Gemini síntesis + fallback

**Causa raíz de crashes** (logs OpenRouter): `nvidia/nemotron:free` es proveedor único; se degradó →
`content=None` (crasheaba `AIMessage`) y `finish_reason="length"` (~25.9k tokens sin parar). El gateway
no blindaba ninguno ni mandaba `max_tokens`.

- **Guard:** `content` None/vacío o `finish_reason="length"` → `EmptyGenerationError` (dentro del
  `@retry`) → `ResilientChatModel` cae al fallback; si todos agotan, **degrada a `""`** (Fase 1 cae al
  caché). + `max_tokens` 32k (red alta, no cap que trunque — las síntesis largas legítimas pasan; el
  discriminador es `finish_reason`, no el nº de tokens).
- **Provider por tier** (ADR-002, todo en `.env`): `_provider_base_and_key` (openrouter|gemini); Gemini
  reusa el mismo cliente HTTP (endpoint OpenAI-compat). **Síntesis = Gemini + fallback `openrouter/free`**
  (cadena dedicada; reserva la cuota de Gemini para los pocos llamados de Cap 5/6/Resumen).
- **Modelo:** `gemini-2.5-flash` tiene 20 RPD → se usa **`gemini-3.5-flash-lite` (500 RPD)**.

**E2E de validación (Alpina 1040, 2026-08-03, `output/alpina_gemini.docx`):** EXIT=0, **0 crashes**;
Gemini sirvió la síntesis incl. Resumen `in=22.658 tok` sin desbocarse; **Cap 1 completo** (9
subsecciones, regresión curada); 2.1.1 = 8 globales food, **0 tabaco/cerveza** (los "Tabaco" son
etiquetas CIIU de locales). Deuda: costo $0 = `_PRICING` sin Gemini (**DT-040**).

## Consolidación de documentación
Auto-memory 54→14 archivos (índice slim, numeración DT, digest `project_historial_fases`). Repo: nuevo
`ROADMAP.md` canónico (supersede roadmaps regados), `ROADMAP_FASE9+.md` congelado como tracker DT
detallado, FASE*_HALLAZGOS unificados en `docs/decisions/`, efímeros a `docs/decisions/archive/`. Plan
para cerrar la doc completa en `ROADMAP.md` §"Documentación — cómo continuar".

## Gate
ruff 0 (src/ tests/), 599 fast tests. Commits en `develop`: DT-065 (c9b8bbb, 84680ba, c89d025, b739269),
Fase 1 (e87dd6a), gateway (4cf9ac1), docs (785f79b, 8abd938).
