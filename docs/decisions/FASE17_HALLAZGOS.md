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

| Empresa | Modelo | radar_json emitido | parseable | n_competidores | GICS | tiempo | refs |
|---------|--------|--------------------|-----------|----------------|------|--------|------|
| Nestlé Colombia | qwen3:8b | ✅ | ✅ | 8 | 3020 | — | — |
| EPM | resilient/qwen3:8b | ⚠️ no capturado | — | — | 5510 | (abortó) | — |

**Estado:** N útil = 1 (Nestlé). La corrida de EPM abortó en Cap 6 por un incidente de red
(§6) **antes** de llegar a `_run_n3`, donde vive la instrumentación del radar. El `radar_json`
se genera en Cap 2 (que sí completó) pero solo se observa/usa en el ensamblado, que no se
alcanzó. **DT-027 sigue 🟡** — faltan corridas completas.

**Decisión DT-027:** pendiente. Mantener 🟡 hasta tener N≥5 corridas **completas**.

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

## 7. Curso de acción para mañana (arranque de la próxima sesión)

1. **Commitear lo verde de hoy** (si no se hizo): T17.1 (contadores caché), T17.4 (Open Sans),
   instrumentación radar/GICS, fix E501 en `models/__init__.py`. Rama
   `feature/fase17-instrumentacion`. Gate ya verde (280 tests, ruff 0).
2. **Implementar DT-029** (resiliencia red transitoria) — es el bloqueante real de las corridas
   E2E. Sin esto, cada corrida larga tiene alta probabilidad de morir en tier free.
3. **Re-correr EPM completa** + 3 empresas más (Alpina, Bancolombia, Avianca) para cerrar T17.2
   (N≥5 completas) y adjuntar el radar real de EPM.
4. **Registrar DT-029 y DT-030** en ROADMAP §5. Evaluar DT-030 como Fase 18 (checkpoint/reanudar)
   y reordenar el roadmap posterior.
5. Investigar los **615 s de Cap 1** (retrieval web lento) — opcional, no bloquea.
6. Cerrar Fase 17: actualizar ROADMAP §4/§5/§8, commit `docs(fase17)`, merge `--no-ff` a
   `develop`, generar prompt Fase 18.
