# Data Model: Multi-sector Benchmarking (DT-UI04f)

## Entidades del dominio

### Entidad (`informes_ic.entidades`)

Empresa canónica del KB. Atributos relevantes para esta feature:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | BIGINT PK | Identificador único |
| `nombre` | TEXT | Forma display |
| `nombre_normalizado` | TEXT | Clave de dedup (sin sufijos, minúsculas) |
| `sector_gics` | TEXT | Código GICS primario (ej: `"3020"`) |
| `alcance` | TEXT | `"global"` / `"local"` / NULL |
| `estado` | TEXT | `"candidato"` / `"verificado"` / `"descartado"` |
| `aliases` | JSONB | Lista de denominaciones alternativas (ej: `["NOEL", "Compañía de Galletas NOEL"]`) |
| `n_chunks` | BIGINT | Señal de evidencia (tiebreak de ranking) |

**Invariante**: `aliases` ya existe como JSONB en el schema; no se requiere migración.

### EntidadSector (`informes_ic.entidad_sectores`)

Membresía sectorial multi-sector (usada por `list_locales_by_sector`).
Esta feature no modifica la tabla; `list_competidores_by_sector` sigue usando
la columna `sector_gics` de `entidades` directamente (ver research D2).

### EntidadAtributo (`informes_ic.entidad_atributos`)

Atributos de ficha (portafolio, ingresos, presencia, etc.). La query de
`list_ficha_atributos_by_sector` filtra por `e.sector_gics = ANY(:sectores)`.
No hay cambios estructurales.

## Cambios de firma de métodos

### `list_competidores_by_sector` — antes vs después

**Antes**:
```
list_competidores_by_sector(
    sector_gics: str,
    productos_terms: set[str] | None = None,
    alcance: str | None = None,
    limit: int = 8,
    exclude_nombre: str | None = None,
) -> list[str]
```

**Después** (parámetro renombrado, tipo extendido):
```
list_competidores_by_sector(
    sectores_gics: str | Sequence[str],   # antes: sector_gics: str
    productos_terms: set[str] | None = None,
    alcance: str | None = None,
    limit: int = 8,
    exclude_nombre: str | None = None,
) -> list[str]
```

Cambios internos:
- Normalización: `str` → `[str]`; `Sequence[str]` → filtrar vacíos
- SQL: `WHERE e.sector_gics = ANY(:sectores)` (bind con lista Python)
- SELECT añade: `e.aliases`
- Dedup post-fetch por `_clave_exclusion(nombre)` (conserva el de mayor score)
- Exclusión de empresa focal: chequea `nombre` canónico Y cada elemento de `aliases`

### `list_ficha_atributos_by_sector` — antes vs después

**Antes**:
```
list_ficha_atributos_by_sector(
    sector_gics: str,
    nombres: list[str],
) -> dict[str, dict[str, str]]
```

**Después**:
```
list_ficha_atributos_by_sector(
    sectores_gics: str | Sequence[str],   # antes: sector_gics: str
    nombres: list[str],
) -> dict[str, dict[str, str]]
```

Cambios internos:
- Normalización: igual que `list_competidores_by_sector`
- SQL: `WHERE e.sector_gics = ANY(:sectores)` en lugar de `= :sector`
- Sin cambios en dedup (ya usa `setdefault` con prioridad por ORDER BY)

## Flujo de datos — tier global multi-sector

```
ctx.empresa.actividad_ciiu + ctx.gics.grupo_gics
        ↓
sectores_ancla_local(g_code, ciiu_ancla)   ← ya existe, devuelve list[str]
        ↓
list_competidores_by_sector(sectores_gics=sectores, alcance="global", ...)
        ↓
dedup por _clave_exclusion + exclusión por aliases
        ↓
kb_competidores: list[str]   → GenerateBenchmarking
```

## Exclusión de empresa focal — lógica extendida

```
_clave_exclusion(nombre_focal)
    → compara contra: _clave_exclusion(r.nombre)
    → Y contra: _clave_exclusion(alias) for alias in (r.aliases or [])
```

No se necesita cambiar `_clave_exclusion`; solo ampliar el predicado de exclusión
en el list comprehension de `list_competidores_by_sector`.
