# Arquitectura del Sistema — Informes de Inteligencia Competitiva

**Versión:** 2 (post Fase 2)
**Última actualización:** 2026-06-22
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
| **Local-primero** | Ollama en el host; la API externa (Claude, Gemini, etc.) solo se invoca si el modelo local no supera el umbral de calidad |
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
│    · casos de uso (generar capítulo, ensamblar)      │
│    · política de datos ausentes                      │
│    · DAG de capítulos (N0→N1→N2→N3→ensamblado)      │
└───────┬───────────────────────────────┬──────────────┘
        │                               │
┌───────▼───────────┐       ┌───────────▼──────────────┐
│  infrastructure/  │       │  data/                   │
│  · LLM gateway    │       │  · repositories           │
│  · WebConnector   │       │  · models (ORM)           │
│  · Embedder       │       │  · database (engine)      │
│  · Chunker        │       └──────────────────────────┘
│  · PGVectorStore  │
└───────────────────┘
        │
┌───────▼───────────────────────────────────────────┐
│  shared/              tipos, constantes, config   │
│  · Settings (pydantic-settings, lru_cache)        │
│  · DTOs: WebResult, ChunkResult                   │
│  · Enums: FuenteTipo, EstadoInforme, etc.         │
│  · Constantes: GICS_GROUPS (25 grupos)            │
└───────────────────────────────────────────────────┘
```

---

## 4. Flujo de generación de un informe

```
Input usuario: {nombre_empresa}, {descripcion_preliminar}
                         │
                         ▼
          ┌──────────────────────────┐
          │  N0: Fundacionales       │
          │  · Prompt-01: Descripción│ ← búsqueda web RUES + CIIU (WebConnector)
          │  · Prompt-02: GICS       │ ← 25 grupos en system prompt (sin retrieval)
          │  · Prompt-00: Ecuaciones │ ← genera queries de búsqueda por canal
          └──────────────┬───────────┘
                         │
          ┌──────────────▼───────────────────────────────────┐
          │  N1: Analíticos (paralelizables)                 │
          │  · Cap 2 Benchmarking  ← web on-demand + pgvector│
          │  · Cap 3 Tendencial    ← OpenAlex + web + pgvec  │
          │  · Cap 4 Ecosistema    ← web + pgvector           │
          │  · Cap 5 Convergencia  ← retrieval cruzado       │
          └──────────────┬───────────────────────────────────┘
                         │  (barrera de sincronización)
          ┌──────────────▼───────────┐
          │  N2: Síntesis            │
          │  · Cap 6 Accionables     │ ← consume salidas N1
          └──────────────┬───────────┘
                         │  (barrera de sincronización)
          ┌──────────────▼───────────┐
          │  N3: Meta                │
          │  · Resumen Ejecutivo     │ ← consume informe completo
          │  · Párrafos Intro        │
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
- Entre N1 y N2: los 4 capítulos N1 deben estar persistidos antes de Cap 6.
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
| Enums | `shared/constants/__init__.py` | EstadoInforme, TipoDocumento, FuenteTipo, EstadoIngesta |
| Scripts | `scripts/create_schema.py` | Crea el schema `informes_ic` y las tablas |

### Fase 2 ✅

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| DTOs | `shared/types.py` | WebResult, ChunkResult |
| Constantes GICS | `shared/constants/gics_groups.py` | 25 grupos + `build_gics_prompt_block()` |
| WebConnector | `infrastructure/sources/web_connector.py` | Búsqueda Tavily/DDG; extracción CIIU |
| Chunker | `infrastructure/retrieval/chunker.py` | `chunk_text()` sobre `RecursiveCharacterTextSplitter` |
| Embedder | `infrastructure/retrieval/embedder.py` | httpx directo a Ollama `/api/embeddings` |
| EmbeddingRepository | `data/repositories/embedding_repo.py` | `insert_many()` + `search_similar()` (cosine pgvector) |
| PGVectorStore | `infrastructure/retrieval/pgvector_store.py` | Orquesta chunker + embedder + repo; `ingest()` + `search()` |

### Pendiente

| Fase | Componente | Descripción |
|------|-----------|-------------|
| 3 | LLM Gateway | Wrapper único: circuit breaker, budget tracker, fallback local→API, logging de costo |
| 3 | Cadenas LCEL | Chains para Prompt-01, 02, 03; política de datos ausentes |
| 3 | Prompt-00 | Generación de ecuaciones de búsqueda por canal (OpenAlex, arXiv, web) |
| 4 | Ensamblador | `domain/assembler.py` + `infrastructure/docx_builder.py` via python-docx |
| 4 | Citación APA | Generador de citas APA 7 desde metadatos del chunk |
| 4 | PDF Ingestor | `scripts/ingest_pdf.py` para PDFs manuales (EMIS, informes sectoriales) |
| 5 | DAG completo | Orquestador de los niveles N0→N1→N2→N3→ensamblado |
| 5 | Tests E2E | Piloto NOEL completo (empresa → informe .docx) |
| 6 | Medición | Dashboard de costo/tiempo por informe |

---

## 6. Infraestructura del entorno de desarrollo

| Servicio | Ubicación | Config |
|----------|-----------|--------|
| PostgreSQL + pgvector | `repositorio_postgres` Docker, `localhost:5434` | DB: `repositorio_ctie`, schema: `informes_ic` |
| Ollama | Host (no Docker) | `http://127.0.0.1:11434` |
| Modelos disponibles | Ollama host | `qwen2.5:7b` (draft/analítico), `nomic-embed-text:latest` (embeddings 768d) |
| Python runtime | `.venv` gestionado por `uv` | Python 3.12 |

**Variables de entorno críticas** (en `.env`, nunca en código):

```env
DATABASE_URL=postgresql://...             # conexión a repositorio_ctie
LLM_LOCAL_EMBED_MODEL=nomic-embed-text:latest
LLM_LOCAL_DRAFT_MODEL=qwen2.5:7b
LLM_LOCAL_ANALYTIC_MODEL=qwen2.5:7b
LLM_API_PROVIDER=claude                  # o gemini
LLM_API_ANALYTIC_MODEL=...               # modelo API sin hardcodear
LLM_API_KEY=...
OLLAMA_BASE_URL=http://127.0.0.1:11434
RAG_SIMILARITY_THRESHOLD=0.7
RAG_TOP_K=10
TAVILY_API_KEY=                          # vacío = fallback a DDG
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

---

## 8. Patrones establecidos (copiar en Fase 3+)

### Patrón de acceso a Ollama (httpx directo)

```python
# infrastructure/retrieval/embedder.py — referencia
resp = httpx.post(
    f"{settings.ollama_base_url}/api/embeddings",
    json={"model": settings.llm_local_embed_model, "prompt": text},
    timeout=30,
)
resp.raise_for_status()
return resp.json()["embedding"]
```

### Patrón de raw SQL con schema calificado

```python
# data/repositories/embedding_repo.py — referencia
table = EmbeddingVectorial.__table__.fullname  # "informes_ic.embeddings_vectoriales"
sql = text(f"SELECT ... FROM {table} ...")
```

### Patrón de lectura de config (sin hardcodear modelos)

```python
# Correcto — el nombre del modelo viene del .env
model = settings.llm_local_embed_model

# Incorrecto — viola CLAUDE.md Tier 1
model = "nomic-embed-text"
```

---

## 9. Guía rápida de comandos

```bash
# Verificar servicios
docker ps | grep repositorio_postgres    # BD corriendo?
curl http://127.0.0.1:11434/api/tags     # Ollama responde?

# Desarrollo
uv sync                                  # sincronizar deps
uv run pytest tests/ -v                  # suite completa (13 tests)
uv run python scripts/create_schema.py   # re-crear schema si hay cambios ORM

# Verificación rápida de embeddings
uv run python -c "
from ic.shared.config import get_settings
from ic.infrastructure.retrieval.embedder import Embedder
e = Embedder(get_settings())
v = e.embed('test')
print(f'OK: {len(v)} dims')
"
```
