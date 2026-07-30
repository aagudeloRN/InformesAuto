# Propuesta — Knowledge Base de entidades, ingesta enriquecida y auto-revisión

> **Estado:** PROPUESTA (parcialmente implementada, no es ADR). Consolida las decisiones discutidas
> y acordadas con el usuario el **2026-07-29**, tras el cierre del Sprint A de Fase 22. Se
> implementa en **chats limpios por bloque** (evitar context rot); los prompts de arranque
> están al final. Amplía y no reemplaza `PROPUESTA_BASE_EMPRESAS.md` (DT-050).
>
> **Avance:** §2 (ingesta enriquecida sin reingesta) → DT-057 ✅ (F23). §1 (KB de entidades) +
> §1.4 (anclaje de competidores) + §1.2 (base viva) → **DT-056 ✅ (F24, 2026-07-30**, rama
> `feature/fase24-dt056`; ver `docs/decisions/FASE24_HALLAZGOS.md`). §3 (Cap 4 adaptativo) →
> DT-058 ✅ (F22 B2). Pendientes: §4 (auto-revisión) → DT-059; §2 Tanda 2 (reingesta A/B) → DT-060;
> §5 (UI captura manual) → HITL F24/F25.
>
> Regla de oro transversal (acordada): **procedencia (provenance) + estado candidato/verificado**
> en todo dato acumulado, para que un error extraído una vez NO se reuse como "hecho" en informes
> futuros (RN-001 a escala).

## 0. Diagnóstico que la motiva — por qué el Cap 2 no trae competidores

Verificado en código (`generate_benchmarking.py`, `chain_03_benchmarking.py`) durante el
cierre de F22 A3 (E2E Alpina/Sofasa):

- **A. Identificar y enriquecer en un solo paso (causa raíz).** No existe extracción de entidades;
  el LLM recibe un blob genérico de sector y debe *adivinar* 14 competidores y *rellenar* 8 campos
  cada uno. Sin evidencia por-entidad → "Dato no disponible". (T22.4 "enriquecimiento dirigido"
  está en el roadmap pero nunca se implementó.)
- **B. Queries a nivel sector, no por entidad.** Las 3 búsquedas web son overviews de sector
  (traen blogs de tendencias, no perfiles de empresa). Nunca se busca `"<competidor> portafolio
  ingresos 2025"`.
- **C. El corpus local no tiene fichas por empresa.** Los EMIS son informes *de sector*, no
  perfiles. Ni web ni RAG traen datos estructurados por-competidor (lado B de DT-054).
- **D. Sin memoria entre corridas.** ADR-013 purga chunks web no citados → dos informes del mismo
  sector re-buscan lo mismo desde cero.
- **E. Nombres no anclados → alucinación** (origen de la huérfana `(Alpina, Carvajal, 2019)`).

**La solución** (este documento) combina: (1) pipeline identificar→enriquecer por entidad
(T22.4), (2) un KB de entidades que se nutre en cada corrida (idea del usuario), y (3) arreglos
de ingesta RAG (DT-054/057) — hoy dispersos como deudas separadas.

## 1. Knowledge Base de entidades (generaliza DT-050)

En vez de tablas sueltas (empresas / competidores / oportunidades), **un patrón común de entidad**
con provenance por campo. Empresas, competidores, oportunidades de inversión y eventos (M&A/JV)
comparten ~80 % del diseño → la UI y los importadores se construyen una vez.

### 1.1 Modelo (esquema propio `informes_ic`, TIER 1 regla 3)

- `entidades` — entidad canónica (empresa, oportunidad, evento). Clave fuerte: `nit` (empresas
  colombianas); fallback nombre normalizado + país/ciudad.
- `entidad_atributos` (o JSONB con lineage) — **un atributo, con su procedencia**: `valor`,
  `fuente` (`usuario`|`emis`|`web`|`db_externa`|`informe`), `confianza`, `fecha`, `documento_id`.
  Prioridad en conflicto: **usuario > db_oficial/emis > web**.
- `entidad_menciones` — entidad ↔ documento ↔ sector (poblada por NER en ingesta, §2).
- `entidad_relaciones` — empresa ↔ oportunidad ↔ evento (para Cap 4).
- `estado`: `candidato` (extraído de web, sin verificar) vs `verificado` (fuente curada o
  aprobado por humano). `curado`/`curado_por`/`curado_en` (curación humana futura, HITL F24/F25).

### 1.2 Enriquecimiento incremental ("base viva") — idea del usuario

En cada corrida ya pagamos el costo de recuperar info de la empresa principal; se **reutiliza para
nutrir el KB**. Así, cuando se analice otra empresa del mismo sector, la primera ya está disponible
como competidor con datos. Dos niveles:

1. **Campos estructurados** (portafolio, ingresos, ciudad, tamaño) — con provenance; los de web
   entran como `candidato`.
2. **Campo libre etiquetado** ("casos de éxito", notas) — blob con provenance que el LLM *puede
   consultar* para enriquecer, **sin tratarlo como verdad**.

**Riesgo controlado (crítico):** sin el gate candidato/verificado + provenance, un dato mal
extraído se vuelve error sistemático en todos los informes futuros del sector. El gate es
condición de diseño, no opcional.

### 1.3 Oportunidades de inversión

Misma entidad-pattern (`tipo='oportunidad'`), alimenta **Cap 4 (Ecosistema)**. Se nutre de: EMIS
(eventos M&A/JV citados), web dirigida, y aportes manuales del usuario (UI, §4).

### 1.4 Anclaje de competidores (cierra causas A/E)

El pipeline identificar→enriquecer (T22.4) consulta el KB por `sector_gics` (+ relevancia:
sector, tamaño, geografía, actividad — criterio DT-050 §133) para obtener la **lista canónica** de
competidores antes de buscar. Menos alucinación, fichas pre-pobladas, y cada búsqueda dirigida
por-entidad nutre el KB de vuelta.

## 2. Ingesta RAG enriquecida — batch en la reingesta por sector (DT-057)

La reingesta cuesta ~2 días → se batchea todo lo que **no se backfillea barato**. (Metadata
enriquecida sola: precisión ~73 %→~82 %, ver Fuentes.) Reingesta **por sector** para poder ir
probando.

**Tanda 1 — alto valor / bajo riesgo (hacer sí o sí):**
1. **`tipo_fuente` en EMIS individuales** — causa raíz de DT-054 (hoy NULL → nunca entran a la
   reserva sectorial estricta que filtra a `informe_compilado`).
2. **Metadata enriquecida por chunk**: sección/heading, nº de página, fecha, idioma, tipo de doc
   (citación a nivel página + filtrado).
3. **Idempotencia por hash de contenido + update path** (ya existe `chunk_sha256` en metadatos):
   arregla el skip-por-título de DT-053 que impide re-etiquetar.
4. **NER en ingesta → `entidad_menciones`** (base de §1.2, sin costo extra de búsqueda).
5. **Preservar tablas/cifras de los EMIS** (cuota de mercado, ingresos — oro del benchmarking).
6. **Poblar `sectores_adicionales`** (dato dormido de DT-053).

**Tanda 2 — "ahora o nunca barato" (decidir con prueba de 1 sector antes de comprometer 2 días):**
7. **Chunking estructural** (respetar headings) vs fijo 1000 — punto medio, menos riesgo que
   semantic-chunking puro.
8. **Doc-summary vector** (multi-vector/parent-doc) — un doc aflora por match temático aunque
   ningún chunk suelto puntúe alto (ataca diversidad DT-054).

**Fuera de default (experimento aparte):**
9. **Cambiar embedder** (nomic-embed-text → multilingüe más fuerte). La reingesta es el momento
   barato, pero es scope/riesgo: **probar candidato contra el harness primero**; si no gana claro,
   quedarse con nomic.

**Aprovechar para diagnosticar:** los 5 PDFs fallidos (detectar escaneado/vacío + flag; OCR opcional).

## 3. Cap 4 (Ecosistema) — adaptativo, NO eliminar (DT-058)

Acordado: el problema no es el capítulo, es que **fuerza 5 subsecciones fijas** (4.1–4.5) aunque no
haya evidencia → rellena con "Dato no disponible". Solución:
- **Gatear cada subsección con `check_retrieval_sufficient`** (ya existe): emitir solo las que
  tienen evidencia real.
- Si el capítulo entero no supera el umbral, **omitirlo** (sin filler; principio de datos ausentes
  ADR-002).
- Cap 4 es donde el KB de oportunidades/eventos (§1.3) más aportará → no cerrar esa puerta
  eliminándolo.

## 4. Loop de auto-revisión (extiende T22.7 / DT-048 — DT-059)

Patrón **Reflection/Reflexion/evaluator-optimizer** (ver Fuentes). Grafo cíclico: generar →
juez con rúbrica → revisar → repetir hasta umbral. Ya tenemos rúbrica v1.0 (F20), `eval_gate` y el
LLM-judge planeado (T22.7). El loop = juez + arista de revisión.

**Decisiones acordadas:**
- **Por-nodo dentro de UNA corrida del DAG** (NO correr el informe 3× y mezclar caps de distintas
  corridas → rompería coherencia; el Cap 6 sintetiza 2/3/4/5 y necesita insumos consistentes).
  Cada cap guarda **su** mejor versión dentro de su propio loop.
- El DAG **ya** ordena N1(web) → N2 → N3(integración) → los caps de integración consumen los caps
  web ya refinados. La intención del usuario ("caps web sólidos antes de integrar") sale gratis.
- **Dos sabores del loop**: caps web pueden **re-buscar** en el loop (Reflexion con herramientas:
  el juez pide un dato faltante → nueva búsqueda dirigida por entidad); caps de integración solo
  **re-sintetizan**.
- **Guardar el mejor, no el último** (rúbrica-scored); parada: score ≥ umbral **O** sin mejora
  **O** **3 iteraciones**.
- **Selectivo**: solo revisa el cap que no pasa el gate (no todos).
- **Evaluador**: OpenRouter/Nemotron (ha funcionado bien, rápido); Ollama solo fallback. Latencia
  no es limitante (informe manual ~1 semana; automático ~20 min; 3× = ~1 h sigue siendo óptimo).

## 5. UI de captura manual (después del diseño de DBs — punto 3 del usuario)

Primero DBs + interacción de agentes, **luego** UI. La UI es "tonta" (TIER 3): formulario que
escribe a *staging* con `fuente="manual"` (nunca lógica de negocio); validación/dedup/merge viven
en `domain`/`data`. Encaja con HITL (F24/F25). Buenas prácticas: staging → validación/dedup →
merge (upsert idempotente); un importador por formato externo (wrappers en `infrastructure/`,
TIER 1 regla 5), todos normalizan a la entidad canónica.

## 6. Secuenciación acordada (fixes primero — punto 2 del usuario)

1. **Sprint B (deuda + fix competidores)** — valor inmediato en el próximo informe:
   DT-055 (fuga intro Cap 6), T22.2 (radar), T22.3 (checkpoint) · **DT-054 + T22.4** (fix real de
   competidores: `tipo_fuente` + reserva incluye individuales + pipeline identificar→enriquecer) ·
   **DT-058** (Cap 4 adaptativo).
2. **DT-057 (ingesta enriquecida) + reingesta por sector** — batch de la Tanda 1; probar Tanda 2 en
   1 sector.
3. **DT-056 (KB de entidades)** — diseño DBs + interacción de agentes → luego UI (§5).
4. **DT-059 (auto-revisión)** — extender T22.7 una vez el juez/rúbrica estén sólidos.

## 7. Fuentes

Ingesta/RAG:
- [Advanced RAG techniques: Data processing & ingestion — Elasticsearch Labs](https://www.elastic.co/search-labs/blog/advanced-rag-techniques-part-1)
- [Beyond Fixed Chunks: Semantic Chunking and Metadata Enrichment (Medium)](https://medium.com/@shaikmohdhuz/beyond-fixed-chunks-how-semantic-chunking-and-metadata-enrichment-transform-rag-accuracy-07136e8cf562)
- [A Systematic Framework for Enterprise Knowledge Retrieval: LLM-Generated Metadata to Enhance RAG (arXiv 2512.05411)](https://arxiv.org/pdf/2512.05411)
- [Chunking Strategies for RAG: Methods, Trade-offs & Best Practices (Atlan)](https://atlan.com/know/chunking-strategies-rag/)

Auto-revisión (Reflection/Reflexion):
- [LangGraph — Build Self-Improving Agents (Medium)](https://medium.com/@shuv.sdr/langgraph-build-self-improving-agents-8ffefb52d146)
- [Reflexion Agent with LangChain and LangGraph (Medium)](https://medium.com/@vi.ha.engr/building-a-self-correcting-ai-a-deep-dive-into-the-reflexion-agent-with-langchain-and-langgraph-ae2b1ddb8c3b)
- [Reflection vs Reflexion with LangGraph (Level Up Coding)](https://levelup.gitconnected.com/building-a-self-improvement-agent-with-langgraph-reflection-vs-reflexion-1d1abcc5865d)
