# Arquitectura del Sistema — Informes de Inteligencia Competitiva

**Versión:** 8 (post Fase 8 — ruff limpio + historial UI + test E2E Cap5)
**Última actualización:** 2026-07-06
**Propósito:** documento vivo de referencia arquitectónica. Las decisiones cerradas
viven en los ADRs; este documento describe el sistema como está construido y hacia
dónde va.

---

## 1. Visión del producto

Un sistema que, partiendo de **información preliminar sobre una empresa** (nombre,
industria, descripción básica), genera automáticamente un **informe de vigilancia e
inteligencia competitiva** estructurado, citado y listo para la toma de decisiones
empresariales.

El informe incluye:
- Descripción detallada de la empresa y su posición sectorial
- Clasificación GICS del sector industrial
- Benchmarking de 14 competidores directos e indirectos
- Análisis de tendencias tecnológicas, económicas y sociales del sector
- Mapeo del ecosistema (local Medellín + global)
- Convergencias estratégicas identificadas
- Accionables y recomendaciones concretas
- Resumen ejecutivo + referencias en APA 7

**Caso de referencia para el piloto:** Compañía de Galletas NOEL SAS (Grupo Nutresa).

---

## 2. Principios arquitectónicos

| Principio | Implicación práctica |
|-----------|----------------------|
| **Separación de capas (SoC)** | `presentation/` no conoce a `data/`; `domain/` no importa librerías externas |
| **Dependency Agnosticism** | Todo acceso externo pasa por un wrapper en `infrastructure/`; el dominio no depende de langchain, httpx ni pgvector directamente |
| **Local-primero** | Ollama en el host; la API externa solo se invoca si el local no supera el umbral de calidad. **Solo modelos free o económicos** (ADR-006) |
| **Datos ausentes = condición de recuperación** | Si el retrieval no supera el umbral, NO se llama al LLM; se inserta un párrafo de ausencia estándar |
| **Citación trazable** | Toda afirmación proviene de un chunk con fuente verificable; no hay alucinación por diseño |
| **Presupuesto máximo** | ≤ 1 USD por informe completo (controlado en el LLM gateway) |

---

## 3. Capas del sistema

```
┌─────────────────────────────────────────────────────┐
│  presentation/         Streamlit UI (solo renderiza)│
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│  domain/               Orquestación del DAG          │
│    · use cases: GenerateEmpresaDescription,          │
│                ClassifyGICS, GenerateBenchmarking,   │
│                GenerateTendencias, GenerateEcosistema │
│    · chains LCEL: chain_01…chain_05                  │
│    · política de datos ausentes (absent_data.py)     │
│    · DAG de capítulos orquestado por GenerateInforme (ADR-008)            │
└───────┬───────────────────────────────┬──────────────┘
        │                               │
┌───────▼───────────┐       ┌───────────▼──────────────┐
│  infrastructure/  │       │  data/                   │
│  · LLM gateway         │  │  · repositories           │
│  · WebConnector        │  │  · models (ORM)           │
│  · OpenAlexConnector   │  │  · database (engine)      │
│  · Embedder            │  └──────────────────────────┘
│  · Chunker             │
│  · PGVectorStore       │
└───────────────────┘
        │
┌───────▼───────────────────────────────────────────┐
│  shared/              tipos, constantes, config   │
│  · Settings (pydantic-settings, lru_cache)        │
│  · DTOs: WebResult, ChunkResult,                  │
│          DescripcionEmpresa, ClasificacionGICS,   │
│          CapBenchmarking, Referencia, InformePiloto│
│  · Constantes: GICS_GROUPS (25 grupos)            │
└───────────────────────────────────────────────────┘
```

---

## 4. Flujo de generación de un informe

```
Input usuario: {nombre_empresa}
                         │
                         ▼
          ┌──────────────────────────┐
          │  N0: Fundacionales       │
          │  · Prompt-01: Descripción│ ← web RUES+CIIU (WebConnector) → OllamaGatewayLLM
          │  · Prompt-02: GICS       │ ← 25 grupos en system prompt (sin retrieval)
          │  · Prompt-00: Ecuaciones │ ← genera queries de búsqueda por canal
          └──────────────┬───────────┘
                         │  (barrera: Prompt-01 debe completar antes de N1)
          ┌──────────────▼───────────────────────────────────┐
          │  N1: Analíticos — ThreadPoolExecutor(workers=3)  │ ← Fase 5F: paralelos
          │  · Cap 2 Benchmarking  ← web on-demand + pgvector│ └─ sesión BD propia
          │  · Cap 3 Tendencial    ← OpenAlex + web + pgvec  │
          │  · Cap 4 Ecosistema    ← web + pgvector           │
          └──────────────┬───────────────────────────────────┘
                         │  (barrera de sincronización → intros N1)
          ┌──────────────▼───────────┐
          │  N2: Síntesis            │
          │  · Cap 5 Convergencia    │ ← retrieval cruzado
          │  · Cap 6 Accionables     │ ← consume salidas N1+N2
          └──────────────┬───────────┘
                         │  (intros N2)
                         │  (barrera de sincronización)
          ┌──────────────▼───────────┐
          │  N3: Meta                │
          │  · Resumen Ejecutivo     │ ← consume informe completo
          │  · Referencias APA 7     │
          └──────────────┬───────────┘
                         │
          ┌──────────────▼───────────┐
          │  Ensamblado              │
          │  · python-docx           │ ← plantilla membrete
          │  · Citación APA 7        │
          └──────────────────────────┘
                         │
                    Output: informe .docx
```

**Barreras de sincronización:**
- Entre N0 y N1: todos los fundacionales deben estar completos antes de iniciar
  los analíticos (cada capítulo N1 usa el output de Prompt-01 como contexto).
- Dentro de N1: los 3 caps corren en paralelo; la barrera es `f2/f3/f4.result()`.
  Los párrafos intro se añaden después de esta barrera (secuencial, API free).
- Entre N1 y N2: los 3 capítulos N1 deben estar completos antes de Cap 5/6.
- Entre N2 y N3: Cap 6 completo antes del resumen ejecutivo.

---

## 5. Componentes construidos (estado actual)

### Fase 0 ✅

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| Settings | `shared/config.py` | Singleton con pydantic-settings; lee `.env` |
| Engine + Session | `data/database.py` | Conexión PostgreSQL schema-aware (`informes_ic`) |
| ORM: Empresa | `data/models/empresa.py` | Tabla de empresas analizadas |
| ORM: HistorialInforme | `data/models/historial_informe.py` | Registro de cada informe generado |
| ORM: DocumentoLocal | `data/models/documento_local.py` | PDFs manuales (EMIS, sectoriales) |
| ORM: EmbeddingVectorial | `data/models/embedding_vectorial.py` | Chunks embeds (`VECTOR(768)`) + metadata |
| Scripts | `scripts/create_schema.py` | Crea el schema `informes_ic` y las tablas |

### Fase 2 ✅

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| DTOs retrieval | `shared/types.py` | `WebResult`, `ChunkResult` |
| Constantes GICS | `shared/constants/gics_groups.py` | 25 grupos + `build_gics_prompt_block()` |
| WebConnector | `infrastructure/sources/web_connector.py` | Búsqueda Tavily/DDG; extracción CIIU |
| Chunker | `infrastructure/retrieval/chunker.py` | `chunk_text()` sobre `RecursiveCharacterTextSplitter` |
| Embedder | `infrastructure/retrieval/embedder.py` | httpx directo a Ollama `/api/embeddings` |
| EmbeddingRepository | `data/repositories/embedding_repo.py` | `insert_many()` + `search_similar()` (cosine pgvector) |
| PGVectorStore | `infrastructure/retrieval/pgvector_store.py` | Orquesta chunker + embedder + repo; `ingest()` + `search()` |

### Fase 3 ✅

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| DTOs generación | `shared/types.py` | `DescripcionEmpresa`, `ClasificacionGICS`, `CapBenchmarking` |
| OllamaGatewayLLM | `infrastructure/llm/gateway.py` | `BaseChatModel` httpx directo + tenacity circuit breaker |
| CostTracker (esqueleto) | `infrastructure/llm/gateway.py` | Acumulador de tokens (completado en Fase 5A) |
| build_llm() | `infrastructure/llm/gateway.py` | Factory sin hardcodear modelo (ADR-002) |
| absent_data | `domain/absent_data.py` | Umbral de chunks + párrafo de ausencia estándar |
| chain_01 | `domain/chains/chain_01_descripcion.py` | Cadena LCEL Prompt-01 (descripción empresa) |
| chain_02 | `domain/chains/chain_02_gics.py` | Cadena LCEL Prompt-02 (clasificación GICS) |
| chain_03 | `domain/chains/chain_03_benchmarking.py` | Cadena LCEL Prompt-03 (Cap 2 Benchmarking) |
| GenerateEmpresaDescription | `domain/use_cases/generate_empresa_description.py` | Prompt-01: búsqueda web + LLM |
| ClassifyGICS | `domain/use_cases/classify_gics.py` | Prompt-02: clasificación + parsing output |
| GenerateBenchmarking | `domain/use_cases/generate_benchmarking.py` | Prompt-03: ingesta on-demand + LLM + datos ausentes |

### Fase 4 ✅

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| DTOs ensamblado | `shared/types.py` | `Referencia`, `InformePiloto`; `chunks_usados` en `CapBenchmarking` |
| APA formatter | `infrastructure/citation/apa_formatter.py` | Extrae, formatea y deduplica citas desde JSONB |
| DocxBuilder | `infrastructure/docx_builder.py` | Wrapper python-docx; convierte Markdown básico a estilos Word |
| PilotAssembler | `domain/assembler.py` | Orquesta el .docx del piloto (N0+N1 parcial) |
| InformeRepository | `data/repositories/informe_repo.py` | CRUD de `HistorialInforme` + persistencia costo/tiempo |
| ingest_pdf.py | `scripts/ingest_pdf.py` | CLI ingesta PDF manual con SHA-256 anti-duplicados |

### Fase 5A ✅ — 2026-07-02

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| run_pilot.py | `scripts/run_pilot.py` | CLI completo: verifica servicios → ejecuta caps → guarda .docx → resumen |
| OpenRouterGatewayLLM | `infrastructure/llm/gateway.py` | Wrapper httpx para OpenRouter (OpenAI-compatible); extrae tokens de uso |
| `_PRICING` | `infrastructure/llm/gateway.py` | Tabla de precios USD/token para modelos OpenRouter (free y pago) |
| build_api_llm() | `infrastructure/llm/gateway.py` | Factory para 3 tiers: free/synth/paid → OpenRouterGatewayLLM configurado |
| CostTracker (completo) | `infrastructure/llm/gateway.py` | `add_call()` calcula costo real; `records()` historial; enforcement `within_budget()` |
| CostReport | `shared/types.py` | DTO de costo por llamada LLM (modelo, tokens, USD, capítulo) |
| InformePiloto (actualizado) | `shared/types.py` | Agrega `cost_reports` y `costo_total_usd` |

### Fase 5B ✅ — 2026-07-02

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| OpenAlexConnector | `infrastructure/sources/openalex_connector.py` | Wrapper REST api.openalex.org; polite pool via mailto; reconstruye abstract; silencioso en 503 |
| WebConnector (actualizado) | `infrastructure/sources/web_connector.py` | Nuevo param `force_ddg=True` para tests sin gastar créditos Tavily |
| chain_04_tendencias | `domain/chains/chain_04_tendencias.py` | LCEL para Cap 3 (3.1 TES, 3.2 MECE, 3.3 Casos); tono ejecutivo; nivel de confianza |
| GenerateTendencias | `domain/use_cases/generate_tendencias.py` | 2 búsquedas web + OpenAlex + RAG; tier free OpenRouter; degradación silenciosa sin OpenAlex |
| CapTendencias | `shared/types.py` | DTO Cap 3 con texto, chunks usados, flag retrieval_suficiente |
| InformePiloto (actualizado) | `shared/types.py` | Campo `cap_tendencias: CapTendencias | None = None` |
| PilotAssembler (actualizado) | `domain/assembler.py` | Sección Cap 3 condicional en el .docx |
| run_pilot.py (actualizado) | `scripts/run_pilot.py` | Paso 4/6 Cap 3 via OpenRouter; referencias combinadas Cap 2+3 |
| test_connections.py | `scripts/test_connections.py` | Diagnóstico de 6 servicios; 1 crédito Tavily por ejecución |

### Fase 5C ✅ — 2026-07-06

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| text_utils | `shared/text_utils.py` | `has_cjk_characters()` + `format_web_results_as_context()` |
| chain_01 (refactorizado) | `domain/chains/chain_01_descripcion.py` | Prompt con `{web_context}`, anti-CJK, fallback multi-LLM via `.with_fallbacks()` |
| chain_03 (actualizado) | `domain/chains/chain_03_benchmarking.py` | Regla idioma reforzada |
| chain_04 (actualizado) | `domain/chains/chain_04_tendencias.py` | Regla idioma reforzada |
| GenerateEmpresaDescription | `domain/use_cases/generate_empresa_description.py` | 3 queries web, inyecta `{web_context}`, detección CJK post-generación |
| Embedder (actualizado) | `infrastructure/retrieval/embedder.py` | Retries con backoff `[0,3,8]s` ante HTTP 500 de Ollama |
| gateway (actualizado) | `infrastructure/llm/gateway.py` | Tier `free_alt`, `llm_local_timeout` en `build_llm()` |
| config (actualizado) | `shared/config.py` | `llm_api_free_alt_model`, `llm_local_timeout=300` |
| ADR-006 | `docs/architecture/ADR-006-*` | Política presupuestal: solo modelos free o económicos |

### Fase 5D ✅ — 2026-07-06

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| keep_alive:0 — Embedder | `infrastructure/retrieval/embedder.py` | `"keep_alive": 0` en request de embeddings; descarga el modelo tras cada uso para liberar VRAM |
| keep_alive:0 — Ollama LLM | `infrastructure/llm/gateway.py` | `"keep_alive": 0` en `_call` y `_stream` de `OllamaGatewayLLM`; solo para Ollama (no OpenRouter) |
| chain_05_ecosistema | `domain/chains/chain_05_ecosistema.py` | LCEL Cap 4: secciones 5.1 local, 5.2 global, 5.3 disruptores; reutiliza helpers de chain_04 |
| GenerateEcosistema | `domain/use_cases/generate_ecosistema.py` | 2 búsquedas web (proveedores + alianzas) + RAG + tier free; sin openalex |
| CapEcosistema | `shared/types.py` | DTO Cap 4 con texto, chunks usados, flag retrieval_suficiente |
| InformePiloto (actualizado) | `shared/types.py` | Campo `cap_ecosistema: CapEcosistema \| None = None` |
| PilotAssembler (actualizado) | `domain/assembler.py` | Sección "Capítulo 4. Ecosistema Empresarial" condicional en .docx |
| run_pilot.py (actualizado) | `scripts/run_pilot.py` | Paso 5/7 Cap 4; referencias combinadas Cap 2+3+4 |
| pytest markers slow | `pyproject.toml` + `tests/test_llm.py` + `tests/test_retrieval.py` | Marker `slow` en 7 tests que usan Ollama real; excluibles con `-m "not slow"` |
| test_ecosistema | `tests/test_ecosistema.py` | 9 tests mockeados (4 chain + 5 use case); sin dependencias externas |

### Fase 5F ✅ — 2026-07-06

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| chain_intro | `domain/chains/chain_intro.py` | Cadena LCEL genérica para párrafos introductorios de 2-3 oraciones por capítulo |
| Paralelización N1 | `scripts/run_pilot.py` | Caps 2, 3, 4 en `ThreadPoolExecutor(max_workers=3)`; sesión SQLAlchemy propia por hilo |
| CostTracker wiring | `scripts/run_pilot.py` | `CostTracker` instanciado en `main()` y pasado a todos los `build_api_llm()`; resumen real al final |
| test_chain_intro | `tests/test_chain_intro.py` | 3 tests rápidos (FakeListChatModel) + 1 @slow |

### Fase 6 ✅ — 2026-07-06

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| GenerateInforme | `domain/use_cases/generate_informe.py` | Orquestador completo del pipeline con callback `on_step` (ADR-008) |
| InformeParams / InformeResult | `domain/use_cases/generate_informe.py` | DTOs de entrada/salida del orchestrator |
| app.py | `presentation/app.py` | UI Streamlit (puerto 8503): formulario → progreso 10 pasos → descarga .docx |
| run_pilot.py (refactor) | `scripts/run_pilot.py` | Thin wrapper CLI: argparse → `GenerateInforme.run()` → resumen |
| test_generate_informe | `tests/test_generate_informe.py` | 5 tests rápidos + 1 @slow E2E |

**E2E validado (2026-07-06):** Noel S.A.S. → 10 pasos, 49 headings, ~12k palabras, 19 refs APA, $0.0000.
Ver `docs/decisions/FASE6_HALLAZGOS.md` para tiempos y issues conocidos.

### Fase 7 ✅ — 2026-07-06

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| `_PipelineContext` | `domain/use_cases/generate_informe.py` | Dataclass de estado del pipeline; elimina paso de kwargs entre métodos |
| `_run_n0/n1/n2/n3` | `domain/use_cases/generate_informe.py` | 6 métodos privados; SoC dentro del orchestrator (ADR-009) |
| EmpresaRepository | `data/repositories/empresa_repo.py` | `upsert_by_name()`: crea o recupera empresa; wired en `_run_n3()` |
| `ensure_historial_columns()` | `data/database.py` | Migración idempotente que agrega `tokens_in`/`tokens_out` si no existen |
| PdfIngestor | `infrastructure/sources/pdf_ingestor.py` | Ingesta PDF en lotes de 20 págs + SHA-256 anti-duplicados + keep_alive:0 (RN-010) |
| chain_06a | `domain/chains/chain_06a_convergencia_eje.py` | Chain LCEL genérico para un eje de convergencia (TECNOLÓGICO/MERCADO/SOCIAL) |
| build_chain_06_synth | `domain/chains/chain_06_convergencia.py` | Chain síntesis que recibe `{partes}` concatenadas de los 3 ejes |
| GenerateConvergencia (actualizado) | `domain/use_cases/generate_convergencia.py` | 3 ejes en `ThreadPoolExecutor(max_workers=3)` + síntesis; `chain_eje=None` → ruta legacy |

**E2E referencia (Fase 7):** 97 tests fast + `docs/decisions/FASE7_HALLAZGOS.md`

### Fase 8 ✅ — 2026-07-06

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| `# noqa: E501` en prompts | `chain_01`, `03`, `04`, `05`, `06` + `test_chain_intro` | P1 DT-007: silencia E501 en strings de prompt (>100 chars legítimos) |
| `list_recientes(limit=20)` | `data/repositories/informe_repo.py` | P2 DT-008: JOIN con Empresa, ORDER BY created_at DESC, retorna `list[tuple[HistorialInforme, str]]` |
| `_render_historial()` | `presentation/app.py` | P2 DT-008: tab Historial con 4 estados (error/vacío/datos/descarga); `key=str(informe.id)` para unicidad |
| `st.tabs()` | `presentation/app.py` | P2 DT-008: divide UI en "Generar Informe" y "Historial" |
| `test_informe_repo.py` | `tests/test_informe_repo.py` | P2: 3 tests rápidos mocked para `list_recientes` |
| `test_convergencia_e2e.py` | `tests/test_convergencia_e2e.py` | P3 DT-005: `@pytest.mark.slow`; verifica 3 ejes paralelos < 30 min con servicios reales |

### Deuda técnica cerrada

| ID | Descripción | Fase | Estado |
|----|-------------|------|--------|
| DT-001 | `generate_informe.py` >300 líneas | 7 | ✅ Resuelto — ADR-009 |
| DT-002 | PDF ingesta en `scripts/` | 7 | ✅ Resuelto — `PdfIngestor` en infrastructure/ |
| DT-003 | Cap 5 monolítico ~79 min | 7 | ✅ Resuelto — 3 ejes paralelos |
| DT-007 | ~38 errores ruff E501 en chains | 8 | ✅ Resuelto — `# noqa: E501` + refactor |
| DT-008 | UI sin historial de informes | 8 | ✅ Resuelto — `st.tabs` + `list_recientes` |

### Pendiente (Fase 9+)

| ID | Fase | Componente | Descripción |
|----|------|-----------|-------------|
| DT-004 | monitor | `generate_informe.py` ≥380 líneas | Si el archivo crece, separar `_run_n1` en módulo propio |
| DT-005 | 9 | E2E Cap5 con servicios reales | Test creado (`test_convergencia_e2e.py`); pendiente ejecutar con Ollama + OpenRouter reales |
| DT-006 | 9 | PDF 120 págs validación real | `InformeConvergenciaLocal2026V3RvADAA.pdf` — confirmar no-OOM post-fix |
| DT-009 | 9 | Validación idioma global | `has_cjk_characters()` solo cubre Cap 1; extender a todos los caps N1+ |
| DT-010 | 9 | CostTracker en Ollama | Ollama no expone tokens; registrar tiempo como proxy de costo en `HistorialInforme` |
| DT-011 | 9+ | Fuentes EMIS/sectoriales | Ingestar PDFs privados con `PdfIngestor` ya disponible |
| DT-012 | 9+ | Multi-empresa / cola | UI para generar múltiples informes; historial paginado (actualmente muestra 20) |

---

## 6. Infraestructura del entorno de desarrollo

| Servicio | Ubicación | Config |
|----------|-----------|--------|
| PostgreSQL + pgvector | `repositorio_postgres` Docker, `localhost:5434` | DB: `repositorio_ctie`, schema: `informes_ic` |
| Ollama | Host (no Docker) | `http://127.0.0.1:11434` |
| Modelos Ollama | Ollama host | `nomic-embed-text:latest` (embeddings 768d, 137MB), `qwen2.5:7b` (analítico, 4.7GB) |
| Modelos API | OpenRouter | Tier free: `nemotron-super/ultra`, `llama-3.3-70b:free`; pago (fallback): `gemma-3-27b-it` — política ADR-006 |
| Python runtime | `.venv` gestionado por `uv` | Python 3.12 |

**Variables de entorno críticas** (en `.env`, nunca en código):

```env
DATABASE_URL=postgresql://...             # conexión a repositorio_ctie
LLM_LOCAL_EMBED_MODEL=nomic-embed-text:latest
LLM_LOCAL_DRAFT_MODEL=qwen2.5:7b
LLM_LOCAL_ANALYTIC_MODEL=qwen2.5:7b      # máx 7B en WSL 8GB VRAM
# OpenRouter (Fase 5A+)
OPENROUTER_API_KEY=sk-or-...
LLM_API_FREE_MODEL=nvidia/nemotron-3-super-120b-a12b:free
LLM_API_SYNTH_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
LLM_API_PAID_MODEL=google/gemma-3-27b-it
LLM_API_KEY=...
OLLAMA_BASE_URL=http://127.0.0.1:11434
RAG_SIMILARITY_THRESHOLD=0.7
RAG_TOP_K=10
TAVILY_API_KEY=                          # vacío = fallback a DDG
LLM_MAX_TOKENS_INPUT=8000
LLM_MAX_TOKENS_OUTPUT=4000
LLM_BUDGET_LIMIT_USD=1.0
LLM_CIRCUIT_BREAKER_MAX_RETRIES=3
```

---

## 7. Decisiones arquitectónicas (ADRs)

| ADR | Título | Estado |
|-----|--------|--------|
| ADR-001 | RAG propio reemplaza NotebookLM | Aceptado |
| ADR-002 | Routing local-primero con escalado a API | Aceptado |
| ADR-003 | Estrategia de fuentes doble vía | Aceptado |
| ADR-004 | LangChain como framework de orquestación | Aceptado |
| ADR-005 | Diseño de la capa de retrieval | Aceptado |
| ADR-006 | Presupuesto: solo modelos gratuitos o económicos | Aceptado |
| ADR-007 | Gestión de memoria WSL2: keep_alive:0 + OPENBLAS threads | Aceptado |
| ADR-008 | GenerateInforme orchestrator + patrón on_step callback | Aceptado |
| ADR-009 | Refactor orchestrator Fase 7: límite 300 líneas aceptado + imports diferidos | Aceptado |

---

## 8. Patrones establecidos (copiar en Fase 4+)

### Patrón de acceso a Ollama (httpx directo)

```python
# infrastructure/retrieval/embedder.py — referencia para embeddings
resp = httpx.post(
    f"{settings.ollama_base_url}/api/embeddings",
    json={"model": settings.llm_local_embed_model, "prompt": text},
    timeout=30,
)
resp.raise_for_status()
return resp.json()["embedding"]

# infrastructure/llm/gateway.py — referencia para chat
resp = httpx.post(
    f"{self.base_url}/api/chat",
    json={"model": self.model, "messages": ollama_msgs, "stream": False},
    timeout=self.timeout,
)
resp.raise_for_status()
return resp.json()["message"]["content"]
```

### Patrón de raw SQL con schema calificado

```python
# data/repositories/embedding_repo.py — referencia
table = EmbeddingVectorial.__table__.fullname  # "informes_ic.embeddings_vectoriales"
sql = text(f"SELECT ... FROM {table} ...")
```

### Patrón de cadena LCEL (chain → use case)

```python
# domain/chains/chain_0N_*.py — definir la cadena
def build_chain_0N(llm: OllamaGatewayLLM) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([...])
    return prompt | llm | StrOutputParser()

# domain/use_cases/use_case_0N.py — inyectar, no instanciar
class UseCase0N:
    def __init__(self, chain: Runnable, ...) -> None:  # inyección de dependencias
        self._chain = chain

    def execute(self, ...) -> DTO:
        resultado = self._chain.invoke({...})
        return DTO(...)
```

### Patrón de lectura de config (sin hardcodear modelos)

```python
# Correcto — el nombre del modelo viene del .env
model = settings.llm_local_analytic_model

# Incorrecto — viola CLAUDE.md Tier 1
model = "qwen2.5"
```

### Patrón de conversión WebResult → ingest

```python
# domain/use_cases/ — conversión antes de llamar al store
web_results = self._web_connector.search(query)
if web_results:
    self._store.ingest(
        texts=[r.content for r in web_results],
        fuente_tipo="web",
        urls=[r.url for r in web_results],
        metadatos_extra=[r.metadatos for r in web_results],  # APA: título, año, dominio
    )
```

### Patrón de ensamblado (Fase 4+)

```python
# domain/assembler.py — el dominio no importa python-docx directamente
from ic.infrastructure.docx_builder import DocxBuilder
from ic.infrastructure.citation.apa_formatter import build_references_section

refs = build_references_section(cap.chunks_usados)     # deduplica por URL
informe = InformePiloto(empresa=..., gics=..., cap_benchmarking=cap, referencias=refs)
assembler = PilotAssembler(DocxBuilder(settings.docx_template_path or None))
ruta = assembler.assemble(informe, output_path)
```

### Patrón de escalado a OpenRouter (Fase 5A+)

```python
# infrastructure/llm/gateway.py — usar build_api_llm() con el tier correcto
from ic.infrastructure.llm.gateway import build_api_llm, CostTracker

tracker = CostTracker(budget_limit=settings.llm_budget_limit_usd)

# Caps analíticos (N1): tier free — Nemotron Super
llm_free = build_api_llm(settings, tier="free", cost_tracker=tracker)

# Caps síntesis (N2, N3): tier synth — Nemotron Ultra
llm_synth = build_api_llm(settings, tier="synth", cost_tracker=tracker)

# El tracker lleva el acumulado entre todas las llamadas
print(f"Costo total: ${tracker.total_cost():.4f} USD")
print(f"Tokens: {tracker.total_tokens()}")
```

### Patrón de citación APA desde chunks

```python
# infrastructure/citation/apa_formatter.py
# Los chunks llevan metadatos JSONB con {titulo, fuente_nombre, año, autor, fecha_acceso}
# Si un campo falta → usar código APA de ausencia (nunca inventar)
meta = extract_citation_metadata(chunk)   # lee chunk.metadatos
inline = format_inline(meta)              # "(fortune.com, 2024)"
ref = format_reference(meta)             # Referencia completa APA 7
```

---

## 9. Guía rápida de comandos

```bash
# Verificar servicios
docker ps | grep repositorio_postgres      # BD corriendo en :5434?
curl http://127.0.0.1:11434/api/tags       # Ollama responde?
curl http://127.0.0.1:11434/api/tags | python3 -c \  # modelos disponibles con tamaño
  "import json,sys; [print(m['name'], m['size']//1e9,'GB') for m in json.load(sys.stdin)['models']]"

# Desarrollo
uv sync                                    # sincronizar deps
uv run pytest -m "not slow" -q             # suite rápida (≥100 tests, sin Ollama/BD)
uv run pytest tests/ -v                    # suite completa
uv run python scripts/create_schema.py    # re-crear schema si hay cambios ORM

# Generar informe desde CLI (Fase 5A)
uv run python scripts/run_pilot.py --empresa "Noel S.A.S." --ciiu 1081

# Smoke test gateway LLM
uv run python -c "
from ic.shared.config import get_settings
from ic.infrastructure.llm.gateway import build_llm
from ic.domain.chains.chain_02_gics import build_chain_02
from ic.domain.use_cases.classify_gics import ClassifyGICS
s = get_settings()
llm = build_llm(s)
chain = build_chain_02(llm)
uc = ClassifyGICS(chain)
result = uc.execute('Grupo Nutresa', 'Empresa colombiana de alimentos procesados...')
print(result.grupo_gics)
"

# Verificación rápida de embeddings
uv run python -c "
from ic.shared.config import get_settings
from ic.infrastructure.retrieval.embedder import Embedder
e = Embedder(get_settings())
v = e.embed('test')
print(f'OK: {len(v)} dims')
"
```
