# Decisión sobre Refinamientos Iterativos

**Fecha:** 2026-06-22  
**Scope:** Prompts del piloto (Prompt-01, Prompt-02, Prompt-03)  
**Criterio de decisión:** Si el refinamiento es puramente instrucción de estilo/formato → **Collapse** al system prompt (0 llamadas adicionales). Si requiere razonamiento o generación nueva → **Conserva** como paso LLM adicional.

---

## Tabla de decisiones

| Prompt | Refinamiento original (NotebookLM) | Tipo | ¿Nueva llamada LLM? | Decisión | Justificación |
|--------|-----------------------------------|------|---------------------|----------|---------------|
| Prompt-01 | — (sin refinamientos) | — | — | — | Prompt-01 no tenía pasos de mejora iterativa en el original |
| Prompt-02 | — (sin refinamientos) | — | — | — | Prompt-02 no tenía pasos de mejora iterativa en el original |
| Prompt-03 | **Mejora 2.1:** presentar jugadores en tabla/ficha por subcategoría | Formato | No | **Collapse** | Es instrucción de presentación visual; el modelo puede aplicarla directamente en la generación inicial sin necesitar ver un output previo |
| Prompt-03 | **Mejora 2.2 (a):** síntesis de presión competitiva como storytelling sin viñetas | Formato/Estilo | No | **Collapse** | Cambio de forma de presentación del mismo contenido; no requiere razonamiento nuevo |
| Prompt-03 | **Mejora 2.2 (b):** reglas de editor humano (variar ritmo, ejemplos concretos, evitar muletillas IA, dividir párrafos ≤150 palabras, ±10 % longitud) | Estilo | No | **Collapse** | Son restricciones de escritura universales que el modelo puede aplicar en la generación original si se especifican claramente en el system prompt |
| Prompt-03 | **Mejora 2.2 (c):** quitar citaciones inline y mini-checklist del output | Formato | No | **Collapse** | Restricción de output; se resuelve con una sola instrucción negativa en el system prompt |
| Prompt-03 | **Mejora 2.4:** focos (Innovación/Inversión/Talento) como storytelling + reglas de editor humano | Formato/Estilo | No | **Collapse** | Mismo patrón que 2.2; cambio de presentación sin nuevo razonamiento |
| Prompt-03 | **Mejora 2.5:** brechas como storytelling + reglas de editor humano | Formato/Estilo | No | **Collapse** | Mismo patrón que 2.2 y 2.4 |
| Prompt-03 | **Limpieza final:** quitar citaciones y mini-checklist de todo el capítulo | Formato | No | **Collapse** | Ya cubierto por la regla consolidada en el system prompt |

---

## Resumen de ahorro

| Prompt | Llamadas LLM originales (NotebookLM) | Llamadas LLM después | Ahorro |
|--------|--------------------------------------|----------------------|--------|
| Prompt-01 — Descripción Empresa | 1 | 1 | 0 |
| Prompt-02 — Sector GICS | 1 | 1 | 0 |
| Prompt-03 — Benchmarking (Cap 2) | ~7 (1 generación + 6 refinamientos) | 1 | **6 llamadas** |
| **Total piloto (3 caps)** | **~9** | **3** | **~67 %** |

> Estimación del costo original de Prompt-03 a Claude Sonnet (~500 tokens/llamada ×7): ~3500 tokens de entrada + output ≈ 0.05–0.08 USD solo en este capítulo. Después del collapse: ~0.01–0.02 USD. Dentro del presupuesto de ≤1 USD/informe completo (ADR-002).

---

## Patrón de collapse aplicado

Los 6 refinamientos del Prompt-03 comparten el mismo patrón: instrucciones de **formato de presentación** y **reglas de estilo de escritura** que en NotebookLM se aplicaban en pasos iterativos porque el modelo no recibía esas instrucciones en el primer prompt. En un sistema automatizado, estas instrucciones se incluyen directamente en el **system prompt constante**, eliminando la necesidad de llamadas de corrección post-generación.

El collapse es seguro siempre que:
1. Las instrucciones sean sin ambigüedad (p.ej. "sin viñetas" es binario; "más natural" no lo es).
2. No dependan del output anterior para evaluarse (p.ej. "amplía la sección X si quedó corta" sí dependería del output y requeriría conservarse).

Todos los refinamientos encontrados cumplen ambas condiciones.

---

## Refinamientos que habrían requerido conservarse (no encontrados en el piloto)

Para referencia futura: los siguientes tipos de refinamiento **no se colapsan**:

| Tipo | Ejemplo | Razón |
|------|---------|-------|
| Ampliar sección específica | "Expande el análisis de LatAm en 2.1" | Requiere nueva generación con contexto del output |
| Corrección de citas APA | "Corrige las citas que no cumplen formato APA 7" | Requiere validación del output + corrección razonada |
| Gate de calidad | "¿El cap 2 cubre los 14 actores requeridos?" | Verificación sobre output; dispara re-generación si falla |

Ninguno de estos apareció en los tres prompts del piloto.
