# Sistema de Informes de Inteligencia Competitiva

Genera informes de vigilancia competitiva estructurados y citados a partir del nombre de una empresa,
usando RAG propio sobre pgvector, modelos locales vía Ollama y cadenas LCEL.

**Estado actual:** Fase 3 completa — LLM Gateway + Cadenas LCEL + Use Cases del piloto  
**Piloto de referencia:** Compañía de Galletas NOEL SAS (Grupo Nutresa)

---

## Prerequisitos

| Servicio | Requisito |
|---------|-----------|
| Python | 3.12+ (gestionado con `uv`) |
| PostgreSQL + pgvector | Instancia corriendo en `localhost:5434` (ver PRIME DIRECTIVE §10.3) |
| Ollama | En host, `http://127.0.0.1:11434` (nunca dockerizado — ver ADR-002) |
| Modelos Ollama | `nomic-embed-text:latest` + modelo analítico (configurado en `.env`) |

## Setup en menos de 5 pasos

```bash
# 1. Instalar dependencias
uv sync

# 2. Copiar y completar las variables de entorno
cp .env.example .env   # editar con credenciales reales

# 3. Crear schema y tablas en PostgreSQL
uv run python scripts/create_schema.py

# 4. Verificar servicios
curl http://127.0.0.1:11434/api/tags      # Ollama OK?
docker ps | grep repositorio_postgres     # BD OK?

# 5. Correr tests
uv run pytest tests/ -v                   # debe mostrar 19/19 passed
```

## Variables de entorno requeridas

```env
# BD (apunta a la instancia compartida del entorno)
DATABASE_URL=postgresql://repositorio_user:<pass>@localhost:5434/repositorio_ctie
DB_SCHEMA=informes_ic

# Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Modelos — nombres vienen de .env, nunca hardcodeados en código (ADR-002)
LLM_LOCAL_EMBED_MODEL=nomic-embed-text:latest
LLM_LOCAL_DRAFT_MODEL=<modelo-ollama>
LLM_LOCAL_ANALYTIC_MODEL=<modelo-ollama>
LLM_API_PROVIDER=claude
LLM_API_ANALYTIC_MODEL=<modelo-api>
LLM_API_KEY=

# RAG
RAG_SIMILARITY_THRESHOLD=0.7
RAG_TOP_K=10

# Presupuesto y circuit breaker
LLM_BUDGET_LIMIT_USD=1.0
LLM_CIRCUIT_BREAKER_MAX_RETRIES=3

# Fuentes web (vacío = fallback a DDG gratuito)
TAVILY_API_KEY=
```

## Arquitectura de alto nivel

```
presentation/   → Streamlit UI (pendiente — Fase 6)
domain/         → use cases + cadenas LCEL + política de datos ausentes
data/           → repositorios ORM + acceso a PostgreSQL/pgvector
infrastructure/ → LLM gateway (Ollama/API), WebConnector, Embedder, PGVectorStore
shared/         → Settings, DTOs, constantes GICS
```

El sistema genera un informe siguiendo un DAG de capítulos:
**N0 fundacionales** → **N1 analíticos** (paralelizables) → **N2 síntesis** → **N3 meta** → **ensamblado .docx**

## Fases de desarrollo

| Fase | Estado | Descripción |
|------|--------|-------------|
| 0 | ✅ | Andamiaje: Docker + PostgreSQL + modelos ORM |
| 2 | ✅ | Retrieval: WebConnector + Embedder + PGVectorStore |
| 3 | ✅ | LLM Gateway + Cadenas LCEL + Use Cases del piloto |
| 4 | ⏳ | Ensamblado: python-docx + citación APA 7 |
| 5 | ⏳ | DAG completo + tests E2E piloto NOEL |
| 6 | ⏳ | Medición de costo/tiempo; verificar ≤1 USD/informe |

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [`docs/architecture/ARQUITECTURA.md`](docs/architecture/ARQUITECTURA.md) | Arquitectura viva del sistema |
| [`docs/architecture/ADR-001`](docs/architecture/ADR-001-rag-propio-reemplaza-notebooklm.md) a [`ADR-005`](docs/architecture/ADR-005-retrieval-layer-design.md) | Decisiones arquitectónicas |
| [`docs/decisions/FASE0_HALLAZGOS.md`](docs/decisions/FASE0_HALLAZGOS.md) | Hallazgos operativos Fase 0 |
| [`docs/decisions/FASE2_HALLAZGOS.md`](docs/decisions/FASE2_HALLAZGOS.md) | Hallazgos operativos Fase 2 |
| [`docs/decisions/FASE3_HALLAZGOS.md`](docs/decisions/FASE3_HALLAZGOS.md) | Hallazgos operativos Fase 3 |
| [`docs/prompts/`](docs/prompts/) | Especificación de los 3 prompts del piloto |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial semántico de cambios |
| [`CLAUDE.md`](CLAUDE.md) | Reglas operativas para agentes IA |
| [`docs/architecture/PRIME DIRECTIVE.md`](docs/architecture/PRIME%20DIRECTIVE.md) | Norma arquitectónica completa |
