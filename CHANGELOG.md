# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/).
Versiones siguiendo [SemVer](https://semver.org/lang/es/).

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
