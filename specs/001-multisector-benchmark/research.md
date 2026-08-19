# Research: Multi-sector Benchmarking — DT-UI04f

## Hallazgos clave del código existente

### D1 — `list_locales_by_sector` ya es multi-sector (DT-UI04b)

- **Decision**: No cambiar `list_locales_by_sector`. El método ya acepta
  `str | Sequence[str]`, hace `JOIN entidad_sectores` con
  `WHERE es.sector_gics = ANY(:sectores)` y deduplica por `_clave_exclusion`.
  Los tests de `test_kb_entidades.py` (líneas 273-319) ya lo verifican.
- **Rationale**: El trabajo de multi-sector para locales está completo. Solo
  necesitamos replicar el patrón en `list_competidores_by_sector` y
  `list_ficha_atributos_by_sector`.

### D2 — `list_competidores_by_sector` usa columna directa, no JOIN

- **Decision**: Cambiar la query de `WHERE e.sector_gics = :sector` a
  `WHERE e.sector_gics = ANY(:sectores)` usando la columna `sector_gics`
  de la tabla `entidades` (no el JOIN con `entidad_sectores`).
- **Rationale**: Los competidores globales se siembran con `upsert_entidad`
  que escribe `sector_gics` directamente en `entidades`. No todos tienen
  entrada en `entidad_sectores` (eso es para el KB local DT-050). Cambiar a
  JOIN rompería el acceso a globales sembrados por `DiscoverGlobales`.
- **Alternativa rechazada**: JOIN con `entidad_sectores` (igual que locales).
  Rechazado porque el flujo de siembra de globales no garantiza registros en
  esa tabla.

### D3 — Campo `aliases` JSONB ya existe en `entidades`

- **Decision**: No hay migración de schema necesaria. `Entidad.aliases` ya es
  `JSONB` (entidad.py línea 77). La exclusión por alias se implementa
  añadiendo `e.aliases` al SELECT de `list_competidores_by_sector` y
  verificando en Python si el nombre de la empresa focal coincide con algún
  alias de la entidad candidata.
- **Rationale**: Eficiente — los rows ya se traen todos para el re-rank.
  Añadir un check en Python sobre `aliases` no agrega round-trips a BD.
- **Alternativa rechazada**: WHERE en SQL con `aliases @> :alias_json`. Más
  difícil de parametrizar y menos claro; además la exclusión del nombre
  canónico ya es en Python, conviene mantenerlos juntos.

### D4 — Fuente de los sectores GICS para el tier global

- **Decision**: En `generate_n1.py`, el multi-sector para globales se construye
  igual que para locales: `sectores_ancla_local(g_code, ciiu_ancla)` ya
  devuelve la lista (grupo LLM + canónico CIIU). Reusar esa misma lista para
  los globales, renombrando la variable o creando un alias semántico.
- **Rationale**: `sectores_ancla_local` está en `ic.shared.constants.ciiu_gics`
  y combina el código del grupo del LLM con el código GICS canónico del CIIU.
  Es exactamente lo que se necesita para globales también. El nombre "ancla_local"
  es una etiqueta, no una restricción de tipo de entidad.
- **Alternativa rechazada**: Extender `ClasificacionGICS` con una lista de
  grupos. Modificar `classify_gics.py` está explícitamente fuera de scope.

### D5 — `entidad_repo.py` ya supera el límite de 300 líneas

- **Decision**: El archivo tiene 527 líneas (antes del cambio), lo que ya viola
  la regla de SoC del proyecto. Los cambios de DT-UI04f agregan ~20-30 líneas
  más. NO se extrae un query builder como parte de este PR; se registra la deuda
  en un ticket separado (DT-XXX) para no mezclar refactor con feature.
- **Rationale**: Refactorizar un archivo de 527 líneas en el mismo PR que la
  feature aumenta el riesgo de romper tests y complica el review. La regla de
  "extraer si SUPERA 300 líneas tras el cambio" aplica a código nuevo; el
  umbral ya está superado por código preexistente.
- **How to apply**: Al cerrar este PR, abrir un ticket de refactor de
  `entidad_repo.py` como deuda técnica documentada.

### D6 — Compatibilidad hacia atrás

- **Decision**: Cambiar la firma de `list_competidores_by_sector` de
  `sector_gics: str` a `sectores_gics: str | Sequence[str]` con normalización
  interna (igual que `list_locales_by_sector`). Los tests existentes pasan
  un `str` y seguirán funcionando sin modificación.
- **Rationale**: El patrón ya está probado en `list_locales_by_sector` (líneas
  288-294 del test: `"3020"` se normaliza a `["3020"]` internamente).

### D7 — `list_ficha_atributos_by_sector` — no usa EntidadSector

- **Decision**: Cambiar la WHERE a `ANY(:sectores)` sobre `e.sector_gics` (mismo
  patrón que D2). No cambiar el JOIN structure de la query (ya une `entidades`
  con `entidad_atributos`).
- **Rationale**: La query de fichas filtra por `e.sector_gics` de la entidad.
  Los competidores globales tienen `sector_gics` en `entidades`. Cambio mínimo.

## Archivos afectados (confirmado por grep)

| Archivo | Cambio | Riesgo |
|---------|--------|--------|
| `src/ic/data/repositories/entidad_repo.py` | Firmas + SQL + alias exclusion | Medio |
| `src/ic/domain/use_cases/generate_n1.py` | Pasar lista sectores a las 3 llamadas | Bajo |
| `src/ic/data/models/entidad.py` | Sin cambios (aliases ya existe) | Ninguno |
| `src/ic/domain/use_cases/discover_globales.py` | Sin cambios | Ninguno |
| `src/ic/domain/use_cases/generate_benchmarking.py` | Sin cambios | Ninguno |

## Tests existentes que deben seguir verdes (sin modificar)

- `test_kb_entidades.py` — `test_list_competidores_*` (líneas 201-325)
- `test_dt064_fichas.py` — `list_ficha_atributos_by_sector` (líneas 205-246)
- `test_discover_globales.py` — sin cambios en DiscoverGlobales
