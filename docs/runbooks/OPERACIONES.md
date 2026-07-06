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

El script genera **10 pasos** (Fase 6 — via `GenerateInforme` orchestrator):
1. Cap 1 — Descripción empresa (~50s)
2. GICS — Clasificación de sector (~30s)
3. N1 paralelo — Caps 2, 3, 4 simultáneos (~12 min)
4. Párrafos introductorios N1 (~12s)
5. PDF Convergencia — ingesta condicional (~23 min si hay PDF, puede fallar por OOM)
6. Cap 5 — Convergencia Empresarial (~79 min en tier free — ver H6-02)
7. Cap 6 — Accionables Estratégicos (~48s)
8. Párrafos introductorios N2 (~6s)
9. Resumen Ejecutivo (~94s)
10. Referencias APA + Ensamblado .docx (<1s)

**Tiempo total esperado:** ~117 min (dominado por Cap 5 y PDF ingesta).
Ver `docs/decisions/FASE6_HALLAZGOS.md` para análisis completo de tiempos.

---

## 3. Generar un informe desde la UI Streamlit

```bash
# Iniciar servidor (puerto 8503, no conflicta con el default 8501)
uv run streamlit run src/ic/presentation/app.py --server.port 8503

# Abrir en el navegador
# → http://localhost:8503
```

**Flujo:**
1. Ingresar nombre de empresa (requerido), CIIU (opcional), ruta de salida (opcional)
2. Click "🚀 Generar informe"
3. La UI verifica Ollama + PostgreSQL antes de empezar
4. Barra de progreso muestra los 10 pasos en tiempo real
5. Al finalizar: botón de descarga del `.docx` + expander con métricas

**Nota:** El informe puede tardar ~2 horas. El servidor Streamlit mantiene la conexión
abierta. Si la terminal se cierra, el proceso muere. Para ejecuciones largas, usar `tmux`:
```bash
tmux new-session -s informe
uv run streamlit run src/ic/presentation/app.py --server.port 8503
# Ctrl+B, D para detach; tmux attach -t informe para reconnectar
```

---

## 4. Ingestar un PDF manual

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

## 6. Correr los tests

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

## 7. Troubleshooting OOM (Out of Memory en VRAM)

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

## 8. Gestión de modelos Ollama

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

## 9. Linting y formateo

```bash
# Verificar linting (solo errores no-E501 bloquean)
uv run ruff check .

# Formateo automático
uv run black src/ tests/

# Combinado (lo que corren los hooks de pre-edit)
uv run ruff check . && uv run black --check src/ tests/
```

---

## 10. Backup de la BD

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

## 11. Variables de entorno críticas

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
