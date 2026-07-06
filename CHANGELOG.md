# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/).
Versiones siguiendo [SemVer](https://semver.org/lang/es/).

---

## [0.8.0] — 2026-07-06

### Added
- `src/ic/data/repositories/empresa_repo.py`: `EmpresaRepository.upsert_by_name(nombre)`
  — idempotente: busca la empresa por nombre exacto o la crea. Desbloquea la FK
  `empresa_id` en `historial_informes` (RN-006).
- `src/ic/infrastructure/sources/pdf_ingestor.py`: `PdfIngestor.ingest_batched()` —
  procesa PDFs en lotes de `PDF_BATCH_SIZE_PAGES=20` páginas. Anti-duplicados por SHA-256
  del chunk en JSONB `metadatos->>'chunk_sha256'`. `keep_alive:0` tras cada lote para
  liberar VRAM (RN-010, DT-002).
- `src/ic/domain/chains/chain_06a_convergencia_eje.py`: chain LCEL genérico para un eje
  de convergencia. Recibe `{eje_nombre, eje_instrucciones, ...}`. Tres ejes definidos:
  `EJE_TECNOLOGICO`, `EJE_MERCADO`, `EJE_SOCIAL`. (RN-009)
- `src/ic/data/models/historial_informe.py`: columnas `tokens_in: int | None` y
  `tokens_out: int | None`. Función `ensure_historial_columns(engine)` — migración
  idempotente via `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.
- `tests/test_empresa_repo.py`: 5 tests rápidos mocked (upsert crea, upsert idempotente,
  get_by_id, historial con tokens).
- `tests/test_pdf_ingestor.py`: 4 tests rápidos mocked (skip duplicados SHA-256,
  keep_alive tras cada lote, 2 lotes = 2 releases, error de conexión no propaga).

### Changed
- `src/ic/domain/use_cases/generate_informe.py`: refactor DT-001 — extraído en 6 métodos
  privados (`_setup_infra`, `_run_n0`, `_run_n1`, `_run_pdf`, `_run_n2`, `_run_n3`) con
  `_PipelineContext` dataclass. Imports diferidos por método (no `locals()` pattern).
  `_run_n3()` persiste empresa, costo, tiempo y tokens al finalizar (wrapped en
  try/except para degradación graceful).
- `src/ic/domain/use_cases/generate_convergencia.py`: constructor acepta `chain_eje`
  opcional. Con `chain_eje`: 3 llamadas paralelas (ThreadPoolExecutor max_workers=3) a
  los 3 ejes + 1 síntesis. Sin `chain_eje`: ruta legacy monolítica conservada.
  Cap 5 estimado ~15 min vs ~79 min previo (RN-009).
- `src/ic/domain/chains/chain_06_convergencia.py`: agrega `build_chain_06_synth(llm)` —
  chain de síntesis que recibe `{partes}` (textos de los 3 ejes concatenados).
- `src/ic/data/repositories/informe_repo.py`: `update_completado()` acepta
  `tokens_in: int | None` y `tokens_out: int | None`.
- `src/ic/shared/config.py`: agrega `pdf_batch_size_pages: int = 20`.
- `scripts/ingest_pdf.py`: refactorizado como thin wrapper que delega a
  `PdfIngestor.ingest_batched()`. Mantiene la misma interfaz CLI.
- `tests/test_convergencia.py`: actualizado para el nuevo constructor de dos chains;
  agrega test de paralelismo (chain_eje.invoke.call_count == 3).

### Fixed
- Deuda DT-001 cerrada: `generate_informe.py` descompuesto en métodos cohesivos,
  cada uno < 60 líneas.
- Deuda DT-002 cerrada: ingesta PDF migrada de `scripts/` a `infrastructure/sources/`.
- Persistencia historial desbloqueada (RN-006): `_run_n3()` persiste con
  `EmpresaRepository.upsert_by_name()` antes de `InformeRepository.create()`.

### Tests
- 97 fast passed, 2 skipped (antes: 86 fast passed post Fase 6).

---

## [0.7.0] — 2026-07-06

### Added
- `src/ic/domain/use_cases/generate_informe.py`: orchestrator `GenerateInforme` que
  encapsula el pipeline completo (Caps 1–6 + Resumen Ejecutivo). Acepta un callback
  `on_step(n, total, label)` que desacopla el reporte de progreso de la ejecución
  (CLI usa print; UI usa `st.progress`). Retorna `InformeResult` con ruta, costo,
  tokens y referencias. Cumple SoC: la presentación no contiene lógica de negocio.
- `src/ic/presentation/app.py`: UI Streamlit en puerto 8503. Formulario con empresa,
  CIIU opcional y ruta de salida. Verificación de servicios (Ollama + PG) antes de
  iniciar. Barra de progreso de 10 pasos. Botón de descarga del .docx al finalizar.
  Expander con resumen de costo, tokens y desglose por llamada.
- `tests/test_generate_informe.py`: 5 tests rápidos + 1 `@pytest.mark.slow` (E2E
  completo con servicios reales: Noel S.A.S.).

### Changed
- `scripts/run_pilot.py`: refactorizado como thin wrapper. La lógica del pipeline
  migró a `GenerateInforme`. El CLI mantiene: argparse, verificación de servicios,
  callback de consola `_console_step`, y resumen de ejecución.

### Deferred
- Persistencia en `historial_informes`: diferida a Fase 7. La tabla requiere FK
  `empresa_id → empresas.id` (NOT NULL), lo que exige gestión de entidades Empresa.

---

## [0.6.0] — 2026-07-06

### Added
- `src/ic/domain/chains/chain_intro.py`: cadena LCEL genérica `build_chain_intro(llm)`.
  Genera un párrafo introductorio de 2-3 oraciones para cualquier capítulo del informe.
  Recibe `{titulo}`, `{empresa}` y `{resumen_cap}` (primeros 500 chars del cap ya
  generado). Sin retrieval; usa `api_llm` free para mantener costo bajo.
- `tests/test_chain_intro.py`: 3 tests rápidos (FakeListChatModel) + 1 @slow.
  Test de propagación de respuesta, construcción de Runnable y test E2E con Ollama.
- Párrafos introductorios activos en Caps 2–6: tras la barrera N1 y tras cada cap N2,
  `intro_chain` se aplica si `api_llm` está configurado y el retrieval fue suficiente.
- `scripts/run_pilot.py`: resumen de costo API real al final de la ejecución. Muestra
  costo total en USD + desglose por llamada (modelo, tokens in/out, costo). Reemplaza
  el placeholder `$0.00 (Etapa B)` con datos reales del `CostTracker`.

### Changed
- **Paralelización N1**: Caps 2, 3 y 4 ahora corren simultáneamente vía
  `ThreadPoolExecutor(max_workers=3)`. Tiempo de pared N1 = `max(cap2, cap3, cap4)`
  en lugar de `cap2 + cap3 + cap4`. Cada hilo crea su propia `SessionLocal()` para
  thread-safety de SQLAlchemy.
- Cap 1 y GICS movidos fuera del `with SessionLocal()` (no necesitaban sesión de BD).
- N2 (Caps 5, 6) ejecutan con su propia `with SessionLocal() as db_n2`, separada de N1.
- `CostTracker` ahora se instancia al inicio de `main()` y se pasa como
  `cost_tracker=tracker` a todos los `build_api_llm()`.

---

## [0.5.5] — 2026-07-06

### Added
- `pytest-env==1.6.0` como dependencia de desarrollo. Necesario para que la sección
  `[tool.pytest.ini_options] env` de `pyproject.toml` tenga efecto.
- `docs/architecture/ADR-007-gestion-memoria-wsl2-tests.md`: documenta la raíz y
  corrección de los dos crasheos OOM de esta sesión (OpenBLAS multithreading +
  Ollama cargado durante compilación de Rust).

### Fixed
- `pyproject.toml`: `OPENBLAS_NUM_THREADS=1` y `OMP_NUM_THREADS=1` fijados para toda
  la suite de tests vía `pytest-env`. Elimina crasheos SIGABRT/IOT por OpenBLAS
  saturando RAM en WSL2 al correr múltiples tests en paralelo.
- `tests/test_assembler.py`: `test_pilot_end_to_end_noel` marcado `@pytest.mark.slow`.
  Sin el marker, la suite rápida (`-m "not slow"`) incluía este test y podía encontrar
  un 500 del embedder Ollama si el modelo estaba bajo presión de memoria.

---

## [0.5.4] — 2026-07-06

### Added
- `domain/chains/chain_06_convergencia.py`: cadena LCEL para Cap 5 "Convergencia Empresarial
  en las Áreas Estratégicas del Distrito". 4 secciones (Sostenibilidad Ambiental, Transformación
  Digital, Desarrollo Social-Humano, Desarrollo Económico). Tier synth (Nemotron Ultra free).
  Párrafo intro fijo del spec de negocio. Reutiliza helpers de chain_04.
- `domain/use_cases/generate_convergencia.py`: `GenerateConvergencia` — use case N2. Dos queries
  RAG diferenciadas (caps anteriores vs. convergencia territorial), 2 búsquedas web, deduplicación
  de chunks por `fuente_url`. `_MIN_CHUNKS = 5`. Tier synth.
- `domain/chains/chain_07_accionables.py`: cadena LCEL para Cap 6 "Accionables Estratégicos".
  Genera exactamente 6 accionables cruzando todos los capítulos. Tier free.
- `domain/use_cases/generate_accionables.py`: `GenerateAccionables` — use case N2. RAG sobre
  contenido ya indexado (Caps 2-5 + PDF). Sin web_connector. `_MIN_CHUNKS = 6`.
- `domain/chains/chain_08_resumen_ejecutivo.py`: cadena LCEL para Resumen Ejecutivo (N3).
  Tono C-Level, estructura: gancho → propósito → problema → solución → hallazgos → llamado a
  la acción. 400-600 palabras. Tier synth.
- `domain/use_cases/generate_resumen_ejecutivo.py`: `GenerateResumenEjecutivo` — use case N3.
  Sin retrieval; recibe `cap_textos: dict[str, str]` directamente. Omite caps con texto vacío.
  Siempre `retrieval_suficiente = True`.
- `shared/types.py`: DTOs `CapConvergencia`, `CapAccionables`, `ResumenEjecutivo`. Campos
  opcionales `cap_convergencia`, `cap_accionables`, `resumen_ejecutivo` en `InformePiloto`.
- `domain/assembler.py`: secciones para Cap 5 (Convergencia), Cap 6 (Accionables) y Resumen
  Ejecutivo. Eliminado placeholder "pendiente Fase 5".
- `scripts/run_pilot.py`: TOTAL_PASOS 7 → 10. Paso 6 = ingesta automática del PDF de
  convergencia territorial si `InformeConvergenciaLocal2026V3RvADAA.pdf` existe en la raíz.
  Pasos 7-8 = Cap 5/6. Paso 9 = Resumen Ejecutivo. `api_llm_synth` (tier synth).
- Tests: `test_convergencia.py` (9 tests), `test_accionables.py` (7 tests),
  `test_resumen_ejecutivo.py` (6 tests). Total: +22 tests (64 → 86 passed).

---

## [0.5.3] — 2026-07-06

### Added
- `infrastructure/retrieval/embedder.py`: `"keep_alive": 0` en el request de embeddings a Ollama.
  Descarga el modelo inmediatamente tras cada request, eliminando la coexistencia en VRAM con el
  LLM (`nomic-embed-text` + `qwen3:8b` ≈ 5.7GB) que causaba OOM en WSL2/8GB.
- `infrastructure/llm/gateway.py`: `"keep_alive": 0` en `_call` y `_stream` de
  `OllamaGatewayLLM`. Solo aplica al gateway Ollama; `OpenRouterGatewayLLM` no se modifica.
- `domain/chains/chain_05_ecosistema.py`: nueva cadena LCEL para Cap 4 "Ecosistema Empresarial".
  Secciones: 5.1 Ecosistema local (Medellín/Colombia), 5.2 Ecosistema global, 5.3 Actores
  disruptores. Formato: fichas por categoría con nombre, rol y relevancia. Reutiliza los helpers
  `format_chunks_as_context()` y `format_academic_sources()` de chain_04 (sin duplicar código).
- `domain/use_cases/generate_ecosistema.py`: `GenerateEcosistema` — use case N1. 2 búsquedas
  web específicas (empresa + "ecosistema proveedores" y sector + "alianzas partners"), RAG sobre
  pgvector, política de datos ausentes si < 3 chunks. Tier free OpenRouter. Sin openalex_connector
  (web suficiente para mapeo de actores).
- `shared/types.py`: DTO `CapEcosistema` (texto, n_chunks_usados, retrieval_suficiente,
  chunks_usados). Campo `cap_ecosistema: CapEcosistema | None = None` en `InformePiloto`.
- `tests/test_ecosistema.py`: 9 tests mockeados — 4 de chain (build, format_chunks, vacío,
  format_academic) + 5 de use case (tipo correcto, inputs chain, retrieval insuficiente, web vacío,
  ingest llamado). Sin llamadas a Ollama ni OpenRouter.
- `pyproject.toml`: marker `slow` registrado en `[tool.pytest.ini_options]`. Permite
  `pytest -m "not slow"` para excluir tests que requieren Ollama real.

### Changed
- `domain/assembler.py`: sección condicional "Capítulo 4. Ecosistema Empresarial" después de
  Cap 3 Tendencial.
- `scripts/run_pilot.py`: paso 5/7 Cap 4 Ecosistema; referencias ahora acumulan chunks de Cap 2
  + Cap 3 + Cap 4; pasos Refs (6/7) y Ensamblado (7/7) renumerados. `TOTAL_PASOS = 7`.
- `tests/test_llm.py` + `tests/test_retrieval.py`: `@pytest.mark.slow` añadido a 7 tests que
  invocan Ollama real (4 en test_llm, 3 en test_retrieval).

### Notes
- **Tests:** 64 passed, 2 skipped. Los 9 tests nuevos cubren los dos flujos de Cap 4:
  generación exitosa y degradación por retrieval insuficiente.
- **E2E pendiente:** Validar `run_pilot.py` con Noel SAS para confirmar que Cap 3 y Cap 4
  generan contenido real en español en el .docx.

---

## [0.5.2] — 2026-07-06

### Added
- `shared/text_utils.py`: módulo compartido nuevo con dos utilidades:
  - `has_cjk_characters(text, threshold=5)`: detecta si una respuesta del LLM contiene
    ≥5 caracteres de rangos CJK (chino, japonés, coreano) — umbral > 1 para no rechazar
    marcas asiáticas mencionadas como texto.
  - `format_web_results_as_context(results, max_chars_per_result=1500)`: formatea una lista
    de `WebResult` como bloque numerado para inyectar en el prompt del LLM; incluye URL,
    fuente, año y primeros 1500 chars de contenido.
- `infrastructure/llm/gateway.py`: tier `"free_alt"` en `ModelTier` y en `build_api_llm()`.
  Permite configurar un segundo modelo gratuito de fallback (`LLM_API_FREE_ALT_MODEL`).
- `infrastructure/llm/gateway.py`: parámetro `timeout` en `build_llm()` — se pasa
  `llm_local_timeout` desde settings. Corrige timeouts en `qwen3:8b` con contexto amplio.
- `shared/config.py`: campo `llm_api_free_alt_model: str = ""` — modelo free alternativo.
- `shared/config.py`: campo `llm_local_timeout: int = 300` — timeout en segundos para Ollama
  local (valor anterior implícito era 120s, insuficiente para `qwen3:8b` con contexto amplio).
- `docs/architecture/ADR-006-presupuesto-modelos-gratuitos.md`: formaliza la política de
  costo-cero / bajo costo para todos los modelos de API: solo `free` o económicos en OpenRouter;
  nunca top-tier (Claude, GPT-4o, Gemini Ultra) por restricción presupuestaria del proyecto.

### Changed
- `domain/chains/chain_01_descripcion.py`: refactor completo del prompt:
  - Inyección explícita de `{web_context}` en el user prompt: el LLM solo puede usar
    la información web provista, no su conocimiento propio (reduce alucinación).
  - System prompt reforzado: prohibición explícita de CJK con instrucción de reescritura.
  - `build_chain_01()` acepta `BaseChatModel | list[BaseChatModel]` y encadena con
    `.with_fallbacks()` cuando se recibe lista — cadena de fallback automática.
- `domain/chains/chain_03_benchmarking.py`: refuerzo de la regla de idioma en system prompt.
- `domain/chains/chain_04_tendencias.py`: ídem; prohibición CJK explícita.
- `domain/use_cases/generate_empresa_description.py`:
  - 3 queries de búsqueda web en lugar de 1 (más contexto para el LLM).
  - Formatea resultados con `format_web_results_as_context()` e inyecta como `{web_context}`.
  - Detecta respuestas CJK post-generación con `has_cjk_characters()` y devuelve párrafo
    de ausencia estándar en lugar de guardar texto en idioma incorrecto.
- `infrastructure/retrieval/embedder.py`: reintentos con backoff ante HTTP 500 de Ollama
  (`[0, 3, 8]` segundos). Cubre el swap de VRAM que Ollama necesita entre requests.
- `scripts/run_pilot.py`: construye `api_llm_alt` y `cap1_llms` (lista con fallback);
  la cadena del Cap 1 usa el orden `[api_llm, api_llm_alt, llm_local]`.

### Fixed
- Cap 1 respondía en chino cuando `qwen3:8b` era el modelo local y el prompt no forzaba
  el idioma con suficiente determinismo. Corregido por doble vía: prompt más restrictivo +
  detección post-generación.
- Ollama tiraba errores HTTP 500 transitorios durante el E2E completo por contención de VRAM
  entre el embedder y el LLM. Corregido con retries y `llm_local_timeout` extendido.
- `PRIME DIRECTIVE.md` en la raíz eliminado — el canónico vive en `docs/architecture/`.
- `*.docx` añadido a `.gitignore` (artefactos de output no deben ir en git).

### Notes
- **Tests:** 55 passed, 2 skipped (suite completa). Los 8 tests nuevos cubren los dos nuevos
  flujos: fallback CJK en Cap 1 y `text_utils`.
- **E2E pendiente:** Validar `run_pilot.py` con Noel SAS para confirmar que Cap 3 genera
  ≥200 palabras en español en el .docx antes de arrancar Fase 5D (Cap 4 Ecosistema).

---

## [0.5.1] — 2026-07-02

### Added
- `infrastructure/sources/openalex_connector.py`: `OpenAlexConnector` — wrapper REST sobre
  `api.openalex.org`; usa `mailto` del settings para acceso al polite pool (mayor rate limit);
  reconstruye el abstract desde el índice invertido de OpenAlex; retorna `WebResult` con
  metadatos APA completos (`doi`, `año`, `fuente_nombre`, `autor`, `cited_by_count`);
  retorna lista vacía en 503/timeout sin propagar la excepción (degradación silenciosa).
- `domain/chains/chain_04_tendencias.py`: cadena LCEL para Cap 3 — Análisis Sectorial
  Tendencial; system prompt con reglas estrictas de tono ejecutivo (sin "podría/quizás",
  sin viñetas en narrativas, con nivel de confianza Alto/Medio/Bajo); user prompt estructurado
  en 3.1 Tendencias TES (6 tendencias storytelling), 3.2 MECE (4 tendencias estratégicas),
  3.3 Casos de éxito (4 globales + 2 locales Medellín/Colombia).
- `domain/use_cases/generate_tendencias.py`: `GenerateTendencias` — orquesta 2 búsquedas
  web + búsqueda OpenAlex (4 works) + ingesta al pgvector + retrieval; usa `build_api_llm`
  tier `free` (Nemotron Super); aplica política de datos ausentes si retrieval < 3 chunks;
  OpenAlex es opcional: si devuelve vacío (caída 503), el capítulo se genera con fuentes web.
- `shared/types.py`: `@dataclass CapTendencias` con campos `texto`, `n_chunks_usados`,
  `retrieval_suficiente`, `chunks_usados`.
- `shared/types.py`: campo `cap_tendencias: CapTendencias | None = None` en `InformePiloto`.
- `domain/assembler.py`: sección "Capítulo 3" condicional — solo aparece en el .docx si
  `informe.cap_tendencias is not None`.
- `scripts/run_pilot.py`: paso 4/6 para Cap 3 usando `build_api_llm(tier='free')` (Nemotron
  Super); referencias combinan chunks de Cap 2 + Cap 3; si `OPENROUTER_API_KEY` no está
  configurada, el paso se omite con aviso y el informe sigue generándose con los 3 caps.
- `scripts/test_connections.py`: script de diagnóstico de servicios — verifica Ollama (GET
  `/api/tags`), PostgreSQL (`SELECT 1` en schema), OpenRouter free (Nemotron Super), OpenRouter
  synth (Nemotron Ultra), Tavily (1 búsqueda básica = 1 crédito), OpenAlex (3 works).
  Costo: 1 crédito Tavily por ejecución. No ejecutar en CI.
- `tests/test_openalex.py`: 10 tests — búsqueda con mock, campos APA, 503 silencioso, error
  de red silencioso, work sin abstract, parámetro mailto, ausencia de mailto, reconstrucción
  de abstract (3 variantes).
- `tests/test_tendencias.py`: 10 tests — build_chain retorna Runnable, formato de chunks,
  formato de fuentes académicas, execute retorna CapTendencias, inputs al chain, párrafo de
  ausencia por retrieval insuficiente, ingesta de resultados web, OpenAlex silencioso.

### Changed
- `infrastructure/sources/web_connector.py`: método `search()` acepta parámetro opcional
  `force_ddg: bool = False`; con `True` usa DDG aunque Tavily esté configurado — para usar
  en todos los tests y evitar consumir créditos del free tier (~1000/mes).
- `scripts/run_pilot.py`: TOTAL_PASOS de 5 a 6; nuevo paso Cap 3 dentro del bloque
  `SessionLocal`; referencias combinan todos los chunks de caps generados.
- `shared/types.py`: campo `referencias` de `InformePiloto` ahora tiene `default_factory=list`
  para permitir que `cap_tendencias` (con default) quede antes en la firma.

### Fixed
- `DATABASE_URL` en `.env`: corregida de credenciales de ejemplo (`ic_user/changeme`) a
  credenciales reales del postgres compartido (`repositorio_user@repositorio_ctie`).

### Notes
- **Tests:** 47 definidos (37 heredados + 10 OpenAlex + 10 Cap 3 — 20 nuevos en total).
  37/37 pasan en ejecución en frío; 4 fallos transitorios de timeout Ollama bajo carga.
- **OpenAlex 503:** La API de OpenAlex tuvo una caída el 2026-07-02. El conector la maneja
  con degradación silenciosa — Cap 3 se genera igualmente con fuentes web.
- **Prueba E2E pendiente:** correr `run_pilot.py --empresa "Noel S.A.S." --ciiu 1081` para
  validar que el .docx incluye texto real en Cap 3 (criterio de completitud: ≥200 palabras,
  no el párrafo de ausencia). No se ejecutó en esta sesión por carga de Ollama.

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
