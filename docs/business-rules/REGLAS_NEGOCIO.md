# Reglas de Negocio del Sistema

> Reglas invariantes que definen el comportamiento del sistema de informes.
> Cada regla tiene un código `RN-NNN` para referencia desde el código y los ADRs.

---

## RN-001 — Datos ausentes: condición de recuperación, no de generación

**Regla:** Si el retrieval RAG retorna menos de `MIN_CHUNKS` fragmentos con score ≥ `RAG_SIMILARITY_THRESHOLD`,
el sistema **no invoca el LLM**. Inserta un párrafo de ausencia estándar generado desde plantilla.

**Implementación:** `domain/absent_data.py` → `check_retrieval_sufficient()` + `build_absent_paragraph()`

**Umbral por defecto:** `MIN_CHUNKS = 3`, configurable por capítulo.

**Razón:** Evitar que el LLM fabrique contenido cuando no hay evidencia suficiente. El párrafo de
ausencia le indica al analista humano qué buscar para enriquecer el informe.

**Formato del párrafo de ausencia:**
```
No se encontró información suficiente para generar [Cap N — Nombre].
Recomendación: ingestar PDFs sectoriales relevantes con `scripts/ingest_pdf.py`
o verificar conectividad con Tavily/DDG para búsquedas web.
```

---

## RN-002 — Citación APA 7 obligatoria y trazable

**Regla:** Toda afirmación en el informe que provenga de fuentes externas debe ser trazable hasta
su `ChunkResult` de origen. Las referencias se generan en APA 7 a partir de los metadatos del chunk.

**Implementación:** `infrastructure/citation/apa_formatter.py` → `build_references_section()`

**Campos requeridos en metadatos del chunk:**
- `titulo` — título del documento o página
- `autor` — autor (puede ser `None` → "Autor desconocido")
- `año` — año de publicación (puede ser `None` → "s.f.")
- `fuente_nombre` — nombre de la fuente (OpenAlex, web, PDF manual)
- URL del chunk (campo `fuente_url` en `ChunkResult`)

**Regla de deduplicación:** Solo se incluye una referencia por URL única. Los chunks del mismo
documento comparten referencia.

---

## RN-003 — Política de modelos: API-primero para LLM generativo, local solo para embeddings

**Regla:** El LLM generativo usa OpenRouter (free tier) como primario. Ollama solo corre
`nomic-embed-text` (embeddings, 0.3 GB) y actúa como fallback de LLM cuando no hay
`OPENROUTER_API_KEY`. Esto aplica desde ADR-010 por restricción de VRAM en WSL2.

**Tiers (ver ADR-006 y ADR-010):**
- N0 Cap 1: `api_llm → api_llm_alt → local` (cadena fallback)
- N0 GICS: `api_llm → local` (ADR-010: invertido respecto a ADR-002)
- N1 Cap 2 Benchmarking: `api_llm → local` (ADR-010)
- N1 Caps 3-4: `api_llm` (sin fallback local)
- N2 Cap 5 Convergencia / Cap 6 Accionables: `api_llm_synth` / `api_llm`
- N3 Resumen Ejecutivo: `api_llm_synth`

**Prohibición absoluta:** Modelos top-tier (Claude-3, GPT-4o, Gemini Ultra, o1/o3). Presupuesto
máximo: $1.00 USD por informe completo.

**Nombres de modelo:** Solo en `.env`. Nunca en código de aplicación.

---

## RN-004 — Ingesta de fuentes: doble vía hacia un único índice

**Regla:** Toda fuente —automática (web, OpenAlex) o manual (PDF)— se indexa en el mismo store
pgvector. Las búsquedas RAG no distinguen el origen de la fuente.

**Fuentes automáticas:** `WebConnector` (Tavily/DDG) + `OpenAlexConnector`
**Fuentes manuales:** PDFs via `scripts/ingest_pdf.py` (con anti-duplicados SHA-256)
**Fuentes prohibidas:** Google Scholar programático (ToS).

**Namespace de fuentes:** el campo `fuente_tipo` en el chunk puede ser `"web"`, `"openalex"`, `"pdf"`.

---

## RN-005 — Estructura del informe: DAG de capítulos con barreras de sincronización

**Regla:** Los capítulos siguen un grafo acíclico dirigido. Las barreras de sincronización
garantizan que los inputs de cada nivel estén completos antes de avanzar.

```
N0 (fundacionales): Cap 1 Descripción + GICS
  ↓ barrera: N0 completo antes de N1
N1 (analíticos): Cap 2 Benchmarking ‖ Cap 3 Tendencial ‖ Cap 4 Ecosistema ‖ Cap 5 Convergencia
  ↓ barrera: N1 completo antes de N2
N2 (síntesis): Cap 6 Accionables (cruza Cap 2+3+4+5)
  ↓ barrera: N2 completo antes de N3
N3 (meta): Resumen Ejecutivo + Párrafos Introductorios + Referencias APA
  ↓
Ensamblado .docx con plantilla membrete
```

**Estado actual de implementación (Fase 8):** DAG completo implementado en
`GenerateInforme` (ADR-008). N0 (Caps 1+GICS), N1 paralelo (Caps 2+3+4), N2 (Caps 5 con 3 ejes
paralelos + Cap 6), N3 (Resumen Ejecutivo + Referencias) + ensamblado .docx. E2E validado con
Noel S.A.S. Ver `docs/decisions/FASE6_HALLAZGOS.md` y `FASE8_HALLAZGOS.md`.

---

## RN-006 — Historial completo en BD: trazabilidad total del informe

**Regla:** Cada informe generado persiste en la BD: inputs del usuario, fuentes consultadas
(chunks usados), texto generado por cap, documento final, costos LLM, tiempos de ejecución.

**Implementación:** `data/repositories/informe_repo.py` → `InformeRepository`
**Tabla:** `informes_ic.historial_informes` con JSON de chunks y costs.

**Razón:** Auditoría, reproducibilidad y mejora del sistema. Un analista debe poder reconstruir
exactamente por qué el sistema generó un texto determinado.

**Estado (Fase 7):** ✅ Implementado. `EmpresaRepository.upsert_by_name()` en
`data/repositories/empresa_repo.py`. Wiring en `GenerateInforme._run_n3()`. Columnas
`tokens_in`/`tokens_out` agregadas con migración idempotente `ensure_historial_columns(engine)`.

---

## RN-007 — Idioma: español latino neutro en toda la salida

**Regla:** Todo el contenido generado debe estar en español latino neutro. Si el LLM genera texto
en otro idioma (CJK principalmente en `qwen3:8b`), se activa la política de ausencia.

**Implementación:** `shared/text_utils.py` → `has_cjk_characters()` (umbral ≥5 chars CJK)

**Alcance:** Solo se aplica post-generación en Cap 1 actualmente. En fase futura se aplicará a
todos los caps como capa de validación.

---

## RN-008 — Presupuesto máximo por informe: $1.00 USD

**Regla:** El `CostTracker` en el LLM gateway lleva la cuenta acumulada de tokens y costo en USD
por sesión. Si se supera `LLM_BUDGET_LIMIT_USD`, el circuit breaker activa el nivel `paid`
como último recurso y emite alerta.

**Implementación:** `infrastructure/llm/gateway.py` → `CostTracker`

**Nota:** Los modelos `free` tienen costo $0. El presupuesto aplica principalmente al tier `paid`
(< $0.20/MTok). Un informe completo con 6 caps debería costar entre $0 y $0.30.

---

## RN-009 — Divide y vencerás: caps de síntesis largos se subdividen por eje temático

**Regla:** Cuando un capítulo de síntesis requiere analizar múltiples ejes temáticos
independientes, el sistema realiza una llamada LLM por eje y luego agrega los resultados,
en lugar de una única llamada monolítica.

**Motivación (H6-02):** Cap 5 Convergencia tardó 79 minutos con una sola llamada a
Nemotron Ultra 550B (free tier). La causa fue rate limiting o latencia extrema del modelo.
Al subdividir en 3 llamadas de ~5 min al modelo más rápido (Nemotron Super 120B),
el tiempo total estimado baja a ~15 min.

**Aplicación en Cap 5 — Convergencia (diseño Fase 7):**
```
Llamada 1: Convergencia Tecnológica   → api_llm (free, ~120B)
Llamada 2: Convergencia de Mercado    → api_llm (free, ~120B)
Llamada 3: Convergencia Competitiva   → api_llm (free, ~120B)
  ↓
Llamada 4: Síntesis integradora corta → api_llm_synth (synth, ~10% del contexto original)
```

**Implementación (Fase 7):** ✅
- `chain_06a_convergencia_eje.py` — chain genérico con `EJE_TECNOLOGICO`, `EJE_MERCADO`, `EJE_SOCIAL`
- `GenerateConvergencia.execute()` — 3 llamadas paralelas ThreadPoolExecutor(max_workers=3) + 1 síntesis
- `build_chain_06_synth(llm)` en `chain_06_convergencia.py` — síntesis que recibe `{partes}`
- El constructor acepta `chain_eje=None` (ruta legacy monolítica conservada por compatibilidad)

**Regla general:** Si un capítulo devuelve por primera vez en > 30 minutos y el modelo
es free tier, aplicar subdivisión. El umbral de subdivisión es configurable en `.env`
como `LLM_CAP_TIMEOUT_SPLIT_THRESHOLD=1800` (segundos).

---

## RN-010 — Ingesta de PDFs grandes: procesamiento por lotes con liberación de memoria

**Regla:** Los PDFs de más de N páginas (`PDF_BATCH_SIZE_PAGES=20`, configurable) se
ingestaran en lotes secuenciales. Tras cada lote, se libera la memoria de Ollama
explícitamente antes de continuar.

**Motivación (H6-03):** El PDF Convergencia (~120 páginas) falló por OOM tras 23 min
de embeddings secuenciales. El proceso agotó la VRAM de 8GB antes de completar.

**Algoritmo de ingesta por lotes:**
```
1. Abrir PDF y calcular total_paginas
2. Para cada lote [i*N, (i+1)*N]:
   a. Extraer texto de las páginas del lote
   b. Verificar si los chunks ya existen en BD (SHA-256 del texto) — skip si sí
   c. Chunk → embed (nomic-embed-text) → store en pgvector
   d. POST http://127.0.0.1:11434/api/generate {keep_alive:0} para liberar VRAM
   e. Log: "Lote i/total completado en Xs"
3. Log: "PDF completamente ingestado — N chunks totales"
```

**Implementación (Fase 7):** ✅
- `infrastructure/sources/pdf_ingestor.py` — `PdfIngestor.ingest_batched(pdf_path, empresa_id, titulo, autor, año)`
- Anti-duplicados por `hashlib.sha256(chunk_texto).hexdigest()` guardado en JSONB `metadatos->>'chunk_sha256'`
- Si un lote falla: loguear el error, continuar con el siguiente lote (degradación graceful)
- `scripts/ingest_pdf.py` convertido en thin wrapper del `PdfIngestor` — DT-002 cerrado
