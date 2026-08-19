# Contratos: EntidadRepository — DT-UI04f

## `list_competidores_by_sector`

### Precondiciones

- `sectores_gics`: uno o más códigos de grupo GICS no vacíos.
  - Si es `str`: se normaliza internamente a lista de un elemento.
  - Si la lista resulta vacía: retorna `[]` sin consultar BD (corto-circuito).
- `exclude_nombre`: nombre canónico de la empresa focal (puede ser None).

### Postcondiciones

- Retorna `list[str]` con nombres canónicos de competidores ordenados por relevancia descendente.
- **Sin duplicados**: si una misma entidad (`_clave_exclusion(nombre)` igual) aparece en
  múltiples sectores, se conserva solo la primera ocurrencia en el ranking.
- **Empresa focal excluida**: no aparece ninguna entidad cuyo `nombre` O cuyo `aliases[]`
  resuelva a la misma clave normalizada que `exclude_nombre`.
- Lista vacía si no hay candidatos, sin lanzar excepción.

### Invariantes

- `estado <> 'descartado'` siempre aplicado.
- `tipo IN ('competidor', 'empresa')` siempre aplicado.
- Si `alcance` es `"global"`, solo se incluyen entidades con `alcance = 'global'`.
- Backward compat: pasar un único `str` da el mismo resultado que antes.

### Ejemplo de contrato

```python
# Multi-sector → une candidatos de 1040 y 1050, sin duplicados
result = repo.list_competidores_by_sector(
    ["1040", "1050"], alcance="global", limit=6
)
# → list[str], len <= 6, sin entidades repetidas

# Mono-sector (compat) → idéntico a comportamiento previo
result = repo.list_competidores_by_sector("3020", limit=8)
# → list[str], idéntico al resultado anterior
```

---

## `list_ficha_atributos_by_sector`

### Precondiciones

- `sectores_gics`: uno o más códigos de grupo GICS no vacíos.
  - Normalización igual que `list_competidores_by_sector`.
- `nombres`: lista de nombres de entidades a buscar. Vacío → retorna `{}`.

### Postcondiciones

- Retorna `dict[str, dict[str, str]]` con `{nombre: {clave_ficha: valor}}`.
- Solo incluye entidades cuyo `sector_gics` esté en la lista dada.
- Prioridad de campos: nativo > alias de fuente > columna ciudad (sin cambios).
- Prioridad de estado: `verificado` > `candidato` (sin cambios, ORDER BY).

### Invariantes

- `sector_gics = ANY(:sectores)` en la WHERE.
- Si la lista de sectores está vacía, retorna `{}` sin consultar BD.
- Backward compat: pasar un único `str` da el mismo resultado que antes.

---

## `list_locales_by_sector` — sin cambios

Este método ya soporta multi-sector (DT-UI04b). No se toca en DT-UI04f.
