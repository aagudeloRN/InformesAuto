# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/).
Versiones siguiendo [SemVer](https://semver.org/lang/es/).

---

## [0.5.0] — 2026-07-02

### Added
- `scripts/run_pilot.py`: CLI completo para generar el informe piloto sin UI.
  Acepta `--empresa` (requerido), `--ciiu` (opcional, se extrae auto) y `--salida`
  (opcional). Verifica Ollama y PostgreSQL al arrancar, muestra progreso por paso
  con tiempos individuales, imprime resumen de ejecución con barra gráfica y costo.
  Suprime logs verbosos de SQLAlchemy para mantener la salida legible.
- `infrastructure/llm/gateway.py`: nueva clase `OpenRouterGatewayLLM(BaseChatModel)` —
  wrapper httpx para la API OpenAI-compatible de OpenRouter; extrae `usage.prompt_tokens`
  y `usage.completion_tokens` de cada respuesta; aplica enforcement de presupuesto
  (`within_budget()`) antes de cada llamada; manejo de SSE para streaming; tenacity
  circuit breaker con backoff más amplio (max 30s) para respetar rate limits de free tier.
- `infrastructure/llm/gateway.py`: tabla de precios `_PRICING` como constante de módulo
  (USD por token in/out): `nemotron-super:free` $0, `nemotron-ultra:free` $0,
  `google/gemma-3-27b-it` $0.10/$0.20 MTok. Extensible sin tocar código de aplicación.
- `infrastructure/llm/gateway.py`: `build_api_llm(settings, tier, cost_tracker)` —
  factory para 3 tiers: `free` → Nemotron Super (caps analíticos), `synth` → Nemotron
  Ultra (síntesis), `paid` → Gemma 3 27B (respaldo con rate limit).
- `infrastructure/llm/gateway.py`: `CostTracker.add_call(model, tokens_in, tokens_out)`
  calcula costo real desde `_PRICING`; `records()` devuelve historial completo por
  llamada; `add_local_call()` mantiene compatibilidad con código existente.
- `shared/types.py`: `@dataclass CostReport` con campos `modelo`, `tokens_in`,
  `tokens_out`, `costo_usd`, `capitulo`.
- `shared/types.py`: `InformePiloto` agrega `cost_reports: list[CostReport]` y
  `costo_total_usd: float` para transportar el desglose económico hasta el assembler.
- `shared/config.py`: nuevos campos `openrouter_base_url`, `openrouter_api_key`,
  `llm_api_free_model`, `llm_api_synth_model`, `llm_api_paid_model`; campos legados
  marcados como opcionales con defaults vacíos para no romper `.env` existentes.
- `.env.example`: bloque OpenRouter documentado con los 3 tiers y comentarios de
  cuándo usar cada uno; variables legadas marcadas como compatibilidad.
- `docker-compose.yml`: nota de conflicto de puerto: el container `repositorio_postgres`
  ya ocupa `5434`; instrucciones para evitar el conflicto en el entorno compartido.
- `.gitignore`: excluir `output/` (informes generados, no deben ir al repo).
- `tests/test_cost_tracker.py`: 10 tests — costo $0 en local y free, cálculo correcto
  en modelos pago, enforcement de presupuesto, acumulación de llamadas, campos de
  registros, tabla de precios, factory `build_api_llm`.

### Changed
- `data/repositories/informe_repo.py`: `update_completado()` acepta parámetro
  opcional `tiempo_s: float | None` para persistir la duración real de la generación
  en `HistorialInforme.tiempo_generacion_s`.

### Fixed
- Logs de SQLAlchemy e httpx suprimidos en `run_pilot.py` (nivel WARNING) para
  mantener la salida del CLI legible; los logs de BD solo aparecen en pytest.

### Notes
- **Prueba E2E validada:** `run_pilot.py` generó exitosamente `output/noel_sas_informe.docx`
  con Cap 1 + GICS + Cap 2 en 279s usando `qwen2.5:7b` local.
- **Benchmark de tiempo local:** Cap 1 ~32s, GICS ~4s, Cap 2 ~243s. La duración de
  Cap 2 con modelo local es la motivación principal para escalar analíticos a OpenRouter.
- **Suite de tests:** 37/37 pasando (27 heredados + 10 nuevos).
- **OpenRouter pendiente de activar:** el gateway está construido pero requiere
  `OPENROUTER_API_KEY` + las 3 variables de modelo en `.env` para funcionar.

---

## [0.4.0] — 2026-06-25

### Added
- `shared/types.py`: DTOs `Referencia` e `InformePiloto`; campo `chunks_usados: list[ChunkResult]`
  en `CapBenchmarking` para transportar evidencia al ensamblador sin re-query.
- `shared/types.py`: campo `metadatos: dict | None` en `WebResult` para transportar
  metadatos APA desde el conector hasta el almacén vectorial.
- `shared/config.py`: vars `docx_template_path` y `docx_output_dir` (con defaults seguros).
- `infrastructure/citation/apa_formatter.py`: `CitationMetadata`, `extract_citation_metadata()`,
  `format_inline()`, `format_reference()`, `build_references_section()` — deduplication por
  URL + orden alfabético. APA básico: fuente, año, URL; sin autor → dominio; sin año → `"s.f."`.
- `infrastructure/docx_builder.py`: `DocxBuilder` wrapper sobre `python-docx` con
  `add_markdown_section()` que convierte Markdown básico (##, **negrita**, listas) a estilos
  Word via regex; carga plantilla `.dotx` si existe, documento limpio como fallback.
- `domain/assembler.py`: `PilotAssembler.assemble(InformePiloto, output_path) → str`; produce
  el .docx del piloto con portada, Cap 1 (descripción), GICS, Cap 2 (benchmarking),
  Referencias APA 7, nota de generación automática.
- `data/models/documento_local.py`: columna `metadatos JSONB` para SHA-256 anti-duplicados.
- `data/repositories/informe_repo.py`: `InformeRepository` — `create()`, `update_estado()`,
  `update_completado()`, `get_by_id()`.
- `scripts/ingest_pdf.py`: CLI de ingesta manual de PDFs; SHA-256 anti-duplicados;
  extrae metadatos del PDF (`/Title`, `/Author`, `/CreationDate`); fallback a args CLI;
  aplica `ALTER TABLE … ADD COLUMN IF NOT EXISTS` idempotente al arrancar.
- `tests/test_assembler.py`: 8 tests — 3 DocxBuilder, 3 APA formatter, 1 assembler con
  datos fijos (sin Ollama), 1 e2e Noel completo (web + Ollama + BD + .docx).
- `pyproject.toml`: dependencia `pypdf>=4.0`.

### Changed
- `infrastructure/sources/web_connector.py`: `_search_tavily()` y `_search_ddg()` pueblan
  `WebResult.metadatos` con `{titulo, fuente_nombre, año, fecha_acceso, autor}` —
  condición previa para citación APA correcta.
- `domain/use_cases/generate_benchmarking.py`: `CapBenchmarking` ahora recibe
  `chunks_usados=chunks` (o `[]` si retrieval insuficiente).

---

## [0.3.0] — 2026-06-25

### Added
- `infrastructure/llm/gateway.py`: `OllamaGatewayLLM(BaseChatModel)` — wrapper httpx
  directo a Ollama `/api/chat` con circuit breaker tenacity y soporte de streaming.
- `infrastructure/llm/gateway.py`: `CostTracker` — acumulador de costo y tokens por sesión.
- `infrastructure/llm/gateway.py`: `build_llm(settings)` — factory que construye el LLM
  desde settings sin hardcodear el modelo (ADR-002).
- `domain/absent_data.py`: política de datos ausentes — `check_retrieval_sufficient()` +
  `build_absent_paragraph()` (ADR-002).
- `domain/chains/chain_01_descripcion.py`: cadena LCEL para Prompt-01 (descripción empresa).
- `domain/chains/chain_02_gics.py`: cadena LCEL para Prompt-02 (clasificación GICS);
  el bloque de 25 grupos se interpola en el system prompt al importar el módulo.
- `domain/chains/chain_03_benchmarking.py`: cadena LCEL para Prompt-03 (Cap 2 Benchmarking)
  + `format_chunks_as_context()`.
- `domain/use_cases/generate_empresa_description.py`: use case Prompt-01 con retrieval web.
- `domain/use_cases/classify_gics.py`: use case Prompt-02 con parsing de salida LLM.
- `domain/use_cases/generate_benchmarking.py`: use case Prompt-03 con ingesta on-demand +
  política de datos ausentes.
- `shared/types.py`: DTOs `DescripcionEmpresa`, `ClasificacionGICS`, `CapBenchmarking`.
- `tests/test_llm.py`: 6 tests nuevos (4 con Ollama real, 2 lógica pura).

### Fixed
- `generate_benchmarking.py`: conversión correcta de `list[WebResult]` a `list[str]` +
  `list[str | None]` antes de llamar a `PGVectorStore.ingest()`.

---

## [0.2.0] — 2026-06-22

### Added
- `shared/types.py`: DTOs `WebResult`, `ChunkResult`.
- `shared/constants/gics_groups.py`: 25 grupos GICS + `build_gics_prompt_block()`.
- `infrastructure/sources/web_connector.py`: `WebConnector` con fallback Tavily → DDG
  y extracción de CIIU por regex.
- `infrastructure/retrieval/chunker.py`: wrapper sobre `RecursiveCharacterTextSplitter`.
- `infrastructure/retrieval/embedder.py`: httpx directo a Ollama `/api/embeddings` (768d).
- `data/repositories/embedding_repo.py`: `EmbeddingRepository` con búsqueda coseno pgvector.
- `infrastructure/retrieval/pgvector_store.py`: `PGVectorStore` — orquesta ingest + search.
- `tests/test_retrieval.py`: 9 tests nuevos (retrieval end-to-end).
- `docs/architecture/ADR-005-retrieval-layer-design.md`: 6 decisiones de diseño del retrieval.
- `docs/decisions/FASE2_HALLAZGOS.md`: hallazgos técnicos de Fase 2.

### Fixed
- Raw SQL en `EmbeddingRepository` usa nombre de tabla calificado con schema
  (`Model.__table__.fullname`) para evitar fallos de `search_path` al correr la suite completa.

---

## [0.1.0] — 2026-06-22

### Added
- `docker-compose.yml`: PostgreSQL + pgvector:pg16, puerto 5434, bind mount en host.
- `shared/config.py`: `Settings` con pydantic-settings + `get_settings()` con `lru_cache`.
- `data/database.py`: engine + `SessionLocal` con `search_path` hacia `informes_ic`.
- `data/models/`: 4 modelos ORM (empresas, historial_informes, documentos_locales,
  embeddings_vectoriales `VECTOR(768)`).
- `scripts/create_schema.py`: crea el schema `informes_ic` y las tablas.
- `.claude/settings.json` + hooks: `check-secrets.sh`, `check-hardcoded-models.sh`,
  `format-python.sh`.
- `docs/architecture/ADR-001` a `ADR-004`: decisiones arquitectónicas fundacionales.
- `docs/decisions/FASE0_HALLAZGOS.md`: hallazgos técnicos de Fase 0.
- `tests/test_database.py`: 4 smoke tests de BD.
