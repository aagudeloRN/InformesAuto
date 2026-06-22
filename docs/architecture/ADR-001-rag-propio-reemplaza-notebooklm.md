# ADR-001: RAG propio reemplaza NotebookLM como motor de recuperación

**Estado:** Aceptado | **Fecha:** 2026-06-19
**Decisores:** Equipo del sistema de informes de inteligencia competitiva
**Reemplaza a:** —
**Reemplazado por:** —

## Contexto

Los prompts originales del sistema fueron diseñados para operarse manualmente en
Google NotebookLM. Casi todos incluyen la instrucción "NO utilizar conocimiento
externo al cuaderno de NotebookLM", cuyo propósito es restringir al modelo a hablar
únicamente de lo contenido en las fuentes curadas, evitando alucinación.

El sistema que se está construyendo es un servicio automatizado (FastAPI + Streamlit)
que debe generar informes end-to-end sin intervención manual, con trazabilidad
completa y almacenamiento del historial, conforme a la Prime Directive del entorno.

NotebookLM presenta limitaciones estructurales para este objetivo:

- No expone una API estable y soportada para orquestación automatizada desde backend.
- No permite controlar ni inspeccionar su mecanismo de recuperación (qué fragmento
  sustenta cada afirmación), lo que impide la trazabilidad exigida.
- No es versionable en el repositorio ni auditable, en conflicto con los principios
  de explicabilidad y servicios controlados de la Prime Directive.
- Depende de carga manual de cuadernos, lo que contradice la meta de automatización.

## Decisión

Se adopta un sistema RAG propio como único motor de recuperación en producción,
construido sobre la infraestructura compartida del entorno:

- Índice vectorial en PostgreSQL + pgvector (instancia compartida, esquema propio).
- Embeddings con `nomic-embed-text` servido localmente por Ollama (costo cero).
- La restricción "solo fuentes, no conocimiento externo" se implementa de forma
  nativa mediante recuperación con umbral de relevancia y el manejo determinista de
  datos ausentes (ver ADR-002 y la regla de negocio asociada).

NotebookLM queda reservado, fuera del sistema, como herramienta manual de
exploración de dominios por parte del analista, sin rol en el flujo de producción.

## Consecuencias

### Positivas
- Trazabilidad hasta el fragmento (chunk) que sustenta cada afirmación, citable en APA.
- Control total del retrieval: umbral de relevancia, reranking, estrategia de chunking.
- Historial completo persistido en PostgreSQL (inputs, fuentes, respuestas, documento).
- Costo marginal de recuperación cercano a cero (embeddings locales, BD ya existente).
- Cumplimiento de la Prime Directive en trazabilidad, explicabilidad y portabilidad.

### Negativas / costos asumidos
- Mayor esfuerzo de desarrollo inicial: hay que construir conectores, chunking,
  embeddings y reranking que NotebookLM ofrecía "llave en mano".
- La calidad del retrieval pasa a ser responsabilidad del equipo; un mal chunking
  degrada todo el informe. Se mitiga validando context precision/recall en el piloto.
- Mantenimiento continuo del índice y de los conectores de fuentes.

## Alternativas consideradas

- **Mantener NotebookLM con automatización por scraping/UI:** descartada por
  fragilidad, falta de soporte, ausencia de trazabilidad y conflicto con la Prime Directive.
- **Enfoque híbrido (NotebookLM para algunos capítulos, RAG para otros):** descartada
  por duplicar mecanismos de cita y romper la homogeneidad del manejo de datos ausentes.
