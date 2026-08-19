# Contracts: Cap 2.1 — Jugadores Clave Modular

**Feature**: 002-cap21-jugadores-clave | **Date**: 2026-08-19

Estos contratos definen las interfaces públicas de los tres use cases nuevos y las modificaciones
a interfaces existentes. Son la fuente de verdad para los tests (`_FakeSession` / mocks).

---

## UC-1: `Generate21Globales`

```
Módulo: src/ic/domain/use_cases/generate_21_globales.py

Constructor:
  chain_candidatos: Runnable          # chain_02c_pares_globales
  chain_perfil: Runnable              # chain_cap2_21_globales (nuevo)
  store: PGVectorStore
  web_connector: WebConnector
  max_empresas: int = 5               # FR-003

Método principal:
  execute(
    nombre_empresa: str,
    descripcion_empresa: str,
    sector_gics: str,
    sector_gics_code: str | None,
    empresa_id: UUID | None,
    productos: str = "",              # para steering del chain_candidatos
  ) -> Cap21Globales

Contrato de comportamiento:
  1. Llama chain_candidatos con sector_gics + productos → lista de candidatos (str[])
  2. Filtra: excluye nombre_empresa y variantes normalizadas
  3. Recorta a max_empresas candidatos
  4. Por cada candidato: web_connector.search(query_perfil) → store.ingest(fuente_tipo="web")
  5. store.search(retrieval_query, sector_gics=sector_gics_code, empresa_id=empresa_id)
  6. Si chunks < MIN_CHUNKS (3): devuelve Cap21Globales con texto=párrafo_ausencia, retrieval_suficiente=False
  7. chain_perfil.invoke(payload) → texto prosa con perfiles
  8. Devuelve Cap21Globales(texto, candidatos, n_candidatos_con_web, retrieval_suficiente=True, chunks_usados)
```

**Invariantes**:
- Si chain_candidatos devuelve `[]`: no se lanza ninguna búsqueda web → ausencia.
- Si un candidato no retorna chunks web: se omite de la prosa (no se fabrica perfil).
- La empresa analizada (nombre_empresa + aliases) NUNCA aparece en candidatos.

---

## UC-2: `Generate21Regionales`

```
Módulo: src/ic/domain/use_cases/generate_21_regionales.py

Constructor:
  chain_perfil: Runnable              # chain_cap2_21_regionales (nuevo)
  store: PGVectorStore
  web_connector: WebConnector
  max_empresas: int = 3               # FR-005

Método principal:
  execute(
    nombre_empresa: str,
    descripcion_empresa: str,
    sector_gics: str,
    sector_gics_code: str | None,
    empresa_id: UUID | None,
  ) -> Cap21Regionales

Contrato de comportamiento:
  1. store.search(query, sector_gics=sector_gics_code, fuente_tipo_filter="emis") → chunks_emis
  2. Si len(chunks_emis) < MIN_CHUNKS (3): devuelve Cap21Regionales con ausencia + retrieval_suficiente=False
  3. Extrae nombres de empresas de los chunks EMIS (NER simple o regex sobre metadatos)
  4. Selecciona hasta max_empresas por relevancia/score de los chunks
  5. Complemento web (opcional): por cada empresa sin suficiente contexto EMIS, lanza búsqueda web
  6. chain_perfil.invoke(payload con chunks EMIS + complemento web) → texto prosa
  7. Devuelve Cap21Regionales(texto, empresas_emis, n_con_emis, retrieval_suficiente=True, chunks_usados)
```

**Invariantes**:
- Sin chunks EMIS → ausencia inmediata; NO se hace web-only para regionales (FR-004).
- El complemento web solo se lanza si hay chunks EMIS de base (enriquecimiento, no reemplazo).
- Los perfiles se redactan mayoritariamente desde EMIS; el web es secundario (FR-006).

---

## UC-3: `Generate21Startups`

```
Módulo: src/ic/domain/use_cases/generate_21_startups.py

Constructor:
  chain_perfil: Runnable              # chain_cap2_21_startups (nuevo)
  store: PGVectorStore
  web_connector: WebConnector
  entidad_repo: EntidadRepository
  max_locales: int = 3                # FR-008
  max_internacionales: int = 2        # FR-009

Método principal:
  execute(
    nombre_empresa: str,
    descripcion_empresa: str,
    sector_gics: str,
    sector_gics_code: str | None,
    sectores_ancla: list[str],        # para list_locales_by_sector
    empresa_id: UUID | None,
  ) -> Cap21Startups

Contrato de comportamiento:
  1. entidad_repo.list_locales_by_sector(sectores_ancla, segmento="startup", limit=max_locales, exclude_nombre=nombre_empresa)
     → lista de LocalRow (startups locales StartIA)
  2. Por cada startup local: format_startup_profile(local_row) → bloque de texto desde atributos KB
  3. Si len(startups_locales) < max_locales: buscar internacionales vía web
     web_connector.search(query_internacionales) → store.ingest(fuente_tipo="web")
     store.search(query, sector_gics=sector_gics_code, fuente_tipo_filter=None) → chunks_internacionales
  4. Si no hay startups locales Y no hay chunks internacionales: devuelve Cap21Startups con ausencia
  5. chain_perfil.invoke(payload con locales + internacionales) → texto prosa
  6. Devuelve Cap21Startups(texto, locales, internacionales, retrieval_suficiente, chunks_usados)
```

**Invariantes**:
- Los perfiles de locales se construyen PRIMERO desde `EntidadAtributo` (datos KB), sin llamada LLM de perfil si los datos son suficientes. Solo entra el LLM para redactar la prosa final.
- Las startups locales aparecen ANTES que las internacionales en la prosa.
- Deduplicación: si un nombre local aparece en la búsqueda de internacionales, se usa solo como local.

---

## UC-4: `Generate21Jugadores` (orquestador)

```
Módulo: src/ic/domain/use_cases/generate_21_jugadores.py

Constructor:
  gen_globales: Generate21Globales
  gen_regionales: Generate21Regionales
  gen_startups: Generate21Startups

Método principal:
  execute(
    nombre_empresa: str,
    descripcion_empresa: str,
    sector_gics: str,
    sector_gics_code: str | None,
    sectores_ancla: list[str],
    empresa_id: UUID | None,
    productos: str = "",
    ctx: _PipelineContext | None = None,   # para checkpoint/resume
  ) -> Cap21Jugadores

Contrato de comportamiento:
  1. Restaurar desde checkpoint si ctx disponible: globales, regionales, startups
  2. Ejecutar sub-módulos no restaurados (pueden correr en paralelo vía ThreadPoolExecutor)
  3. Deduplicar cross-tier por _clave_exclusion (Globales > Regional > Startup)
  4. Ensamblar texto: "## 2.1. Jugadores Clave\n\n" + globales.texto + regionales.texto + startups.texto
  5. Persistir cada sub-módulo al checkpoint (cap2_21_globales, cap2_21_regionales, cap2_21_startups)
  6. Devuelve Cap21Jugadores con texto ensamblado y referencias a los tres sub-resultados
```

---

## Modificación de interfaces existentes

### `EmbeddingRepository.search_similar` — parámetro adicional

```python
def search_similar(
    self,
    vec: list[float],
    k: int = 10,
    fetch_k: int = 20,
    sector_gics: str | None = None,
    sector_estricto: bool = False,
    empresa_id=None,
    fuente_tipo_filter: str | None = None,   # NUEVO — default None preserva invariante
) -> list[ChunkResult]: ...
```

Cuando `fuente_tipo_filter` no es `None`: agrega `AND e.fuente_tipo = :fuente_tipo` al WHERE.
Todos los callers existentes que no pasan `fuente_tipo_filter` no se ven afectados.

### `PGVectorStore.search` — parámetro adicional

```python
def search(
    self,
    query: str,
    sector_gics: str | None = None,
    empresa_id=None,
    fuente_tipo_filter: str | None = None,   # NUEVO — default None
) -> list[ChunkResult]: ...
```

Pasa `fuente_tipo_filter` a `EmbeddingRepository.search_similar`. Invariante total para callers existentes.
