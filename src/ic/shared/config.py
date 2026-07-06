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
    llm_api_free_alt_model: str = ""  # tier free alternativo (ej: meta-llama/llama-3.3-70b-instruct:free)
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

    # Fuentes automáticas (ADR-003)
    openalex_email: str = ""
    tavily_api_key: str = ""

    # Ensamblado de documentos (Fase 4)
    docx_template_path: str = ""
    docx_output_dir: str = "./output"

    # Aplicación
    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
