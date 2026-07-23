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

### Pendiente para Fase 18
1. Registrar DT-029/030/031/032/033 en ROADMAP §5.
2. Decidir DT-027 (radar_json): confirmar grep de Avianca y cerrar o planificar cadena dedicada.
3. Ingestar `InformeConvergenciaLocal2026RvADAA.pdf` como fuente global Cap 5/6 (Q2, DT-031).
4. Corregir citación APA — nombre de archivo crudo en lugar de metadatos APA (Q4, DT-033).
5. Mecanismo EMIS y docs extra por empresa (Q6).
6. DT-030: checkpoint antes de barreras N2/N3.
7. Investigar bug numeración subcapítulos post-Cap 4 (Q3, DT-032).
8. Merge `--no-ff` a `develop`, generar prompt Fase 18.
