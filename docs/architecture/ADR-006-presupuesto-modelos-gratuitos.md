# ADR-006: Política de presupuesto — solo modelos gratuitos o económicos en API externa

**Estado:** Aceptado | **Fecha:** 2026-07-06
**Decisores:** Equipo del sistema de informes de inteligencia competitiva
**Reemplaza a:** —
**Reemplazado por:** —
**Relacionado con:** ADR-002 (routing local-primero)

---

## Contexto

El sistema escala a modelos externos vía OpenRouter cuando la inferencia local (Ollama) no
alcanza el umbral de calidad o genera output en idioma incorrecto. OpenRouter ofrece tres
categorías de modelos:

| Categoría | Ejemplos | Precio |
|-----------|----------|--------|
| **Free** | Nemotron Super/Ultra, Llama 3.3 70B, DeepSeek R1 (distill) | $0 (rate-limited) |
| **Económicos** | Gemma 3 27B, Mistral Small, Llama 3 8B | < $0.20/MTok in |
| **Top-tier** | Claude 3.5 Sonnet/Opus, GPT-4o, Gemini Ultra, o1 | $3–$15/MTok in |

El sistema es **interno, sin concurrencia**, genera un informe a la vez y tiene como meta
estricta **≤ $1 USD por informe completo** (ADR-002). El volumen esperado en la fase piloto
es de 2–5 informes/mes.

Dado ese contexto, los modelos top-tier son económicamente inviables: un informe con 5
capítulos analíticos y 2 de síntesis a $3–$15/MTok podría costar $2–$10 USD solo en tokens
de entrada, superando el presupuesto por informe y generando un costo mensual inaceptable
para un proyecto piloto.

---

## Decisión

**Se adopta una política de costo-cero o costo-mínimo para todos los modelos de API:**

1. **Primer intento:** modelos `free` en OpenRouter (precio $0, rate-limited).
   - Primario (`LLM_API_FREE_MODEL`): Nemotron Super (actualmente el mejor free de OpenRouter
     para generación analítica en español).
   - Alternativo (`LLM_API_FREE_ALT_MODEL`): segundo modelo free como fallback ante rate limit
     del primario (ej. Llama 3.3 70B Instruct free).

2. **Fallback pago:** solo si ambos free fallan (rate limit persistente, 5xx), se escala a un
   modelo **económico** (< $0.20/MTok in): actualmente `google/gemma-3-27b-it`.
   - Probabilidad esperada en uso normal: < 5% de las llamadas.

3. **Prohibición explícita:** nunca usar modelos top-tier (`claude-*`, `gpt-4*`, `gemini-ultra`,
   `o1`, `o3`) en producción ni en desarrollo de este proyecto, salvo autorización explícita
   del equipo con modificación a este ADR.

### Tiers de modelo (inmutables en código, configurables en `.env`)

| Variable `.env` | Tier | Uso | Costo esperado |
|-----------------|------|-----|----------------|
| `LLM_API_FREE_MODEL` | `free` | Caps N1 analíticos (2, 3, 4) | $0 |
| `LLM_API_FREE_ALT_MODEL` | `free_alt` | Fallback automático si `free` falla | $0 |
| `LLM_API_SYNTH_MODEL` | `synth` | Caps N2 síntesis (5, 6, Resumen) | $0 (free) |
| `LLM_API_PAID_MODEL` | `paid` | Fallback último recurso | < $0.20/MTok in |

Los nombres concretos de modelo **viven en `.env`**, nunca en código (regla CLAUDE.md Tier 1,
ADR-002). Cambiar el proveedor o modelo no requiere tocar la aplicación.

---

## Consecuencias

### Positivas
- Costo monetario esperado por informe: **$0 en el 95% de los casos** (solo free models).
- En el 5% con rate limit en free → costo < $0.10 USD (modelo económico, pocos tokens).
- El equipo puede experimentar libremente sin preocupación de facturación.
- La restricción presupuestaria está documentada y es verificable — no depende de que el
  desarrollador recuerde no elegir modelos caros.

### Negativas / costos asumidos
- Los modelos `free` tienen rate limits (típicamente 10–20 req/min, 200 req/día en OpenRouter).
  Un informe con 5+ llamadas paralelas podría golpear el límite. **Mitigación:** los capítulos
  se generan secuencialmente en el piloto (el DAG paralelo se implementa en Fase 6, cuando
  la carga esté calibrada).
- Los modelos free pueden tener latencia variable (colas de otros usuarios). **Mitigación:**
  `llm_local_timeout=300s` y circuit breaker configurado.
- La calidad de los modelos free (120B–550B) es inferior a los top-tier en matices sutiles.
  **Decisión aceptada:** para informes de vigilancia competitiva a nivel de prototipo piloto,
  la calidad de Nemotron Super/Ultra es suficiente. Si un cliente requiere calidad top-tier,
  se revisa este ADR con la aprobación presupuestaria correspondiente.

## Alternativas consideradas

- **API pura top-tier:** descartada. Claude 3.5 Sonnet a $3/MTok in generaría ~$2–$5 por
  informe solo en tokens de entrada. Inviable para el presupuesto del proyecto.
- **Modelos económicos como primario (sin free):** posible pero innecesario — los free tienen
  calidad suficiente para el caso de uso y el fallback económico cubre los fallos de rate limit.
- **Local puro (sin OpenRouter):** descartado en ADR-002 por techo de calidad y tiempos de
  inferencia (Cap 2 local = 243s; Cap 2 API free = 2s). Los modelos locales se reservan para
  procesamiento fundacional (embeddings, GICS, Cap 1 con contexto pequeño).
