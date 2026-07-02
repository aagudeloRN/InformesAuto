# Hallazgos y decisiones operativas — Fase 5A

**Fecha:** 2026-07-02  
**Alcance:** Diagnóstico del sistema + Script piloto CLI + Gateway OpenRouter + CostTracker real  
**Tests al cierre:** 37/37 pasando (27 heredados + 10 nuevos)  
**Commit:** `944fd76`

---

## H5A-01: El entorno compartido tiene múltiples proyectos — los puertos son recurso crítico

**Contexto:** Al iniciar la fase se detectaron 11 contenedores Docker corriendo de otros proyectos
(`sacd_*`, `repositorio_*`, `consejoredaccion_*`). Los puertos relevantes ocupados:

| Puerto | Contenedor | Propósito |
|--------|-----------|-----------|
| 5433 | sacd_postgres | Otro proyecto |
| **5434** | repositorio_postgres | **Instancia compartida de este proyecto** |
| 5435 | consejoredaccion-db-1 | Otro proyecto |
| 8501, 8502 | sacd_frontend | UI de otro proyecto |
| 6380, 6381 | Redis de otros proyectos | — |

**Hallazgo clave:** `repositorio_postgres` en el puerto 5434 **ya es** la instancia PostgreSQL
que InformesAuto usa. El `docker-compose.yml` del proyecto intentaría conflictuar si se ejecuta
cuando esa instancia ya está activa.

**Decisión:** Agregar nota explicativa en `docker-compose.yml`. El script piloto verifica
conectividad directa en lugar de levantar contenedores.

**Implicación para UI Streamlit (Fase 6):** usar puerto **8503** (8501 y 8502 ocupados).

---

## H5A-02: OpenRouter no estaba configurado — el gateway solo hablaba Ollama

**Contexto:** El `.env.example` indicaba `LLM_API_PROVIDER=anthropic` con clave vacía.
El gateway solo tenía `OllamaGatewayLLM`. No existía ninguna ruta de código para escalar
a un modelo API, a pesar de estar documentado en ADR-002 y en la sección "Pendiente"
de ARQUITECTURA.md.

**Decisión:** Construir `OpenRouterGatewayLLM` usando httpx directo (misma dependencia
del proyecto, sin agregar `langchain-openai`). OpenRouter expone la API OpenAI-compatible
en `https://openrouter.ai/api/v1/chat/completions`, compatible con el patrón existente.

**Headers obligatorios para OpenRouter:**
```python
"Authorization": f"Bearer {api_key}",
"HTTP-Referer": "https://github.com/aagudeloRN/informes-ic",
"X-Title": "InformesAuto-IC",
```

**Por qué OpenRouter y no Anthropic/OpenAI directamente:**
- El usuario ya usa OpenRouter y conoce los modelos free disponibles ahí
- Los modelos Nemotron de NVIDIA (free) son potentes y sin costo monetario
- Un solo proveedor simplifica el manejo de claves y el código
- `google/gemma-3-27b-it` como respaldo pago es muy económico (~$0.15 USD por informe completo estimado)

---

## H5A-03: CostTracker existía pero era un cascarón sin conectar

**Contexto:** `CostTracker` (Fase 3) acumulaba tokens pero `total_cost()` siempre
retornaba `0.0` — nunca se calculaba el costo. El método `add_local_call()` no actualizaba
`_total_cost`. Las columnas `costo_usd` y `tiempo_generacion_s` en `HistorialInforme`
existían pero nunca se poblaban.

**Decisión:**
1. Agregar tabla de precios `_PRICING` como constante de módulo (fácil de mantener sin
   tocar lógica de negocio)
2. `add_call(model, tokens_in, tokens_out)` calcula y acumula costo real
3. `add_local_call()` mantenido por compatibilidad, registra tokens con costo $0
4. `records()` retorna `list[CallRecord]` para que el assembler/UI consuma el desglose

**Deuda pendiente:** Los use cases existentes (caps 1, GICS, 2) todavía usan `OllamaGatewayLLM`
directamente sin pasar el tracker. Para que los costos se registren correctamente en los
caps locales, hay que inyectar el tracker en `build_llm()` o en los use cases en Fase 5B.

---

## H5A-04: El modelo local qwen2.5:7b tarda ~243s en Cap 2 — validación del escalado a API

**Contexto:** La prueba E2E del script piloto arrojó estos tiempos con `qwen2.5:7b` local:

| Paso | Tiempo |
|------|--------|
| Cap 1 — Descripción empresa | 32.1s |
| GICS — Clasificación | 4.4s |
| Cap 2 — Análisis competitivo | 242.7s |
| Referencias APA | 0.0s |
| Ensamblado .docx | 0.0s |
| **Total** | **279.3s (~4.6 min)** |

El 87% del tiempo es Cap 2. Con 8 capítulos analíticos, el tiempo total local rondaría
los 30–40 minutos. Inaceptable para un producto usable.

**Implicación para routing:** Confirmado que Cap 2 en adelante deben usar OpenRouter
(modelos free sin latencia de GPU local). El modelo local queda para embeddings y caps
fundacionales rápidos (Cap 1 ~32s, GICS ~4s).

**Benchmark de referencia:** En condiciones óptimas, un cap analítico con Nemotron Super
en OpenRouter debería tardar 10–30s, reduciendo el tiempo total a ~5 min con todos los caps.

---

## H5A-05: Estrategia de modelos para WSL con GPU 8GB

**Contexto:** El entorno corre en WSL2 con GPU RTX (8GB VRAM). Los modelos Ollama >7B
consumen toda la memoria y pueden cuelgar el sistema.

**Política definida:**

| Capa | Modelo | Tamaño | Uso |
|------|--------|--------|-----|
| Embeddings | `nomic-embed-text:latest` | 137 MB | Siempre local |
| N0 (fundacionales) | `qwen2.5:7b` | 4.7 GB | Cap 1, GICS |
| N1 analíticos | `nemotron-super:free` (OpenRouter) | — | Caps 2, 3, 4 |
| N2/N3 síntesis | `nemotron-ultra:free` (OpenRouter) | — | Caps 5, 6, Resumen |
| Respaldo pago | `google/gemma-3-27b-it` (OpenRouter) | — | Si free tiene rate limit |

**NUNCA usar localmente:** modelos >8B (ej: `llama3.1:70b`, `qwen2.5:14b+`, `deepseek-r1:32b`).

---

## H5A-06: CIIU de Noel S.A.S. se clasificó como retail, no como alimentos

**Contexto:** En la prueba E2E, la clasificación GICS retornó:
`"Distribución y venta minorista de productos básicos (GICS 3010)"`
en lugar del esperado `"Alimentos, bebidas y tabaco"`.

**Análisis:** El CIIU 1081 (fabricación de productos de panadería) es correcto para Noel,
pero la descripción generada por Cap 1 (con búsqueda web genérica sobre "Noel S.A.S. RUES CIIU")
devolvió texto centrado en distribución/retail, no en manufactura de alimentos. La cadena
GICS clasificó en base a esa descripción.

**No es un bug sino una señal de calidad de retrieval:** La búsqueda web no encontró
suficiente contexto manufacturero. El flag `--ciiu 1081` se pasó manualmente y se registró
en el DTO, pero chain_02 recibe la descripción textual, no el código CIIU directamente.

**Implicación para Fase 5B:**
1. Mejorar el prompt de Cap 1 para que enfatice la actividad industrial cuando hay CIIU
2. Considerar pasar el CIIU como variable al prompt de clasificación GICS para anclar la clasificación
3. El lookup CIIU planeado para Fase 6 (CSV DANE + RUES) ayudará a pre-validar la categoría

---

## H5A-07: El patrón de prueba uno-a-uno es la estrategia correcta para Fase 5B

**Contexto:** Para los caps 3–6 y el resumen, la tentación es implementar todos a la vez.
El análisis de riesgo muestra que cada capítulo tiene su propia complejidad de retrieval
(OpenAlex para tendencias, web local para ecosistema, cruce de caps para convergencias).

**Decisión del usuario:** Implementar y probar un capítulo a la vez antes de avanzar al siguiente.
Secuencia acordada: Cap 3 → (test) → Cap 4 → (test) → Cap 5/6 → (test) → Resumen.

**Criterio de "prueba pasa":** El `.docx` generado por `run_pilot.py` incluye el nuevo capítulo
con texto real (no el placeholder de ausencia) y las referencias corresponden al retrieval
del capítulo recién implementado.

---

## Pendientes concretos al cierre de Fase 5A

1. **Usuario debe agregar al `.env`:**
   ```env
   OPENROUTER_API_KEY=sk-or-...
   LLM_API_FREE_MODEL=nvidia/nemotron-3-super-120b-a12b:free
   LLM_API_SYNTH_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
   LLM_API_PAID_MODEL=google/gemma-3-27b-it
   ```

2. **Siguiente tarea de código:** leer `source_prompts/6. Prompt - Capítulo 3 - Análisis tendencial.docx`
   y codificar `chain_04_tendencias.py` + `generate_tendencias.py` + DTO `CapTendencias` +
   integración en assembler + test.

3. **Deuda menor:** inyectar `CostTracker` en los use cases de caps locales (Cap 1, GICS)
   para registrar tokens aunque el costo sea $0.
