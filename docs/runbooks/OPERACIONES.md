# Runbook Operativo — Sistema de Informes IC

> Procedimientos para operar, mantener y depurar el sistema en el entorno de desarrollo
> (WSL2, Ollama en host, PostgreSQL dockerizado).

---

## 1. Verificación de servicios antes de ejecutar

```bash
# Ollama (debe responder con lista de modelos)
curl http://127.0.0.1:11434/api/tags | jq '.models[].name'

# PostgreSQL (instancia compartida en puerto 5434)
docker ps | grep repositorio_postgres

# Script de diagnóstico completo (consume 1 crédito Tavily si está configurado)
uv run python scripts/test_connections.py
```

**Si Ollama no responde:**
```bash
# En PowerShell de Windows (fuera de WSL)
ollama serve
# O verificar que el servicio está corriendo:
Get-Process ollama
```

**Si PostgreSQL no responde:**
```bash
docker compose up -d
uv run python scripts/create_schema.py  # solo la primera vez
```

---

## 2. Generar un informe desde CLI

```bash
# Forma mínima
uv run python scripts/run_pilot.py --empresa "Nombre S.A.S."

# Con CIIU explícito (evita la búsqueda automática en RUES)
uv run python scripts/run_pilot.py --empresa "Alpina S.A.S." --ciiu 1040

# Con ruta de salida personalizada
uv run python scripts/run_pilot.py --empresa "Alpina" --salida ./output/alpina_2026.docx
```

El script genera 7 pasos (Fase 5D):
1. Cap 1 — Descripción empresa
2. GICS — Clasificación de sector
3. Cap 2 — Análisis Competitivo
4. Cap 3 — Análisis Tendencial
5. Cap 4 — Ecosistema Empresarial
6. Referencias — Formateo APA 7
7. Ensamblado .docx

---

## 3. Ingestar un PDF manual

Los PDFs sectoriales (EMIS, informes del distrito, etc.) se ingresan via:

```bash
# Ingestar un PDF con metadatos mínimos
uv run python scripts/ingest_pdf.py \
  --archivo "/path/al/InformeConvergenciaLocal2026V3RvADAA.pdf" \
  --titulo "Informe de Convergencia Local 2026" \
  --fuente "Alcaldía de Medellín" \
  --año 2026

# El script calcula el SHA-256 del archivo para evitar duplicados.
# El PDF se chunkea, embebe e indexa en pgvector.
```

**Cuándo ingestar PDFs:**
- Antes de generar Cap 5 Convergencia (el informe de convergencia territorial del distrito)
- Cuando un cap devuelve párrafo de ausencia por retrieval insuficiente
- Para incorporar informes sectoriales de EMIS, Fedesarrollo, DANE, etc.

---

## 4. Correr los tests

```bash
# Suite rápida (sin Ollama ni BD) — siempre disponible
uv run pytest -m "not slow" -q

# Suite completa con tests lentos (requiere Ollama + PostgreSQL)
uv run pytest -q

# Solo tests de un capítulo
uv run pytest tests/test_ecosistema.py -v

# Con output de prints (útil para debug)
uv run pytest -s tests/test_tendencias.py
```

**Tests que requieren servicios externos** (marcados `@pytest.mark.slow`):
- `test_llm.py`: `test_ollama_gateway_simple_complete`, `test_chain_02_gics_noel`, `test_use_case_classify_gics_noel`, `test_use_case_prompt01_noel`
- `test_retrieval.py`: `test_embedder_returns_correct_dimensions`, `test_embedder_many`, `test_ingest_and_search`

---

## 5. Troubleshooting OOM (Out of Memory en VRAM)

**Síntoma:** Ollama retorna error 500, timeout, o el sistema WSL2 se congela.

**Causa:** `nomic-embed-text` (~500MB) y el LLM analítico (~5.2GB) coexisten en VRAM.

**Verificación:**
```bash
# En Windows PowerShell
nvidia-smi   # ver uso de VRAM

# Verificar que keep_alive:0 está activo (debe retornar 768)
curl -s http://127.0.0.1:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test","keep_alive":0}' | jq '.embedding | length'
```

**Si el OOM persiste:**
1. Reiniciar Ollama: `taskkill /f /im ollama.exe && ollama serve`
2. Liberar VRAM: `ollama rm <modelo>` temporalmente
3. Verificar que no hay otro proceso consumiendo VRAM: `nvidia-smi`

---

## 6. Gestión de modelos Ollama

```bash
# Modelos requeridos
ollama pull nomic-embed-text:latest   # embeddings — 274MB
ollama pull qwen2.5:7b                # LLM analítico — ~5GB

# Ver modelos instalados
ollama list

# Verificar que un modelo responde
ollama run qwen2.5:7b "Responde solo: OK"

# Liberar VRAM manualmente (si keep_alive:0 no liberó)
ollama stop nomic-embed-text
ollama stop qwen2.5:7b
```

---

## 7. Linting y formateo

```bash
# Verificar linting (solo errores no-E501 bloquean)
uv run ruff check .

# Formateo automático
uv run black src/ tests/

# Combinado (lo que corren los hooks de pre-edit)
uv run ruff check . && uv run black --check src/ tests/
```

---

## 8. Backup de la BD

```bash
# Backup del schema del proyecto
pg_dump -h 127.0.0.1 -p 5434 -U repositorio_user -d repositorio_ctie \
  --schema=informes_ic \
  -f ~/backups/$(date +%Y%m%d_%H%M)_informes_ic.sql

# Restaurar desde backup
psql -h 127.0.0.1 -p 5434 -U repositorio_user -d repositorio_ctie \
  < ~/backups/FECHA_informes_ic.sql
```

---

## 9. Variables de entorno críticas

Ver `.env.example` en la raíz del proyecto. Las más importantes:

| Variable | Default | Descripción |
|---------|---------|-------------|
| `LLM_LOCAL_TIMEOUT` | `300` | Timeout Ollama en segundos. `qwen3:8b` necesita >120s. |
| `RAG_SIMILARITY_THRESHOLD` | `0.7` | Score mínimo de cosine similarity para considerar un chunk relevante |
| `RAG_TOP_K` | `10` | Máximo chunks devueltos por búsqueda |
| `LLM_BUDGET_LIMIT_USD` | `1.0` | Presupuesto máximo por informe |
| `TAVILY_API_KEY` | vacío | Vacío = fallback a DDG gratuito |

---

## 10. Estructura de directorios clave

```
src/ic/
  domain/chains/          ← Prompts LCEL (chain_01 a chain_0N)
  domain/use_cases/       ← Orquestación RAG + LLM por cap
  domain/assembler.py     ← Ensamblado final .docx
  infrastructure/llm/     ← Gateway Ollama + OpenRouter
  infrastructure/retrieval/ ← Embedder + PGVectorStore
  infrastructure/sources/ ← WebConnector + OpenAlexConnector
  infrastructure/citation/ ← APA formatter
  shared/types.py         ← Todos los DTOs
  shared/config.py        ← Settings (singleton pydantic)

scripts/
  run_pilot.py            ← CLI principal
  ingest_pdf.py           ← Ingesta PDFs manuales
  create_schema.py        ← Inicialización BD
  test_connections.py     ← Diagnóstico de servicios

tests/                    ← Espeja src/ic/ en nombres de archivo
```
