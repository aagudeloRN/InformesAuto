# Sistema de Informes de Inteligencia Competitiva

Genera informes de vigilancia competitiva estructurados y citados a partir del nombre de una empresa,
usando RAG propio sobre pgvector, modelos locales vía Ollama y cadenas LCEL.

**Estado actual:** Fase 5D — keep_alive:0 OOM fix + Cap 4 Ecosistema + markers slow
**Piloto de referencia:** Compañía de Galletas NOEL SAS (Grupo Nutresa)
**Tests:** 64 passed, 2 skipped (57 sin servicios) | **Caps implementados:** 1, GICS, 2, 3, 4

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
#    NOTA: si repositorio_postgres ya está corriendo en :5434, saltar este paso
uv run python scripts/create_schema.py

# 4. Verificar servicios
curl http://127.0.0.1:11434/api/tags      # Ollama OK?
docker ps | grep repositorio_postgres     # BD OK? (puerto 5434)

# 5. Correr tests
uv run pytest tests/ -v                   # debe mostrar 55 passed, 2 skipped
```

## Generar un informe desde CLI

```bash
uv run python scripts/run_pilot.py --empresa "Nombre de la empresa" --ciiu 1234

# Con ruta de salida personalizada
uv run python scripts/run_pilot.py --empresa "Alpina S.A.S." --salida ./output/alpina.docx
```

El script verifica servicios, ejecuta los capítulos disponibles y muestra un resumen de tiempos.  
El `.docx` se guarda en `./output/` (excluido de git).

## Variables de entorno requeridas

```env
# BD (apunta a la instancia compartida del entorno)
DATABASE_URL=postgresql://repositorio_user:<pass>@localhost:5434/repositorio_ctie
DB_SCHEMA=informes_ic

# Ollama (en host, no Docker — WSL: máx modelos 7B para no saturar 8GB VRAM)
OLLAMA_BASE_URL=http://127.0.0.1:11434
LLM_LOCAL_EMBED_MODEL=nomic-embed-text:latest   # siempre local, 137MB
LLM_LOCAL_DRAFT_MODEL=qwen2.5:7b               # cap 1, GICS — seguro en WSL 8GB
LLM_LOCAL_ANALYTIC_MODEL=qwen2.5:7b

# OpenRouter — escalado API para caps analíticos (ADR-002, ADR-006)
# POLÍTICA: solo modelos free o económicos — nunca top-tier (Claude, GPT-4, Gemini Ultra)
# Obtener clave: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-...
LLM_API_FREE_MODEL=nvidia/nemotron-3-super-120b-a12b:free      # tier free primario — $0
LLM_API_FREE_ALT_MODEL=meta-llama/llama-3.3-70b-instruct:free  # tier free alternativo — $0
LLM_API_SYNTH_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free     # síntesis (caps 5/6/resumen) — $0
LLM_API_PAID_MODEL=google/gemma-3-27b-it                       # respaldo pago <$0.20/MTok

# RAG
RAG_SIMILARITY_THRESHOLD=0.7
RAG_TOP_K=10

# Presupuesto y circuit breaker
LLM_BUDGET_LIMIT_USD=1.0
LLM_CIRCUIT_BREAKER_MAX_RETRIES=3
LLM_LOCAL_TIMEOUT=300                                           # segundos; qwen3:8b necesita >120s

# Fuentes web (vacío = fallback a DDG gratuito)
TAVILY_API_KEY=

# Ensamblado .docx
DOCX_TEMPLATE_PATH=assets/plantilla_membrete.dotx   # vacío = documento limpio
DOCX_OUTPUT_DIR=./output
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
| 4 | ✅ | Ensamblado .docx + Citación APA 7 + Ingesta PDF |
| 5A | ✅ | Script piloto CLI + Gateway OpenRouter + CostTracker real |
| 5B | ✅ | Cap 3 Tendencial + OpenAlexConnector + test_connections |
| 5C | ✅ | Estabilidad OOM/CJK + fallback multi-LLM Cap 1 + ADR-006 |
| 5D | ✅ | `keep_alive:0` Ollama + Cap 4 Ecosistema + markers slow |
| 5E | 🔄 | **Siguiente:** Cap 5 Convergencia + Resumen Ejecutivo (N2+N3) |
| 6 | ⏳ | DAG orquestador + UI Streamlit (puerto 8503) |

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [`docs/architecture/ARQUITECTURA.md`](docs/architecture/ARQUITECTURA.md) | Arquitectura viva del sistema |
| [`docs/architecture/ADR-001`](docs/architecture/ADR-001-rag-propio-reemplaza-notebooklm.md) a [`ADR-005`](docs/architecture/ADR-005-retrieval-layer-design.md) | Decisiones arquitectónicas |
| [`docs/decisions/FASE0_HALLAZGOS.md`](docs/decisions/FASE0_HALLAZGOS.md) | Hallazgos operativos Fase 0 |
| [`docs/decisions/FASE2_HALLAZGOS.md`](docs/decisions/FASE2_HALLAZGOS.md) | Hallazgos operativos Fase 2 |
| [`docs/decisions/FASE3_HALLAZGOS.md`](docs/decisions/FASE3_HALLAZGOS.md) | Hallazgos operativos Fase 3 |
| [`docs/decisions/FASE4_HALLAZGOS.md`](docs/decisions/FASE4_HALLAZGOS.md) | Hallazgos operativos Fase 4 |
| [`docs/decisions/FASE5A_HALLAZGOS.md`](docs/decisions/FASE5A_HALLAZGOS.md) | Hallazgos operativos Fase 5A (CLI, OpenRouter, CostTracker, benchmarks) |
| [`docs/decisions/FASE5B_HALLAZGOS.md`](docs/decisions/FASE5B_HALLAZGOS.md) | Hallazgos operativos Fase 5B (Cap 3, OpenAlex, credenciales BD) |
| [`docs/decisions/FASE5C_HALLAZGOS.md`](docs/decisions/FASE5C_HALLAZGOS.md) | Hallazgos operativos Fase 5C (OOM/CJK, keep_alive, ADR-006) |
| [`docs/decisions/FASE5D_HALLAZGOS.md`](docs/decisions/FASE5D_HALLAZGOS.md) | Hallazgos operativos Fase 5D (keep_alive:0 definitivo, Cap 4, markers) |
| [`docs/architecture/ADR-006`](docs/architecture/ADR-006-presupuesto-modelos-gratuitos.md) | Política de presupuesto: solo free o económicos |
| [`docs/business-rules/REGLAS_NEGOCIO.md`](docs/business-rules/REGLAS_NEGOCIO.md) | Reglas de negocio del sistema: datos ausentes, citación, política modelos |
| [`docs/runbooks/OPERACIONES.md`](docs/runbooks/OPERACIONES.md) | Runbook operativo: ingesta PDF, verificación de servicios, troubleshooting |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Guía para agentes y colaboradores |
| [`docs/prompts/`](docs/prompts/) | Especificación de los prompts del piloto |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial semántico de cambios |
| [`CLAUDE.md`](CLAUDE.md) | Reglas operativas para agentes IA |
| [`docs/architecture/PRIME DIRECTIVE.md`](docs/architecture/PRIME%20DIRECTIVE.md) | Norma arquitectónica completa |
