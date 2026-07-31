from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de datos
    database_url: str
    db_schema: str = "informes_ic"

    # Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"

    # Routing de modelos (ADR-002) — valores vienen de .env, nunca hardcodeados aquí
    llm_local_embed_model: str
    llm_local_draft_model: str
    llm_local_analytic_model: str

    # OpenRouter (escalado API)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    llm_api_free_model: str = ""      # tier free primario (Nemotron Super 120B)
    llm_api_free_alt_model: str = ""  # tier free alternativo (ej: meta-llama/llama-3.3-70b-instruct:free)  # noqa: E501
    llm_api_synth_model: str = ""     # tier síntesis free (Nemotron Ultra)
    llm_api_paid_model: str = ""      # respaldo pago (Gemma 3)

    # Compatibilidad legada — mantener para no romper .env existentes
    llm_api_provider: str = "openrouter"
    llm_api_analytic_model: str = ""
    llm_api_key: str = ""

    # Control de presupuesto y timeouts
    llm_max_tokens_input: int = 8000
    llm_max_tokens_output: int = 4000
    llm_budget_limit_usd: float = 1.0
    llm_circuit_breaker_max_retries: int = 3
    llm_local_timeout: int = 300  # segundos; qwen3:8b con contexto amplio puede tardar >120s

    # Retrieval (ADR-001)
    rag_similarity_threshold: float = 0.7
    rag_top_k: int = 10
    # Cap por documento: evita que un informe sectorial grande monopolice el contexto
    # (diversidad de fuentes — hallazgo RepositorioRN MMR, ADR-012).
    # Fase 22 (DT-049): bajado 4→2 con el corpus EMIS multi-documento por sector, para que
    # los slots de contexto cubran más documentos distintos → más fuentes citables.
    rag_max_chunks_per_doc: int = 2
    # Cupos reservados para chunks del corpus sectorial estricto (mismo GICS) cuando hay
    # match de sector: garantiza que la evidencia sectorial aflore pese al backlog web (ADR-012)
    rag_sector_reserve: int = 3
    # Umbral relajado solo para los cupos reservados: el corpus sectorial es on-topic por
    # construcción; su vocabulario a veces embebe por debajo del umbral general (ADR-012)
    rag_sector_reserve_threshold: float = 0.5
    # MMR (Fase 14, T14.2): reranking por diversidad de documento. λ=1.0 lo desactiva (no-op);
    # λ<1.0 → penaliza chunks del mismo documento. Fase 14 lo desactivó (λ=1.0) porque el
    # corpus era mono-documento por sector (la evidencia estaba concentrada en un único doc;
    # penalizar diversidad degradaba el retrieval — FASE14_HALLAZGOS.md). Fase 22 (DT-049) lo
    # REACTIVA (λ=0.7) al llegar el corpus EMIS multi-documento por sector: esa condición ya
    # no aplica y la diversidad de documento vuelve a ser deseable (no re-litiga ADR-014; es su
    # palanca documentada). Validable A/B con `scripts/eval_retrieval.py --mmr-lambda`.
    rag_mmr_lambda: float = 0.7
    # Piso de diversidad (Fase 22, DT-049): mínimo de documentos DISTINTOS que search() intenta
    # devolver cuando el corpus los tiene. Garantía determinista sobre MMR + cap por doc, para
    # que las Referencias del informe reflejen la amplitud real del corpus (≥8 fuentes citables).
    rag_min_distinct_docs: int = 5
    # Cupos reservados para chunks globales cross-sector (Fase 18, DT-031): documentos con
    # es_global=true participan en todos los sectores con cupo propio, antepuestos tras los
    # sectoriales. Mismo umbral relajado que rag_sector_reserve_threshold (ADR-012 addendum).
    rag_global_reserve: int = 2
    # Cupos reservados para chunks de la empresa específica del informe (Fase 18, T18.3):
    # docs asociados a empresa_id específica se anteponen con prioridad máxima.
    rag_empresa_reserve: int = 2

    # Embedding — keep_alive (Fase 15, T15.1, ADR-006)
    # Default "0": libera VRAM inmediatamente (política ADR-006).
    # batch_keep_alive "5m": keep_alive usado en batch_mode() para re-ingesta/harness/N1.
    # batch_mode() descarga el modelo al cerrar → el lote es explícito y acotado, no el default.
    embedder_keep_alive: str = "0"
    embedder_batch_keep_alive: str = "5m"
    # Paralelismo de embeddings (Fase 23): nomic-embed-text ocupa poca VRAM y Ollama atiende
    # peticiones concurrentes → embed_many las lanza en paralelo (medido ~5x vs serial con 4).
    # Solo tiene efecto seguro dentro de batch_mode() (modelo cargado; sin thrash de keep_alive:0).
    embedder_max_workers: int = 4

    # Caché de retrieval (Fase 15, T15.2)
    retrieval_cache_ttl_hours: int = 168  # 7 días por defecto

    # Timeouts por tier API (Fase 15, T15.3)
    llm_api_timeout_free: int = 180
    llm_api_timeout_free_alt: int = 180
    llm_api_timeout_synth: int = 180
    llm_api_timeout_paid: int = 120

    # Gate de latencia/costo (Fase 15, T15.4)
    eval_gate_max_latency_ms: float = 3000.0   # ms por consulta embed+SQL
    eval_gate_max_latency_sql_ms: float = 50.0  # ms SQL puro
    eval_gate_max_cost_usd: float = 0.0         # harness no gasta API

    # Fuentes automáticas (ADR-003)
    openalex_email: str = ""
    tavily_api_key: str = ""

    # Ensamblado de documentos (Fase 4)
    docx_template_path: str = ""
    docx_output_dir: str = "./output"

    # Ingesta PDF (RN-010)
    pdf_batch_size_pages: int = 20

    # Auto-revisión por-nodo (DT-059) — loop generar→juez→revisar con la rúbrica v1.0.
    # Flag maestro default-OFF: apagado = comportamiento actual idéntico (invariante). El
    # evaluador reusa el LLM resiliente ya construido (sin nombre de modelo en código, ADR-002).
    selfreview_enabled: bool = False
    selfreview_min_total: int = 11  # gate de la rúbrica (>=11/15 y sin dimensión en 0)
    selfreview_max_iter: int = 3    # tope de iteraciones de revisión por capítulo

    # Descubrimiento LLM de competidores globales (DT-062) — el LLM recomienda actores de clase
    # mundial, corroborados por web dirigida (RN-001), sembrados alcance=global. Flag maestro
    # default-OFF: apagado = anclaje solo con la semilla curada de DT-061b (invariante).
    discover_globales_enabled: bool = False
    discover_globales_min_corrob: int = 2  # nº de fuentes web que deben mencionar el candidato

    # Anclaje del tier LOCAL (DT-050) — inyecta jugadores del directorio (EmpresasColombia +
    # StartIA) a 2.1.2 (regionales) y 2.1.3 (startups) del Cap 2, como contexto estructurado +
    # búsqueda web dirigida. Flag maestro default-OFF: apagado = comportamiento actual (el LLM
    # llena el tier local solo desde web/RAG), prompt idéntico (invariante).
    anclaje_local_enabled: bool = False
    anclaje_local_top_n: int = 6  # tope de jugadores locales por subsección (regionales/startups)

    # NER de entidades (DT-057/T3) — motor y modelos por config, nunca hardcodeados en app-code.
    # Motor pluggable: "spacy" (librería, CPU, sin VRAM) hoy; otros motores se añaden en el wrapper.
    # Corpus EMIS bilingüe (~79% inglés / ~24% español): se elige el modelo por idioma del chunk.
    ner_engine: str = "spacy"
    ner_spacy_model_en: str = "en_core_web_md"
    ner_spacy_model_es: str = "es_core_news_md"

    # Aplicación
    app_env: str = "development"
    log_level: str = "INFO"
    informe_disclaimer: str = (
        "Informe generado automáticamente por IA. "
        "Los contenidos deben ser verificados por un analista antes de su uso."
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
