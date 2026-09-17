# Quickstart: 008 — Validación de Ingesta Paralela y Enriquecimiento Automático

**Date**: 2026-09-17

---

## Prerequisitos

```bash
docker compose up -d          # PostgreSQL + pgvector
curl http://127.0.0.1:11434/api/tags  # Ollama operativo con nomic-embed-text
uv run python scripts/test_connections.py  # Verificar conectividad
```

---

## Validación A — Ingesta Paralela

### 1. Preparar corpus de prueba

```bash
# Usar 5-10 PDFs del directorio existente
ls documentos_sectoriales/*.pdf | head -5
```

Crear `docs/test_pdfs/indice.csv` con esas rutas (o usar el `indice.csv` existente con un subconjunto).

### 2. Ejecutar con workers

```bash
uv run python scripts/ingest_batch.py \
  --dir documentos_sectoriales \
  --csv documentos_sectoriales/indice.csv \
  --workers 3 \
  2>/dev/null | python3 -m json.tool
```

**Resultado esperado**: JSON lines por cada PDF, línea de resumen con `"ok"` ≥ 1, sin interrupciones por errores individuales.

### 3. Verificar idempotencia

```bash
# Segunda ejecución del mismo lote
uv run python scripts/ingest_batch.py \
  --dir documentos_sectoriales \
  --csv documentos_sectoriales/indice.csv \
  --workers 3 2>/dev/null | grep '"n_chunks"'
# Resultado esperado: "n_chunks": 0 en todos (ON CONFLICT DO NOTHING)
```

### 4. Verificar aceleración

```bash
# Secuencial (baseline)
time uv run python scripts/ingest_batch.py --workers 1 ...

# Paralelo
time uv run python scripts/ingest_batch.py --workers 4 ...
# SC-001: tiempo_paralelo <= tiempo_secuencial * 0.4
```

---

## Validación B — Enriquecimiento Automático

### 1. Sector sin documentos

Identificar un sector con 0 chunks en el índice:

```bash
# En psql
SELECT sector_gics, count(*) FROM informes_ic.embedding_vectorial
GROUP BY sector_gics ORDER BY count ASC LIMIT 5;
```

### 2. Lanzar generación de informe sobre ese sector

```bash
# Desde la UI Streamlit (http://localhost:8503) o directamente:
uv run python -c "
from ic.shared.config import get_settings
# ... invocar pipeline con sector de baja densidad
"
```

**Resultado esperado**:
- El log muestra `AutoEnrich.try_enrich` activado para ese sector
- Al menos 1 fragmento nuevo en `embedding_vectorial` con `metadatos->>'fuente' IN ('openalex','web_enrichment')`
- El informe generado cita la fuente enriquecida con APA

### 3. Verificar degradación elegante

Desconectar temporalmente la red (o apuntar a URL inválida de OpenAlex en tests) y lanzar generación — el informe debe generarse con párrafo de ausencia, sin lanzar excepción.

---

## Tests Automatizados

```bash
uv run pytest tests/test_parallel_ingestor.py tests/test_auto_enrich.py -v
# Todos deben pasar sin BD real ni Ollama activos (mocks)
```

---

## Verificación de Invariantes

```bash
uv run ruff check .
find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -5
# Ningún archivo > 300 líneas
```
