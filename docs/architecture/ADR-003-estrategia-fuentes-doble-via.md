# ADR-003: Estrategia de fuentes con doble vía de ingesta (automática y manual)

**Estado:** Aceptado | **Fecha:** 2026-06-19
**Decisores:** Equipo del sistema de informes de inteligencia competitiva
**Reemplaza a:** —
**Reemplazado por:** —

## Contexto

El sistema necesita evidencia de múltiples tipos: literatura científica, preprints,
metadatos académicos, información de mercado y fuentes sectoriales. Parte de esa
evidencia está disponible vía API abierta; otra parte proviene de fuentes sin API de
conexión (p. ej. EMIS, informes sectoriales de pago, estudios de mercado en PDF) que
el analista descarga manualmente. Los prompts originales ya consumían PDFs específicos
de este tipo (informes de mercado, documentos de convergencia).

El panorama 2026 de APIs académicas es mayoritariamente abierto y gratuito, lo que
favorece el presupuesto del sistema.

## Decisión

Se adopta una arquitectura de **doble vía de ingesta que converge en un único índice
vectorial**. Toda evidencia, sin importar su origen, se trocea, embebe y cita de la
misma forma; el capítulo que la consume no distingue la vía de origen, solo recibe
fragmentos relevantes con su metadato de procedencia.

### Vía 1 — Fuentes automáticas (consultadas por el sistema)
- **OpenAlex** como columna vertebral de descubrimiento y metadatos académicos:
  cobertura amplia (250 M+ obras), sin API key, sin autenticación, límite diario
  generoso. Ingiere metadatos de Crossref, arXiv y PubMed Central unificados por DOI.
- **arXiv** para preprints y novedad reciente cuando el sector lo amerite.
- **Crossref** para resolución de DOIs y construcción de referencias en formato APA.
- **Semantic Scholar** como complemento opcional (fuerte en CS/ingeniería).
- **Búsqueda web** (Tavily/DuckDuckGo) para información de mercado y actualidad no
  académica.
- **Google Scholar NO se usa como fuente programática** (bloquea scraping); queda solo
  como herramienta manual de descubrimiento del analista.

### Vía 2 — Fuentes manuales (subidas por el analista)
- PDFs descargados de fuentes sin API: EMIS, informes sectoriales de pago, estudios de
  mercado (p. ej. Fortune Business Insights), documentos internos de referencia.
- Entran al sistema por el flujo RAG de documentos locales: mismo chunking, mismos
  embeddings, mismo índice pgvector, misma citación que la Vía 1.

### Ecuaciones de búsqueda separadas por canal
- Las ecuaciones booleanas extensas (estilo buscador) se conservan para la búsqueda web.
- Para las APIs académicas se usa una versión de keywords + filtros estructurados
  (año, campo, open-access, idioma), donde el filtrado por metadatos rinde más que
  encadenar operadores booleanos. La transformación se define al refinar los prompts.

### Interacción con el manejo de datos ausentes
- Si para un capítulo no hay fragmentos suficientes ni por la Vía 1 ni por la Vía 2,
  se dispara el párrafo de ausencia (ADR-002) y la recomendación al usuario incluye,
  cuando aplique, sugerir la incorporación manual de una fuente concreta
  (p. ej. "considere subir un informe sectorial de EMIS sobre el mercado X").

## Consecuencias

### Positivas
- Costo de fuentes cercano a cero: las APIs primarias son abiertas y gratuitas.
- Homogeneidad: una sola lógica de chunking, embedding, cita y datos ausentes para
  todas las fuentes, sin importar su origen.
- Flexibilidad: el analista puede enriquecer cualquier informe con fuentes premium sin
  cambios de código.
- Trazabilidad uniforme: toda afirmación es citable hasta su fragmento de origen.

### Negativas / costos asumidos
- La Vía 2 depende de acción humana; su cobertura no es garantizable automáticamente.
- Los detalles operativos de cada API (límites de rate, formato de respuesta, si
  Semantic Scholar requiere key según volumen) deben verificarse contra su documentación
  viva al implementar cada conector. Este ADR fija la estrategia, no el contrato de
  integración.
- Las fuentes manuales de pago (EMIS) tienen restricciones de licencia de uso que el
  analista es responsable de respetar al incorporarlas.

## Alternativas consideradas

- **Solo fuentes automáticas:** descartada porque deja fuera evidencia sectorial
  valiosa sin API (EMIS, informes de pago) que ya se usaba en los prompts originales.
- **Una API académica comercial única (Scopus/WoS):** descartada por costo y por
  requerir suscripción/acceso institucional, frente a la cobertura abierta de OpenAlex.
- **Google Scholar como fuente programática:** descartada por bloqueo de scraping y
  fragilidad; relegada a descubrimiento manual.
