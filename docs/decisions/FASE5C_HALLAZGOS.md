# Hallazgos y decisiones operativas — Fase 5C

**Fecha:** 2026-07-06
**Alcance:** Corrección OOM/CJK + fallback multi-LLM Cap 1 + text_utils + ADR-006
**Tests al cierre:** 55 passed, 2 skipped (suite completa)
**Commit:** `9cc0733`

---

## H5C-01: qwen3:8b responde en chino — causa raíz y solución

**Contexto:** El E2E de Fase 5B con `LLM_LOCAL_ANALYTIC_MODEL=qwen3:8b` generaba Cap 1
íntegramente en chino. El system prompt anterior decía "Respuesta 100 % en español latino
neutro" pero qwen3 (modelo chino) ignoraba la instrucción cuando el contexto era amplio.

**Causa raíz:** La instrucción de idioma estaba enterrada en una lista de reglas genéricas.
Los LLMs chinos le dan más peso al idioma de sus datos de preentrenamiento cuando el contexto
es denso en texto extranjero (URLs, nombres de empresas en inglés, fragmentos web).

**Solución implementada (doble vía):**
1. **Prompt más determinista:** la regla de idioma se elevó a Regla #1 con instrucción de
   reescritura explícita: *"Si detectas que empiezas a escribir en otro idioma, detente y
   reescribe en español."* Aplicado en chain_01, chain_03 y chain_04.
2. **Detección post-generación:** `text_utils.has_cjk_characters(texto, threshold=5)` —
   si el texto tiene ≥5 caracteres CJK, el use case descarta la respuesta y devuelve un
   párrafo de ausencia con instrucción de reintentar con otro modelo.

**Por qué threshold=5:** Para no rechazar textos que mencionan marcas o empresas asiáticas
legítimamente (ej. "Samsung", "Huawei" pueden aparecer en un análisis de competidores).
Cinco caracteres CJK en el texto narrativo ya indican que el modelo empezó a responder en
el idioma incorrecto.

**Decisión de diseño:** La detección no reintenta automáticamente — solo registra la ausencia.
Un reintento automático podría provocar bucles costosos si el modelo local siempre falla en CJK.
El usuario recibe instrucción explícita en el párrafo de ausencia sobre qué hacer.

---

## H5C-02: OOM en Ollama — causa raíz confirmada y mitigación parcial

**Contexto:** Durante el E2E extendido, Ollama lanzaba HTTP 500 o crasheaba silenciosamente.
La secuencia de operaciones era: `embed(chunk_1)` → `embed(chunk_2)` → ... → `llm(texto)`.
Cuando el LLM llevaba cargado varios minutos, el embedder recibía 500 al intentar cargar
`nomic-embed-text` mientras `qwen3:8b` seguía en VRAM.

**Causa raíz verificada:** Ollama por defecto mantiene los modelos en VRAM 5 minutos
(`keep_alive=5m`). Con 8GB VRAM total:
- `nomic-embed-text`: ~500MB VRAM
- `qwen3:8b`: ~5.2GB VRAM
- Margen restante: ~2.3GB (suficiente si no coexisten, insuficiente si ambos cargan a la vez)

El E2E lanzaba `embed()` justo cuando el LLM todavía estaba en VRAM → contención → 500.

**Mitigación implementada en 5C:**
1. `Embedder.embed()` reintenta con backoff `[0, 3, 8]` segundos ante HTTP 500. El wait de
   3–8s cubre el tiempo que Ollama necesita para descargar el LLM y liberar VRAM.
2. `llm_local_timeout=300s` en config: antes era 120s implícito; `qwen3:8b` con 4k tokens
   de contexto puede tardar 150–200s en el hardware disponible.

**Mitigación pendiente (Fase 5D):** Añadir `"keep_alive": 0` a las requests de embeddings
y de LLM local para que Ollama descargue el modelo inmediatamente tras cada request. Con eso,
los modelos nunca coexisten en VRAM. Ver H5C-03.

---

## H5C-03: Estrategia definitiva para `keep_alive: 0` — pendiente Fase 5D

**Decisión de diseño anticipada:**

```python
# infrastructure/retrieval/embedder.py — a implementar en Fase 5D
resp = httpx.post(
    f"{self._base_url}/api/embeddings",
    json={
        "model": self._model,
        "prompt": text,
        "keep_alive": 0,    # descargar de VRAM inmediatamente
    },
    timeout=30,
)

# infrastructure/llm/gateway.py — a implementar en Fase 5D
# Solo para OllamaGatewayLLM (no para OpenRouterGatewayLLM)
body["keep_alive"] = 0
```

**Por qué no se implementó en 5C:** el retry del embedder ya mitiga el síntoma. Implementar
`keep_alive=0` agrega latencia de carga en cada llamada (~2–3s extra por load/unload). Se
implementa en 5D junto con Cap 4, cuando el E2E tenga más capítulos y el riesgo de OOM sea
mayor.

**Verificación previa requerida:**

```bash
# Verificar que keep_alive:0 funciona en la versión de Ollama instalada
curl -s http://127.0.0.1:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test","keep_alive":0}' | jq '.embedding | length'
# Debe devolver: 768
```

Si da error, probar `"keep_alive": "0s"` (formato string — algunas versiones de Ollama lo
requieren así).

---

## H5C-04: Contexto web explícito en Cap 1 — mejora de calidad

**Contexto:** El prompt anterior de Cap 1 no inyectaba el texto de los resultados web: solo
pasaba `nombre_empresa` y `actividad_ciiu`. El LLM generaba texto basado en su conocimiento
preentrenado, no en fuentes reales. Para empresas colombianas medianas (Noel, Haceb, Argos)
el modelo tiene información limitada y de baja precisión.

**Cambio implementado:**
- 3 queries de búsqueda en lugar de 1 (empresa + descripción, empresa + portafolio,
  empresa + RUES+CIIU).
- Los resultados se formatean con `format_web_results_as_context()` y se inyectan como
  `{web_context}` en el user prompt.
- La instrucción al modelo es explícita: *"usa EXCLUSIVAMENTE el contexto web provisto...
  todo lo que escribas debe poder rastrearse al contexto"*.

**Impacto esperado:** reducción de alucinaciones en cifras específicas y datos históricos.
El modelo tiene que declarar ausencia si el dato no está en el contexto — no puede inventar.

---

## H5C-05: Política de presupuesto formalizada en ADR-006

**Contexto:** La restricción de usar solo modelos gratuitos o económicos existía en la
práctica pero no estaba documentada como decisión arquitectónica. Cualquier agente o
desarrollador nuevo podría elegir Claude o GPT-4o sin saber que viola el presupuesto.

**Decisión:** Creado `ADR-006-presupuesto-modelos-gratuitos.md` con prohibición explícita
de modelos top-tier y tabla de tiers autorizados. Ahora la restricción es un ADR inmutable:
cambiarla requiere crear un ADR nuevo que lo reemplace, con aprobación explícita.

---

## Pendientes concretos al cierre de Fase 5C

1. **E2E de Cap 3 (prioridad antes de Fase 5D):**
   ```bash
   uv run python scripts/run_pilot.py --empresa "Noel S.A.S." --ciiu 1081
   ```
   Criterio de éxito: el `.docx` incluye texto real en Cap 3 con ≥200 palabras en español.

2. **Verificar `keep_alive: 0`** en la versión de Ollama instalada (ver H5C-03).

3. **Fase 5D:** implementar `keep_alive=0`, Cap 4 Ecosistema, markers `@pytest.mark.slow`.
