# Data Model: 008 — Ingesta Masiva Paralela e Infraestructura de Evidencia

**Date**: 2026-09-17

---

## Entidades Nuevas (DTOs internos, sin tabla propia)

### TareaIngesta (dataclass)
Representa un PDF a procesar en el lote paralelo.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pdf_path` | `str` | Ruta absoluta al archivo PDF |
| `titulo` | `str` | Título del documento |
| `autor` | `str` | Autor (ej. "Ruta N Medellín") |
| `año` | `int \| None` | Año de publicación |
| `sector_gics` | `str \| None` | Código GICS del sector |
| `tipo` | `str` | Valor de `TipoDocumento` |
| `sectores_adicionales` | `list[str] \| None` | Sectores secundarios |

---

### ResultadoIngesta (dataclass)
Resultado de procesar un PDF; se serializa como JSON line a stdout.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `archivo` | `str` | Nombre de archivo (basename) |
| `documento_id` | `str \| None` | UUID del documento si exitoso |
| `n_chunks_creados` | `int` | Chunks nuevos insertados (0 si ya existían) |
| `estado` | `Literal["ok", "error"]` | Resultado del procesamiento |
| `error_msg` | `str \| None` | Mensaje de error si estado="error" |
| `procesados` | `int` | Contador acumulado hasta este resultado |
| `total` | `int` | Total de archivos en el lote |

---

### FragmentoEnriquecido (dataclass)
Chunk de texto obtenido de fuente secundaria para enriquecimiento del índice.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `texto` | `str` | Contenido del fragmento (≤ 512 tokens) |
| `titulo` | `str` | Título del artículo/página fuente |
| `autores` | `str \| None` | Autores en formato APA |
| `año` | `str` | Año de publicación o "s.f." |
| `url` | `str \| None` | URL canónica o DOI |
| `fuente` | `str` | `"openalex"` o `"web_enrichment"` |
| `sector_gics` | `str` | Sector al que pertenece el fragmento |
| `idioma` | `str` | Código ISO (ej. `"es"`, `"en"`) |

---

### EventoEnriquecimiento (no persistido, registrado en log de contexto)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sector_gics` | `str` | Sector que activó el enriquecimiento |
| `threshold_usado` | `float` | `rag_sector_reserve_threshold` en el momento |
| `score_max_previo` | `float` | Score máximo del retrieval previo al enriquecimiento |
| `fuentes_consultadas` | `list[str]` | `["openalex", "web"]` según lo activado |
| `n_fragmentos` | `int` | Fragmentos persistidos en pgvector |
| `resultado` | `str` | `"enriquecido"`, `"sin_evidencia"`, `"fallido"` |

---

## Tabla Existente — Sin Cambios de Esquema

**`embedding_vectorial`** (esquema `informes_ic`): Los `FragmentoEnriquecido` se persisten usando el mismo `EmbeddingRepo` y la misma tabla que los chunks de PDFs. La procedencia queda en `metadatos JSONB`:

```json
{
  "fuente": "openalex",
  "titulo": "Renewable Energy in Colombia",
  "autor": "García, J.",
  "año": "2023",
  "url": "https://doi.org/10.1234/abc",
  "sector_gics": "5510",
  "idioma": "en",
  "chunk_sha256": "abc123..."
}
```

---

## Invariante de Idempotencia

La tabla `embedding_vectorial` usa `chunk_sha256` (SHA-256 del texto del chunk) como clave de deduplicación. Re-ingestar el mismo fragmento — ya sea de PDF o de fuente secundaria — activa `ON CONFLICT DO NOTHING` y no crea duplicados.
