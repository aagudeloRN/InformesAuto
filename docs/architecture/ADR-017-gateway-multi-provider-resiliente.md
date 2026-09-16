# ADR-017: Gateway Multi-Provider Resiliente y Política de Modelos LLM

## Estado
Aceptado

## Fecha
2026-09-16

## Contexto
Para garantizar la sostenibilidad operativa del generador de informes de inteligencia competitiva sin incurrir en costos prohibitivos ni sufrir interrupciones por cuotas de rate limit (429) o fallos de red (transient errors), se requiere una arquitectura de routing multi-tier con failover automático.

## Decisión
Se implementa un ResilientChatModel en el Gateway LLM con la siguiente jerarquía de proveedores y modelos:
1. **Tier Primario (Síntesis y Análisis)**: Direct Google Gemini API (gemini-2.5-flash / gemini-1.5-flash en Google AI Studio), aprovechando el free tier de 15 RPM / 1M TPM / 1500 RPD.
2. **Tier Secundario (Fallback API)**: OpenRouter con modelos gratuitos (meta-llama/llama-3.3-70b-instruct:free, google/gemini-2.0-flash-exp:free, etc.) o fallback universal.
3. **Tier Local (Embeddings y Análisis Offline)**: Ollama local (
omic-embed-text para embeddings vectoriales en pgvector, y opcionalmente modelos locales para tareas batch sin dependencia de red).
4. **Resiliencia y Cost Tracking**:
   - Detección automática de respuestas vacías (EmptyGenerationError), rate limits (429) y caídas de conexión con reintento y degradación secuencial entre tiers.
   - CostTracker determinista que registra tokens de entrada/salida y costo estimado en USD según tarifas actualizadas.

## Consecuencias
- Cero costo operativo base utilizando los límites gratuitos de Google AI Studio y OpenRouter.
- Cobertura completa de SLAs de disponibilidad durante picos de carga.
- Independencia de proveedor sin vendor lock-in gracias a la abstracción BaseChatModel de LangChain.
