# Data Model: Cap 2.1 — Jugadores Clave Modular

**Feature**: 002-cap21-jugadores-clave | **Date**: 2026-08-19

---

## Nuevos tipos en `shared/types.py`

### `Cap21Globales` *(dataclass)*

Resultado del sub-módulo Referentes Globales (2.1.1).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `texto` | `str` | Prosa markdown del sub-módulo `### Referentes Globales` |
| `candidatos` | `list[str]` | Nombres propuestos por el LLM (pre-búsqueda web) |
| `n_candidatos_con_web` | `int` | Candidatos que tuvieron resultados web |
| `retrieval_suficiente` | `bool` | True si al menos 1 candidato tiene chunks web |
| `chunks_usados` | `list[ChunkResult]` | Chunks usados para citas APA |

### `Cap21Regionales` *(dataclass)*

Resultado del sub-módulo Referentes Regionales (2.1.2).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `texto` | `str` | Prosa markdown del sub-módulo `### Referentes Regionales LatAm/Colombia` |
| `empresas_emis` | `list[str]` | Nombres extraídos de chunks EMIS |
| `n_con_emis` | `int` | Empresas con al menos 1 chunk EMIS |
| `retrieval_suficiente` | `bool` | True si hay chunks EMIS del sector |
| `chunks_usados` | `list[ChunkResult]` | Chunks usados para citas APA (incluye tipo fuente) |

### `Cap21Startups` *(dataclass)*

Resultado del sub-módulo Startups y Disruptores (2.1.3).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `texto` | `str` | Prosa markdown del sub-módulo `### Startups y Disruptores del sector` |
| `locales` | `list[str]` | Nombres de startups de StartIA incluidas |
| `internacionales` | `list[str]` | Nombres de disruptores internacionales (web) |
| `retrieval_suficiente` | `bool` | True si hay al menos 1 perfil (local o internacional) |
| `chunks_usados` | `list[ChunkResult]` | Chunks web de internacionales para citas APA |

### `Cap21Jugadores` *(dataclass)*

Resultado ensamblado de los tres sub-módulos; es la nueva entidad de salida de la sección 2.1 completa.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `texto` | `str` | Markdown completo de `## 2.1. Jugadores Clave` con los tres `###` |
| `globales` | `Cap21Globales \| None` | Resultado del sub-módulo Globales (None si falló/ausente) |
| `regionales` | `Cap21Regionales \| None` | Resultado del sub-módulo Regionales |
| `startups` | `Cap21Startups \| None` | Resultado del sub-módulo Startups |
| `retrieval_suficiente` | `bool` | True si al menos 1 sub-módulo tiene retrieval suficiente |
| `chunks_usados` | `list[ChunkResult]` | Agregado de chunks de todos los sub-módulos |

---

## Modificaciones a entidades existentes

### `EmbeddingRepository.search_similar` — nuevo parámetro

```
fuente_tipo_filter: str | None = None
```

Cuando no es `None`, añade `AND e.fuente_tipo = :fuente_tipo` al WHERE de la query vectorial. Permite que el sub-módulo Regional haga retrieval exclusivo de chunks EMIS.

### `PGVectorStore.search` — nuevo parámetro

```
fuente_tipo_filter: str | None = None
```

Se pasa directamente a `EmbeddingRepository.search_similar`. Default `None` preserva comportamiento existente (invariante total).

---

## Entidades del KB (sin cambios de esquema)

Estas entidades ya existen y se consultan sin modificación de esquema:

### `Entidad` (tabla `informes_ic.entidades`)

Usada por el sub-módulo Startups para recuperar startups locales:
- `segmento = 'startup'` — identifica startups (vs. empresas establecidas)
- `alcance = 'local'` — filtra jugadores locales colombianos
- `sector_gics` — filtra por sector GICS del análisis

Consultada vía `list_locales_by_sector(segmento="startup")` existente (sin cambios de esquema).

### `Documento` + `Embedding` (tablas de indexado pgvector)

Usadas por el sub-módulo Regional para recuperar chunks EMIS:
- `fuente_tipo = 'emis'` — identifica chunks de EMIS (ya existente en esquema)
- `metadatos->>'sector_gics'` — filtra por sector

No requieren cambios de esquema; solo extensión de la query de búsqueda.

---

## Checkpoint keys (convención existente, nuevas claves)

| Sub-módulo | Checkpoint key | Tipo serializado |
|------------|---------------|-----------------|
| Referentes Globales | `cap2_21_globales` | `Cap21Globales` |
| Referentes Regionales | `cap2_21_regionales` | `Cap21Regionales` |
| Startups y Disruptores | `cap2_21_startups` | `Cap21Startups` |
| Ensamblado 2.1 | `cap2_21` | `Cap21Jugadores` |

Requieren registro en `_REGISTRY` de `checkpoint_serde.py`.

---

## Flujo de datos entre sub-módulos

```
N0 (empresa + GICS)
  │
  ▼
generate_21_jugadores.py  ← orquestador
  ├── generate_21_globales.py
  │     chain_02c_pares_globales (LLM → candidatos)
  │     WebConnector.search (por candidato)
  │     PGVectorStore.search (retrieval post-ingesta)
  │     chain_cap2_21_globales (LLM → texto prosa)
  │     → Cap21Globales
  │
  ├── generate_21_regionales.py
  │     PGVectorStore.search(fuente_tipo_filter="emis")
  │     WebConnector.search (complemento opcional)
  │     chain_cap2_21_regionales (LLM → texto prosa)
  │     → Cap21Regionales
  │
  └── generate_21_startups.py
        EntidadRepository.list_locales_by_sector(segmento="startup")
        [Web: ≤2 internacionales]
        chain_cap2_21_startups (LLM → texto prosa)
        → Cap21Startups
  │
  ▼
Cap21Jugadores (ensamblado) → checkpoint "cap2_21"
  │
  ▼
generate_benchmarking.py (Cap 2.2, 2.4, 2.5 — recibe 2.1 como contexto)
```
