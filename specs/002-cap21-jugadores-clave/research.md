# Research: Cap 2.1 — Jugadores Clave Modular

**Feature**: 002-cap21-jugadores-clave | **Date**: 2026-08-19

---

## D1 — Acceso a datos StartIA para startups locales

**Decision**: Usar `EntidadRepository.list_locales_by_sector(segmento="startup")` existente.

**Rationale**: El ingesto StartIA ya puebla `entidades` con `segmento='startup'` y `alcance='local'` vía `parse_startia`. `list_locales_by_sector` filtra por `sector_gics = ANY(:sectores)` + `segmento='startup'`, devuelve `LocalRow` con nombre, ciudad, vertical e ingresos (`a_ing.valor` desde atributos). La ordenación por `n_menciones DESC, n_chunks DESC` prioriza las más referenciadas/documentadas. Para la priorización por tamaño, el campo `ventas_2025_cop` (atributo de StartIA) ya está en la DB; se puede añadir un sort secundario por ese atributo en la query o post-fetch.

**Alternatives considered**:
- Query directa SQL sobre `entidades` + `entidad_atributos` → rechazada (duplica lógica que ya vive en `_entidad_queries.py`; viola DRY).
- Indexar StartIA en pgvector para RAG → rechazada (ya están en el KB estructurado; no tiene sentido vectorizarlos de nuevo; la data es estructurada, no prosa).

**Gap identificado**: `list_locales_by_sector` no ordena por `ventas_2025_cop`. Se añadirá un parámetro opcional `order_by_revenue: bool = False` o se hará post-ordenación en el use case usando los atributos ya disponibles.

---

## D2 — Acceso a EMIS para referentes regionales

**Decision**: Usar `PGVectorStore.search()` con `sector_gics` + filtro adicional `fuente_tipo="emis"` en `embedding_repo.search_similar`.

**Rationale**: Los chunks EMIS ya están indexados con `fuente_tipo` distinguible. `search_similar` no acepta `fuente_tipo` como filtro hoy — se añade un parámetro opcional `fuente_tipo_filter: str | None = None` que agrega `AND e.fuente_tipo = :fuente_tipo` al WHERE. El impacto es mínimo (un parámetro, una condición SQL opcional). Esto garantiza que el sub-módulo Regional use exclusivamente EMIS como fuente primaria, con recall y ranking semántico propios del pgvector.

**Alternatives considered**:
- Filtrar por `metadatos->>'tipo_fuente' = 'informe_emis'` → factible pero `tipo_fuente` no siempre está seteado (solo tras `backfill_tipo_fuente_emis`); `fuente_tipo='emis'` es más robusto.
- Nueva query SQL directa que une `documento_id` con `documentos WHERE tipo='informe_emis'` → más costoso y duplica lógica del repo.
- Usar `fuente_tipo` como campo de búsqueda pasado por PGVectorStore → PGVectorStore ya pasa params al repo; se añade `fuente_tipo_filter` análogo a `sector_gics`.

**Gap identificado**: `PGVectorStore.search()` necesita exponer `fuente_tipo_filter`; `EmbeddingRepository.search_similar()` necesita el parámetro. Cambio localizado (~10 líneas en cada archivo, dentro de límite 300).

---

## D3 — Propuesta de candidatos globales (LLM)

**Decision**: Reusar `chain_02c_pares_globales` (ya existente) para la lista de candidatos. Limitar el output a 5 (vs. MAX_GLOBALES=12 actual).

**Rationale**: `chain_02c_pares_globales` ya produce una lista JSON de nombres globales con alta calidad. El sub-módulo 2.1.1 necesita exactamente eso: candidatos → búsqueda web → perfil. No se necesita una nueva chain para proponer nombres. Solo se pasa `max_results=5` al parser `parse_pares_globales` en el nuevo use case (el parser ya tiene cota `MAX_GLOBALES`; se usará `[:5]` en el llamador).

**Alternatives considered**:
- Nueva chain 2.1.1 dedicada → rechazada (duplica un chain que hace exactamente lo mismo; viola DRY).
- Reusar `DiscoverGlobales` completo → rechazada (DiscoverGlobales hace seed al KB + corroboración; aquí solo necesitamos los candidatos para buscar su perfil, no sembrarlos).

---

## D4 — Búsqueda web por candidato (perfil)

**Decision**: Para cada candidato (global o internacional), lanzar una búsqueda web dirigida con query `"{nombre} {sector_gics} business model revenue market strategy 2024 2025"`, recuperar ≤3 resultados por candidato, e ingestar en pgvector con `fuente_tipo="web"` de la sesión actual.

**Rationale**: Patrón ya establecido en `GenerateBenchmarking._buscar_por_entidad()`. Se reutiliza exactamente el mismo flujo: `WebConnector.search()` → `PGVectorStore.ingest(fuente_tipo="web")`. Tras ingestar todos los candidatos, se hace un único `store.search()` con query agregada. El query de perfil combina modelo de negocio + mercado + diferenciales, que es lo que el spec solicita.

**Alternatives considered**:
- Búsqueda web + LLM por candidato en paralelo (un llamado LLM por empresa) → rechazada para v1 (costo/latencia altos; el batch post-ingesta es más eficiente y ya está validado en prod).
- Un único llamado LLM con todo el contexto RAG → es exactamente lo que ya hace `chain_03_benchmarking`; la nueva chain 2.1.1 tiene el mismo patrón pero prompt especializado solo en el perfil de 5 globales.

---

## D5 — Estructura de módulos y archivos (SoC)

**Decision**: 3 use cases independientes + 3 chains + extensión de `embedding_repo` + nuevo tipo `Cap21Jugadores`.

**Rationale**: La Constitution I exige ≤300 líneas por archivo y separación de capas. Los tres sub-módulos tienen lógica de negocio distinta y fuentes primarias distintas → deben vivir en archivos separados. Cada chain tiene un prompt especializado diferente (perfil global vs. regional EMIS vs. startup disruptor) → chains separadas.

**Mapa de archivos nuevos/modificados**:

```
src/ic/domain/use_cases/
  generate_21_globales.py    # US1 — lógica Referentes Globales   [NUEVO]
  generate_21_regionales.py  # US2 — lógica Referentes Regionales [NUEVO]
  generate_21_startups.py    # US3 — lógica Startups/Disruptores  [NUEVO]
  generate_21_jugadores.py   # Orquestador de los 3 sub-módulos   [NUEVO]

src/ic/domain/chains/
  chain_cap2_21_globales.py  # Prompt perfil global (inglés → español)  [NUEVO]
  chain_cap2_21_regionales.py # Prompt perfil regional desde EMIS       [NUEVO]
  chain_cap2_21_startups.py  # Prompt perfil startup disruptor          [NUEVO]

src/ic/data/repositories/
  embedding_repo.py          # +parámetro fuente_tipo_filter en search_similar [MODIFICADO]

src/ic/infrastructure/retrieval/
  pgvector_store.py          # +parámetro fuente_tipo_filter en search() [MODIFICADO]

src/ic/shared/types.py       # +Cap21Globales, Cap21Regionales, Cap21Startups, Cap21Jugadores [MODIFICADO]

tests/
  test_generate_21_globales.py    [NUEVO]
  test_generate_21_regionales.py  [NUEVO]
  test_generate_21_startups.py    [NUEVO]
```

`generate_benchmarking.py` se modifica para llamar al orquestador `generate_21_jugadores` en lugar de generar 2.1 inline.

---

## D6 — Checkpoint keys para los sub-módulos

**Decision**: `"cap2_21_globales"`, `"cap2_21_regionales"`, `"cap2_21_startups"`.

**Rationale**: Siguen la convención `cap_nombre` existente del sistema de checkpoint. El prefijo `cap2_21_` los agrupa lógicamente y evita colisiones con `cap2`, `cap3`, etc. El orquestador `generate_21_jugadores` coordina los tres; el resultado ensamblado `cap2_21` puede también persistirse como checkpoint del cap 2.1 completo.

---

## D7 — Deduplicación cross-tier

**Decision**: Deduplicar por `_clave_exclusion(nombre)` en el orquestador antes del ensamblado final. Prioridad: Global > Regional > Startup.

**Rationale**: `_clave_exclusion` ya existe en `_entidad_queries.py` y normaliza nombres (quita acentos + sufijos legales). Si el mismo nombre aparece como global y como regional, el orquestador lo conserva en Globales y lo elimina de Regionales. La deduplicación ocurre en `generate_21_jugadores.py` al ensamblar los tres resultados.

---

## D8 — Ordenación de startups locales por tamaño

**Decision**: Post-ordenación en `generate_21_startups.py` por el atributo `ventas_2025_cop` (de `EntidadAtributo`). Si no disponible, usar `n_menciones` (ya en `LocalRow` via `list_locales_by_sector`).

**Rationale**: `list_locales_by_sector` ya retorna `LocalRow` con `nombre`, `ciudad`, `vertical`. El atributo `ventas_2025_cop` está en `entidad_atributos` pero no en `LocalRow`. Para v1, se usará `n_menciones`/`n_chunks` como proxy de tamaño (ya incluido en el ORDER BY actual de `list_locales_by_sector`). En v2 se puede añadir `ventas_2025_cop` a `LocalRow` con un JOIN adicional.
