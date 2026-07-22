# FASE 16 — Hallazgos: Presentación del Contenido

**Fecha:** 2026-07-22 · **Branch:** `feature/fase16-presentacion` · **Commit:** `aadd99e`

---

## 1. Objetivo

Cerrar la brecha entre el pipeline funcional y un entregable visual profesional: cablear las
piezas de Fase 15 (caché y resiliencia) en el pipeline E2E, alimentar el radar chart con
datos reales del LLM, fijar el estilo tipográfico del .docx y asegurar que las fichas de
competidores se rendericen como tablas Word nativas.

---

## 2. T16.0 — Cableado E2E de Fase 15

### ResilientChatModel (T16.0-A)

`generate_informe._setup_infra` pasó de tres `build_api_llm(tier=...)` individuales a un
único `build_resilient_api_llm(settings, cost_tracker=tracker)`.

```python
# Antes (Fase 15)
api_llm      = build_api_llm(s, tier="free", cost_tracker=tracker)
api_llm_alt  = build_api_llm(s, tier="free_alt", ...)
api_llm_synth = build_api_llm(s, tier="synth", ...)

# Después (Fase 16)
resilient_llm = build_resilient_api_llm(s, cost_tracker=tracker)
# api_llm = api_llm_synth = resilient_llm; api_llm_alt = None
```

El `_PipelineContext` conserva los campos `api_llm` y `api_llm_synth` apuntando al mismo
modelo resiliente (mínimo cambio para evitar renombramiento en cascada). El fallback
`free→free_alt→synth→paid` opera internamente ante cualquier rate-limit.

### CachedWebConnector y CachedOpenAlexConnector (T16.0-B)

**Problema de thread-safety resuelto:** `Session` de SQLAlchemy no es thread-safe. Los Caps
2/3/4 se ejecutan en paralelo (`ThreadPoolExecutor`). Solución: cada thread crea su propia
instancia `Cached*Connector` con su propia `Session` (la que ya abría el helper `_store`).

```python
def _store(fn):
    with SessionLocal() as db:
        store = PGVectorStore(...)
        cached_web = CachedWebConnector(ctx.web, db, s)   # propio por thread
        cached_oal = CachedOpenAlexConnector(OpenAlexConnector(s), db, s)
        return fn(store, cached_web, cached_oal)
```

`ctx.web` se mantiene como `WebConnector` raw (base de los wrappers). Los caps N0 (Cap 1)
y N2 (Cap 5) abren su propia sesión al vuelo.

### Test de no-double-call

`tests/test_cached_pipeline.py`: verifica que dos búsquedas idénticas consecutivas llaman
al connector real exactamente 1 vez (la segunda usa el repo mock con payload cacheado).

---

## 3. T16.1 — Radar chart con datos reales del LLM (DT-019)

### Estrategia de extracción

El LLM emite un bloque delimitado `\`\`\`radar_json ... \`\`\`` al final de la respuesta del
Cap 2 (Benchmarking). `_extract_radar()` en `generate_benchmarking.py`:

1. Busca con regex `r"\`\`\`radar_json\s*(.*?)\`\`\`"` (re.DOTALL).
2. Si encuentra: parsea JSON, limpia el bloque del texto, devuelve `(texto_limpio, data)`.
3. Si no encuentra o JSON inválido: devuelve `(texto_limpio, None)`.

`CapBenchmarking` tiene el nuevo campo `radar_data: dict | None` (no rompe tests existentes
por ser opcional con default `None`).

En `generate_informe._run_n3`:
```python
rd = ctx.cap.radar_data
if rd and rd.get("competidores") and rd.get("dimensions"):
    generate_radar_chart(rd["competidores"], rd["dimensions"], chart_path, title=...)
else:
    generate_placeholder_radar(chart_path, ctx.params.empresa)  # fallback obligatorio
```

### Prompt engineering

`USER_PROMPT_03` cierra con instrucción explícita: emitir el bloque `\`\`\`radar_json` con
4–8 competidores de la sección 2.1, scores 1–5 en las 5 dimensiones estándar.

Riesgo conocido: los LLMs free-tier pueden omitir o malformar el bloque. El fallback
`generate_placeholder_radar` garantiza que el informe nunca aborte ni quede sin imagen.

---

## 4. T16.2 — Estilo Normal del .docx (DT-024)

`DocxRenderer.render()` llama a `_apply_normal_style(word_doc)` antes de `_add_footer`.
Propiedades fijadas:

| Propiedad | Valor |
|-----------|-------|
| Fuente | Calibri (Source Sans Pro como mejora futura si se instala en el servidor) |
| Tamaño | 11 pt |
| Alineación | Justificada |
| Interlineado | Múltiple 1,16 |
| Espacio después | 8 pt |
| Control viudas/huérfanas | Activado |

Tests en `tests/test_docx_style.py` verifican cada propiedad abriendo el .docx resultante
con python-docx y leyendo `styles["Normal"]`.

**Nota ADR:** Source Sans Pro queda como mejora futura (no está disponible en el entorno WSL
sin instalación adicional). Calibri es el fallback documentado.

---

## 5. T16.3 — Tablas Word para fichas de competidores

### Diagnóstico

La infraestructura ya estaba completa desde Fase 11:
- `markdown_parser.parse_markdown` detecta `|...|` líneas y genera `TableBlock`.
- `DocxRenderer._render_table` emite tablas Word nativas con `Table Grid`.
- `assembler.py` llama `parse_markdown(cap_benchmarking.texto)`.

El riesgo era que el LLM no produjera tablas en formato markdown pipe. Se resolvió
añadiendo instrucción explícita en `SYSTEM_PROMPT_03`:

```
FORMATO DE FICHAS (sección 2.1): cada ficha debe ser una tabla markdown con pipes.
Ejemplo: | Campo | Valor | / |-------|-------| / | Nombre + País | Nestlé — Suiza |
```

Test `test_docx_table_block_rendered` confirma el flujo completo:
`TableBlock` → `_render_table` → `.docx` con ≥1 tabla Word visible.

---

## 6. Retos encontrados

1. **Thread-safety de Session:** El diseño inicial del plan indicaba `ctx.web` como
   `CachedWebConnector` compartido. En ejecución paralela, SQLAlchemy lanza errores de
   concurrencia. Solución: instanciar el wrapper cached dentro del contexto de cada thread.

2. **E501 en prompt con JSON de ejemplo:** El JSON inline del `USER_PROMPT_03` superaba
   los 100 caracteres. Solución: dividir la cadena larga en dos literales concatenados.

3. **`--bench --warm` no ejecutable en esta sesión:** Ollama requiere modelos descargados
   y PostgreSQL activo. La medición real queda pendiente de ejecución manual (ver §7).

---

## 7. Recomendaciones / follow-ups

- **Medición real `--bench --warm`**: ejecutar `uv run python scripts/eval_retrieval.py
  --bench --warm` con Ollama activo y actualizar `FASE15_HALLAZGOS.md §2` con datos reales.
- **Source Sans Pro**: si se instala en el servidor, cambiar `font.name = "Calibri"` a
  `"Source Sans Pro"` en `docx_renderer._apply_normal_style`.
- **Hit-rate de caché**: añadir contador de hits/misses en `CachedWebConnector` y emitirlo
  en el log de cierre del informe (aún sin implementar).
- **Validación robustez radar_json**: probar con modelos free-tier reales para ver qué
  porcentaje de corridas emiten el bloque. Si el hit-rate < 50%, considerar llamada
  dedicada de extracción de scores (cadena separada).
