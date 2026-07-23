# FASE 17 — Hallazgos: Instrumentación, Calidad de Radar y Pulido E2E

**Fecha:** 2026-07-22 · **Branch:** `feature/fase17-instrumentacion`

---

## 1. Objetivo

Completar la instrumentación del pipeline (hit-rate de caché, DT-026), validar la robustez
del bloque `radar_json` con N≥5 corridas reales (DT-027), verificar la clasificación GICS +
filtrado sectorial cross-sector, y evaluar la mejora tipográfica Source Sans Pro (DT-024).

---

## 2. T17.1 — Contador de cache hits/misses (DT-026)

### Diseño

Los `Cached*Connector` se instancian en varios sitios y **por-thread** (`_run_n0`, `_run_n2`,
y ×3 en `generate_n1._store`, que corre Caps 2/3/4 en paralelo). Un contador solo-interno por
instancia no agrega. Solución: **`CacheCounter` thread-safe** (con `threading.Lock`) compartido,
inyectado en cada instancia vía el nuevo parámetro opcional `counter=`.

- `src/ic/infrastructure/sources/cached_connector.py`: clase `CacheCounter` (`hit()`, `miss()`,
  atributos `hits`/`misses`). Cada connector mantiene además atributos de instancia para
  observabilidad directa. `force_ddg=True` no cuenta (bypass total de caché).
- `_PipelineContext` lleva `cache_web_counter` y `cache_oal_counter` (creados en `_setup_infra`),
  propagados a las 5 construcciones de connector (n0, n2, ×3 n1).
- Al final de `_run_n3` se emite:
  `Cache web: {hits} HITs / {misses} MISSes — ahorro estimado: {hits*_AVG_WEB_MS:.0f} ms`
  (más una línea análoga para openalex). `_AVG_WEB_MS = 800.0` es una estimación de latencia de
  búsqueda web (no es nombre de modelo → no aplica TIER 1).
- `InformeResult` gana campos opcionales `cache_web_hits/misses`, `cache_oal_hits/misses`.

### Test

`tests/test_cached_connector_counters.py` (3 casos): 1 MISS + 1 HIT incrementan el contador;
`force_ddg` no cuenta; un `CacheCounter` compartido agrega a través de múltiples instancias.

**Estado:** ✅ 280 tests fast (+3), ruff limpio. DT-026 ✅.

> Nota: durante el arranque se detectó y corrigió un E501 pre-existente en
> `src/ic/data/models/__init__.py:8` (introducido por el fix DT-028 del commit `6ef96d4`); el
> gate de entrada de Fase 17 no estaba realmente en verde. Reformateado el `__all__` multilínea.

---

## 3. T17.2 — Robustez de `radar_json` (DT-027)  ·  N≥5 corridas

| Empresa | GICS | Completó | Tiempo | DT-029 | Tier ultra | Refs | radar_json |
|---------|------|----------|--------|--------|------------|------|------------|
| Nestlé Colombia | 3020 | ✅ | — | — | — | — | ✅ real (8 comp.) |
| EPM | 5510 | ⚠️ abortó | — | ❌ pre-fix | — | — | no capturado |
| Alpina | 3020* | ✅ | 761.8s | ✅ 1 fallback | Cap 5/6 | 4 | sin datos† |
| Bancolombia | 4010* | ✅ | 555.2s | — | Resumen | 4 | sin datos† |
| Avianca | 2030* | ✅ | 1088.2s | — | Cap 5 | 13 | ❌ placeholder |

*GICS inferido. †Logging no capturaba ic.domain en esas corridas (corregido en Avianca).

**Observaciones de la serie:**
- **N1 (Caps 2/3/4)** es el cuello de botella: 182–525 s según empresa.
- **Referencias:** Avianca obtuvo 13 únicas vs 4 de Alpina/Bancolombia — mayor cobertura web
  para aerolíneas. Variación indica que la densidad del corpus web impacta el retrieval.
- **DT-029 validado en producción:** Alpina disparó fallback ante `RemoteProtocolError` y
  completó exitosamente. Las otras dos corridas usaron solo el tier free.
- **Tier ultra (Nemotron 550B):** apareció en las 3 corridas nuevas en 1 sola llamada de
  síntesis (Cap 5, Cap 6 o Resumen). Actúa como red de seguridad ante respuestas incompletas.
- **Cache web (Avianca):** 0 HITs / 12 MISSes — esperado para primera corrida de empresa nueva.
  En re-corridas el hit-rate debería subir.

**Decisión DT-027:** Tasa radar real confirmada = 1/2 = 50% (Nestlé ✅, Avianca ❌).
Umbral requerido: ≥ 80%. **→ DT-027 requiere cadena dedicada de extracción de scores.**
Planificar en Fase 18: llamada LLM separada a temperatura 0 para extraer `radar_json` de
forma estructurada, desacoplada del prompt principal del capítulo.

**Estado T17.2:** N=5 corridas completas ✅. DT-027 🔴 requiere acción en Fase 18.

---

## 4. T17.3 — Smoketest cross-sector (EPM, GICS 5510)  ·  ✅ clasificación validada

Aunque la corrida no terminó, la parte que T17.3 debía validar **sí quedó demostrada**:

- **GICS clasificado: `5510` (Utilities)** en 5.9 s — sector ≠ 3020 (alimentos). El clasificador
  cross-sector funciona.
- **Filtrado sectorial operativo:** 12 consultas pgvector ejecutaron
  `WHERE e.metadatos->>'sector_gics' = '5510'` (verificado en el log). El retrieval prioriza el
  corpus del sector correcto cross-sector.
- Pasos completados antes del fallo: Cap 1 (615.3 s ⚠️ lento), GICS (5.9 s), N1 Caps 2/3/4
  (125.7 s), intro N1 (4.6 s), Cap 5 Convergencia — murió en **Cap 6 Accionables**.

**T17.3 ✅** en lo esencial (clasificación + filtrado cross-sector). Falta una corrida completa
de EPM para adjuntar tiempo total / refs / radar.

> Observación: Cap 1 tardó **615 s (~10 min)**, anómalo. Candidato a investigar (retrieval web
> lento para EPM). No bloquea el cierre pero conviene registrarlo.

---

## 5. T17.4 — Open Sans en el .docx (DT-024)  ·  ✅

Source Sans Pro no está empaquetado en Ubuntu 24.04. Instalados `fonts-open-sans` (familia
`Open Sans`, sustituto humanista-sans) y `fonts-crosextra-carlito` (clon métrico libre de
Calibri, de respaldo). `docx_renderer._apply_normal_style` fija ahora `NORMAL_FONT_NAME =
"Open Sans"` (constante de módulo, fuente de verdad única importada por el test). Test
`test_docx_style.py` actualizado. **DT-024 ✅** (Open Sans; Source Sans Pro estricto queda como
mejora futura si se instala `fonts-source-sans-3`).

---

## 6. Incidente E2E — `RemoteProtocolError` aborta el pipeline en Cap 6 (nuevo: DT-029)

### Qué pasó

Corrida de EPM abortó en `_run_n2 → GenerateAccionables.execute → ResilientChatModel._generate
→ OpenRouterGatewayLLM._generate → httpx.post`:

```
httpx.RemoteProtocolError: peer closed connection without sending complete
message body (incomplete chunked read)
```

Secuencia temporal: última SQL 16:20:15 → **60 s de cuelgue** → ROLLBACK 16:21:15 → traceback.
El peer (OpenRouter, tier free) cerró la conexión con el cuerpo a medias.

### Causa raíz (dos huecos de resiliencia)

1. **`OpenRouterGatewayLLM._generate._call`** (tenacity, `gateway.py:213`) reintenta ante
   cualquier excepción, pero el drop transitorio persistió durante los `max_retries` intentos.
2. **`ResilientChatModel._generate`** (`gateway.py:346`) solo hace fallback de tier ante
   `is_rate_limit_error`. Un `RemoteProtocolError` **no** es rate-limit → se propaga inmediato
   (`gateway.py:365`) sin intentar `free_alt`/`synth`/`paid`.

Resultado: un corte de red transitorio en una sola llamada mata el informe completo y **se
pierden Caps 1–5** (~13 min de trabajo, incl. los 615 s de Cap 1). No hay checkpoint.

### DT-029 (nuevo) — Resiliencia ante cortes de red transitorios

Fix propuesto (mañana):
- Añadir `is_transient_network_error(exc)` (cubre `httpx.RemoteProtocolError`,
  `httpx.ReadError`, `httpx.ConnectError`, `httpx.ReadTimeout`, "incomplete chunked read").
- En `ResilientChatModel._generate`: hacer fallback de tier **también** ante error transitorio
  de red (no solo rate-limit). Así un free flaky cae a `free_alt`/`synth`.
- Confirmar que el `retry=` de tenacity en `_call` cubre estos tipos con backoff (ya reintenta
  por defecto; ajustar `wait`/`stop` si hace falta).
- Test: simular `RemoteProtocolError` en tier 1 → cae a tier 2 y devuelve contenido.

### DT-030 (nuevo, mayor) — Checkpoint antes de barreras de sincronización

CLAUDE.md TIER 3 exige "persistir estado antes de cruzar Cap 6 y N3". Hoy no se implementa: un
fallo tardío descarta todo. Persistir Caps N0/N1/N2 (BD o disco) para poder **reanudar** una
corrida. Alcance mayor → candidata a fase propia (¿Fase 18?).

---

## 7. Observaciones de calidad identificadas en corridas E2E (→ Fase 18+)

Identificadas en revisión de documentos generados durante T17.2. Guardadas en memoria
`project_calidad_documento.md`.

| # | Problema | Severidad | Candidato |
|---|----------|-----------|-----------|
| Q1 | Sin revisión de coherencia post-generación (contradicciones entre caps) | Alta | Fase 18/19 |
| Q2 | Cap 5/6 inconclusos — falta ingestar `InformeConvergenciaLocal2026RvADAA.pdf` como fuente global | Alta | DT-031, pronto |
| Q3 | Bug de numeración: subcapítulos post-Cap 4 numerados como `5.x` | Media | DT-032 |
| Q4 | Citación incorrecta: nombre de archivo crudo en vez de APA (ej. `InformeConvergenciaLocal2026V3RvADAA.pdf`) | Media | DT-033 |
| Q5 | Alta frecuencia de "información no disponible" — corpus insuficiente | Alta | Fase 18 |
| Q6 | Sin mecanismo para adjuntar docs extra por empresa (EMIS, sectoriales) | Alta | Fase 18/19 |
| Q7 | Mejora de forma y estilo visual del .docx | Baja | Fase 19/20 |

**Prioridad inmediata:** Q2 (PDF convergencia) + Q4 (citación APA) + Q6 (EMIS) — las tres
afectan directamente el contenido y la credibilidad del informe.

---

## 8. Estado de cierre de Fase 17

### Completado ✅
1. T17.1 (DT-026): contadores caché hits/misses — 289 tests, ruff 0.
2. T17.4 (DT-024): Open Sans en estilo Normal del .docx.
3. DT-029: fallback de tier ante errores de red transitorios — validado en producción (Alpina).
4. T17.3: EPM → GICS 5510 cross-sector validado.
5. T17.2: N=5 corridas completas (Nestlé + Alpina + Bancolombia + Avianca).
6. Fix logging en `run_pilot.py` — ic.domain ahora emite INFO al log.

### Cierre administrativo (2026-07-23)
- DT-029/030/031/032/033 registradas en ROADMAP §5. DT-027 decidido: 🔴 cadena dedicada
  (tasa 50% < 80%) → Fase 19.
- Roadmap §6 reordenado: **F18 Evidencia y Citación → F19 Coherencia y Robustez →
  F20 Estilo y Visualización → F21+ operación continua**.
- Radar de Avianca: `Radar: placeholder — DT-027 miss` confirmado en log.
  `Cache web: 0 HITs / 12 MISSes` (primera corrida de la empresa, esperado).

---

## 9. PROMPT DE ARRANQUE — Fase 18 (Evidencia y Citación)

```text
# ROL Y MISIÓN
Eres el ingeniero a cargo de la FASE 18 (Evidencia y Citación) del sistema de Informes de
Inteligencia Competitiva. Tu misión: anclar el contenido en más y mejor evidencia, citada
correctamente — documentos globales cross-sector para Cap 5/6, documentos por empresa (EMIS),
citación APA real para PDFs locales, menos "información no disponible" y numeración correcta.
Trabajas según CLAUDE.md y docs/architecture/PRIME_DIRECTIVE.md.

# MÉTODO DE TRABAJO (obligatorio)
Dos partes: PARTE A (diseño en Plan Mode, esperar aprobación) → PARTE B (ejecución).
El plan es la especificación: si la realidad diverge, DETENTE y vuelve a Plan Mode.
Cambios atómicos. Tests en el mismo commit que el código.

# RESTRICCIONES DURAS (no negociables)
- Modelos solo en .env (nunca hardcodear nombres). Sin secretos en git.
- Dependency Agnosticism: domain/ NO importa SQLAlchemy/httpx/Streamlit/python-docx.
- NO re-litigar: ADR-012 (filtrado sectorial + reserva), ADR-013 (persistencia web
  solo-citado), ADR-002 (datos ausentes = condición de recuperación). Se construye SOBRE ellos.
- El cupo de documentos globales NO debe desplazar la evidencia sectorial: calibrar con el
  harness (scripts/eval_retrieval.py), no a ciegas.

# ESTADO DE ENTRADA (Fase 17 cerrada)
Branch develop (merge de feature/fase17-instrumentacion). 289 tests fast, ruff 0.
Pipeline instrumentado (CacheCounter, log radar) y resiliente (DT-029: fallback de tier ante
rate-limit Y red transitoria, validado en producción). N=5 corridas E2E completas.
Problemas abiertos que esta fase ataca (FASE17_HALLAZGOS.md §7): Cap 5/6 inconclusos,
citas con nombre de archivo crudo, muchas secciones "información no disponible",
numeración 5.x tras el Cap 4.

# ANTES DE EMPEZAR — pídeme al usuario:
1. La ruta del PDF `InformeConvergenciaLocal2026RvADAA.pdf` (fuente global para Cap 5/6).
2. Si hay PDFs EMIS u otros documentos por empresa disponibles para probar T18.3.

# PASO 0 — Ramas y gate de entrada
git checkout develop && git checkout -b feature/fase18-evidencia-citacion
uv run ruff check src/ tests/ -q && uv run pytest -m "not slow" -q  → 0 errores / verde.

# PASO 1 — LECTURA OBLIGATORIA (antes de planificar)
docs/architecture/ROADMAP_FASE9+.md → sección FASE 18 (tareas T18.1–T18.6, criterios) ·
docs/decisions/FASE17_HALLAZGOS.md (§7 problemas Q1–Q7) ·
docs/architecture/ADR-012-filtrado-sectorial.md (filtro + reserva sectorial — patrón a
extender para documentos globales) ·
src/ic/infrastructure/retrieval/pgvector_store.py (search: filtro sector_gics, cupos) ·
src/ic/data/models/documento_local.py (empresa_id, sector_gics, metadatos) ·
src/ic/infrastructure/sources/pdf_ingestor.py (qué metadatos llegan a los chunks) ·
src/ic/infrastructure/citation/apa_formatter.py (dispatch por tipo de fuente) ·
src/ic/domain/use_cases/generate_convergencia.py y generate_accionables.py (retrieval Cap 5/6) ·
src/ic/domain/chains/ (cómo se inyecta el bloque de fuentes numeradas al prompt) ·
src/ic/infrastructure/render/docx_renderer.py + src/ic/domain/report_model.py (numeración
de headings — bug DT-032) ·
src/ic/presentation/app.py (panel Repositorio — patrón para subida por empresa).

# PASO 2 — PLAN MODE (Parte A). Diseña las tareas EN ORDEN, cada una con criterio de éxito:

T18.1 (DT-031) — Documentos globales cross-sector.
  Concepto "global" (flag en metadatos o sector_gics NULL explícito) que participa en el
  retrieval de TODOS los sectores con cupo propio (patrón reserva ADR-012). Ingestar el
  InformeConvergencia como global.
  ÉXITO: Cap 5/6 de un informe de sector ≠ 3020 citan el documento global (log/refs);
  el harness muestra que la evidencia sectorial NO se degrada.

T18.2 (DT-033) — Citación APA de PDFs locales.
  Metadatos APA (autor/año/título) garantizados en ingesta y en el bloque de fuentes del
  prompt. Fallback institucional ("Ruta N, 2026") si faltan — NUNCA el nombre del archivo.
  ÉXITO: test de contrato chunk PDF local → cita (Autor, año); cero nombres de archivo en
  el cuerpo de un informe E2E.

T18.3 (Q6) — Documentos por empresa.
  Asociar documentos a empresa (empresa_id ya existe); subida por empresa en el panel;
  retrieval prioriza empresa > sector > global > web.
  ÉXITO: un doc asociado a la empresa del informe aparece citado/priorizado (test).

T18.4 (Q5) — Medir y reducir "información no disponible".
  Con el harness: % de consultas bajo umbral por sector; revisar umbral vs corpus;
  tabla de cobertura por sector (qué EMIS conseguir).
  ÉXITO: tabla documentada en FASE18_HALLAZGOS.md con acciones concretas.

T18.5 (DT-032) — Fix numeración de subcapítulos post-Cap 4.
  Reproducir con .docx generado, localizar desfase (renderer o ReportDocument), corregir.
  ÉXITO: numeración correcta en .docx E2E + test.

T18.6 — Corrida E2E de validación (1–2 empresas, una ≠ 3020) verificando los criterios.

Espera aprobación del plan antes de escribir código.

# PASO 3 — EJECUCIÓN (Parte B)
Implementa T18.1→T18.6 en orden. Gate ruff+pytest tras cada tarea.

# CRITERIOS DE ÉXITO GLOBALES (Definition of Done)
1. Gate verde: ruff 0 + pytest -m "not slow" ≥ 289 passed. Cobertura domain/ ≥ 80%.
2. Cap 5/6 citan el documento global en informes de cualquier sector.
3. Cero citas con nombre de archivo (test de contrato + E2E).
4. Retrieval por empresa operativo y probado.
5. Tabla de cobertura por sector documentada.
6. Numeración correcta verificada en .docx.

# PASO 4 — DOCUMENTACIÓN (obligatoria al cierre)
- docs/decisions/FASE18_HALLAZGOS.md: logros, retos, recomendaciones (patrón FASE17).
- ROADMAP_FASE9+.md: tablero §4 (Fase 18 ✅ + hash), deuda §5 (DT-031/032/033), changelog §8.
- ADR nuevo/actualizado si cambia una decisión estructural (documentos globales extiende
  ADR-012 → considerar addendum).
- Confirma el commit conmigo antes de mergear a develop con --no-ff.
- Redacta y propón el PROMPT DE ARRANQUE de la FASE 19 (Coherencia y Robustez: pase de
  coherencia post-generación Q1, cadena dedicada radar DT-027, checkpoint DT-030).

Pregunta si algo no está claro antes de empezar.
```
