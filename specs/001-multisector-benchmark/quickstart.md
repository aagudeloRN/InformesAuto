# Quickstart: Validación DT-UI04f

## Prerequisitos

- PostgreSQL corriendo (`docker compose up -d`)
- BD `informes_ic` poblada con entidades de prueba (al menos 2 sectores distintos)
- `pytest` instalado (`uv run pytest`)

## Escenario 1 — Multi-sector sin duplicados (SC-001 / SC-002)

**Qué valida**: `list_competidores_by_sector` retorna competidores de múltiples
sectores, deduplicados, en orden de relevancia.

```bash
# Test unitario (FakeSession, sin BD real)
uv run pytest tests/test_kb_entidades.py -k "multisector" -v

# Test de integración (requiere BD)
uv run pytest tests/test_kb_entidades.py -k "competidores" -m db -v
```

**Resultado esperado**: todos pasan; el log muestra que competidores de
ambos sectores aparecen una sola vez.

## Escenario 2 — Exclusión por alias (SC-003)

**Qué valida**: empresa focal registrada con alias distinto al nombre de búsqueda
no aparece en resultados.

```bash
uv run pytest tests/test_kb_entidades.py -k "alias" -v
```

**Resultado esperado**: el test confirma que la entidad cuyo alias coincide con
`exclude_nombre` normalizado no aparece en la lista de salida.

## Escenario 3 — Backward compatibility (SC-004)

**Qué valida**: tests preexistentes de `list_competidores_by_sector` pasan sin
modificación al pasarles un `str`.

```bash
uv run pytest tests/test_kb_entidades.py -v
uv run pytest tests/test_dt064_fichas.py -v
```

**Resultado esperado**: 0 fallos, 0 errores. Mismos resultados que antes del cambio.

## Escenario 4 — Fichas multi-sector (integración con generate_n1)

**Qué valida**: `list_ficha_atributos_by_sector` acepta lista y devuelve fichas
de competidores de ambos sectores.

```bash
uv run pytest tests/test_dt064_fichas.py -v
```

**Resultado esperado**: todos los tests de fichas pasan; si se añade un test
con lista, retorna fichas de los dos sectores.

## Escenario 5 — Suite rápida completa (SC-005)

```bash
uv run pytest -x --ignore=tests/test_convergencia_e2e.py -q
```

**Resultado esperado**: 0 fallos. ruff también en verde:

```bash
uv run ruff check src/ tests/ && uv run black --check src/ tests/
```

## Notas de validación

- Los tests unitarios usan `_FakeSession` (sin BD real); los de integración
  usan el marcador `@pytest.mark.db` y requieren BD levantada.
- El comportamiento de `list_locales_by_sector` no cambia; sus tests sirven
  como regresión del patrón `ANY(:sectores)` que se replica en globales.
- Verificar que el log de `run_n1_parallel` muestra `"sectores globales=[...]"`
  con más de un elemento cuando la empresa tiene multi-sector CIIU.
