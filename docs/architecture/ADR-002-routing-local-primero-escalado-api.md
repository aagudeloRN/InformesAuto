# ADR-002: Routing de modelos local-primero con escalado selectivo a API

**Estado:** Aceptado | **Fecha:** 2026-06-19
**Decisores:** Equipo del sistema de informes de inteligencia competitiva
**Reemplaza a:** —
**Reemplazado por:** —

## Contexto

El sistema debe generar informes con un presupuesto objetivo de hasta 1 USD por
informe, sin concurrencia (un informe a la vez), en un entorno con Ollama corriendo
en el host (GPU RTX 2000 Ada 8 GB) y modelos locales ya disponibles (qwen2.5,
gemma3, llama3.2, nomic-embed-text). No existen restricciones de privacidad: solo se
usan datos libres/públicos.

El informe se compone de tareas heterogéneas: procesamiento básico (extracción,
limpieza, embeddings) y redacción analítica/síntesis (capítulos finales con tono
formal y citas). El riesgo principal de costo no es el modelo elegido por llamada,
sino el número total de llamadas (ver decisión sobre refinamiento iterativo, pendiente
de cerrar prompt por prompt).

Benchmarks propios del entorno: Qwen2.5-Coder 7B rinde ~18 t/s en Ollama sobre este
hardware, suficiente para un sistema interno sin concurrencia.

## Decisión

Se adopta una estrategia de routing **local-primero con escalado selectivo**, mediada
por un único wrapper de LLM en la capa de infraestructura (punto único de control de
costo, conforme a la regla de Dependency Agnosticism de la Prime Directive):

1. **Procesamiento básico** (extracción, limpieza, clasificación simple, embeddings):
   siempre local en Ollama. Costo cero.
2. **Redacción analítica y síntesis:** se intenta primero con modelo local. Si la
   verificación de calidad del capítulo no alcanza el umbral definido, se escala
   esa llamada concreta a un modelo de API de tier analítico (Adaptive RAG aplicado
   a redacción). Así el caso típico cuesta casi cero y solo se paga API cuando lo
   local no alcanza.
3. **Política de fallback por disponibilidad:** toda llamada tiene primario y
   secundario; si el primario falla o agota timeout, se intenta el siguiente.

### Reglas de control de presupuesto (en el wrapper)
- Caps de tokens de entrada y salida por llamada.
- Conteo y registro de costo estimado por llamada en PostgreSQL.
- Circuit breaker: límite estricto de intentos por capítulo; al superarlo, se loguea
  el error y se continúa con lo recuperado o se reporta fallo (sin bucles infinitos).
- Los nombres concretos de modelos NO se fijan en código; viven en configuración
  (`.env` + tabla de routing). Cambiar un modelo no requiere tocar la aplicación.

### Manejo determinista de datos ausentes (regla de negocio asociada)
- La ausencia de datos se trata como condición de **recuperación**, no de generación.
- Si para una sección el retrieval no devuelve fragmentos por encima del umbral de
  relevancia, NO se invoca el modelo de redacción: se inserta un párrafo de ausencia
  desde plantilla y se genera una recomendación al usuario sobre cómo conseguir esa
  información (p. ej. "considere incorporar un informe sectorial de la fuente X").
- Esto elimina la posibilidad de alucinación en secciones sin evidencia y ahorra
  llamadas, alineándose con el presupuesto.

## Consecuencias

### Positivas
- Costo del caso común cercano a cero; el gasto de API se concentra donde aporta calidad.
- Punto único de control: presupuesto, fallback y logging en un solo módulo.
- Soberanía de datos y cumplimiento de la Prime Directive (Ollama en host, servicios
  compartidos).
- Agnosticismo de proveedor: modelos intercambiables sin refactor.

### Negativas / costos asumidos
- La inferencia local es más lenta (~18 t/s); el tiempo de generación del informe
  completo será mayor que con API pura. Aceptable por ser uso interno sin concurrencia.
- Requiere definir y calibrar el umbral de calidad que dispara el escalado a API; mal
  calibrado, escala de más (caro) o de menos (baja calidad). Se calibra en el piloto.

## Alternativas consideradas

- **API pura (todo a un proveedor externo):** más rápido y simple, pero rompe la meta
  de costo y desaprovecha la infraestructura local existente.
- **Local puro (nunca escalar a API):** costo cero pero techo de calidad fijo en la
  redacción analítica; descartada por riesgo a la calidad de los capítulos de síntesis.
- **Routing por reglas estáticas (modelo fijo por capítulo):** más simple pero no se
  adapta a la dificultad real de cada generación; el escalado por verificación es
  superior en relación costo/calidad.
