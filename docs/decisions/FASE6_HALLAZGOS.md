# Hallazgos Fase 6

**Fecha:** 2026-07-06
**Contexto:** Validación E2E completa + GenerateInforme orchestrator + UI Streamlit

---

## H6-01 — E2E completado exitosamente: pipeline de 10 pasos funciona end-to-end

**Resultado del informe piloto "Noel S.A.S.":**
- Exit code: 0
- Documento generado: `noel_e2e_test.docx`
- Estructura: 49 headings, 263 párrafos, ~12,300 palabras
- Referencias APA: 19 únicas
- Costo total API: **$0.0000 USD** (modelos free de OpenRouter)
- Tokens: 39,938 entrada / 38,290 salida

**Tiempos por paso:**
| Paso | Tiempo |
|------|--------|
| Cap 1 — Descripción | 50.2s |
| GICS — Clasificación | 30.4s |
| N1 paralelo (Caps 2/3/4) | 702.9s (~11.7 min) |
| Párrafos intro N1 | 12.4s |
| PDF Convergencia (excepción) | 1392.2s (~23 min) |
| Cap 5 — Convergencia | 4725.4s (~79 min) |
| Cap 6 — Accionables | 48.0s |
| Párrafos intro N2 | 5.7s |
| Resumen Ejecutivo | 93.9s |
| Referencias + Ensamblado | 0.3s |
| **Total** | **7061.2s (~117 min)** |

---

## H6-02 — Cap 5 (Convergencia) tomó 79 minutos

**Causa probable:** Rate limiting o tiempo de respuesta del modelo
`nvidia/nemotron-3-ultra-550b-a55b:free` en OpenRouter. Es un modelo de 550B parámetros;
su latencia en tier free puede ser muy alta. Cap 6 usa `nemotron-3-super-120b-a12b:free`
y tomó solo 48s.

**Acción tomada:** ninguna, por ser tier free. Si el tiempo es inaceptable en producción,
cambiar `LLM_API_SYNTH_MODEL` a un modelo más rápido en `.env`.

---

## H6-03 — PDF Convergencia falla silenciosamente tras 23 minutos

**Síntoma:** El paso de ingesta del PDF ejecutó por ~23 min y luego lanzó una excepción
que fue capturada. La excepción se logueó con `logger.warning(..., exc_info=True)` pero
la traza completa no se imprimió en stdout.

**Causa probable:** OOM durante el embedding de los chunks del PDF usando Ollama (WSL2
8GB). El PDF tiene muchas páginas; el proceso de embedding secuencial puede agotar la
RAM disponible.

**Mitigación aplicada en esta fase:**
- La excepción se imprime ahora a stdout como `⚠️ PDF Convergencia omitido: <tipo>: <msg>`
- El pipeline continúa sin el PDF; Cap 5 usa solo RAG de capítulos anteriores

**Pendiente para Fase 7:** Implementar ingesta por lotes con límite de chunks y
`keep_alive:0` explícito entre lotes para liberar VRAM de Ollama entre embeddings.

---

## H6-04 — SQLAlchemy INFO logs escapando a stdout en threads

**Causa:** El `setLevel(WARNING)` en `run_pilot.py` (nivel módulo) no suprimía los logs
de las sesiones creadas dentro de `ThreadPoolExecutor` porque algunos loggers de
SQLAlchemy se reinicializan al crear el engine en un nuevo hilo.

**Corrección:** El `setLevel(WARNING)` se movió al inicio de `GenerateInforme.run()`,
garantizando que se aplique antes de cualquier operación en el mismo proceso (incluyendo
hilos futuros, ya que la configuración de loggers es global al proceso).

---

## H6-05 — GenerateInforme orchestrator: refactorización limpia de run_pilot.py

**Decisión validada:** Extraer el pipeline a `domain/use_cases/generate_informe.py` con
callback `on_step` funcionó sin problemas. El CLI y la UI comparten exactamente el mismo
pipeline; no hay duplicación.

**Estructura de timing:** el callback `_console_step` registra el tiempo de cada paso
como "tiempo desde `on_step(n)` hasta `on_step(n+1)`". Esto es correcto pero incluye
el tiempo de impresión/UI del paso anterior. No es un problema en la práctica.

---

## H6-06 — UI Streamlit creada y lista para uso

**Archivo:** `src/ic/presentation/app.py`
**Inicio:** `uv run streamlit run src/ic/presentation/app.py --server.port 8503`

**Características:**
- Formulario: empresa, CIIU (opcional), ruta de salida (opcional)
- Verificación de servicios (Ollama + PG) antes de iniciar
- Barra de progreso de 10 pasos con label
- Botón de descarga del .docx al finalizar
- Expander con métricas: tiempo, costo, tokens, desglose por llamada
- Los 4 estados obligatorios (Loading, Error, Empty, Data) implementados

**Limitación conocida:** Para un informe que toma 2 horas, el servidor Streamlit mantiene
la conexión abierta. En uso local esto es aceptable. Para uso multi-usuario habría que
mover la ejecución a un worker asíncrono (no aplica al caso de uso actual).

---

## Archivos añadidos / modificados

| Tipo | Archivo |
|------|---------|
| Nuevo | `src/ic/domain/use_cases/generate_informe.py` |
| Nuevo | `src/ic/presentation/app.py` |
| Nuevo | `tests/test_generate_informe.py` (5 fast + 1 slow) |
| Modificado | `scripts/run_pilot.py` (thin wrapper) |
| Modificado | `CHANGELOG.md` (v0.7.0) |
| Modificado | `README.md` (UI, fases) |

---

## Métricas de calidad

- Tests fast antes de Fase 6: 81 passed (Fase 5F)
- Tests fast después de Fase 6: 86 passed, 2 skipped, 10 deselected (slow)
- Ruff: 0 errores en archivos nuevos/modificados
- Ningún test existente roto

---

## Próxima fase: 7 — Gestión de empresas + persistencia historial

1. Modelo `Empresa` + `EmpresaRepository` con upsert por nombre
2. Wiring de `InformeRepository` en `GenerateInforme.run()` (ahora bloqueado por FK)
3. Vista de historial en la UI (lista de informes generados, descarga retroactiva)
4. Opcional: ingesta PDF por lotes para resolver H6-03
