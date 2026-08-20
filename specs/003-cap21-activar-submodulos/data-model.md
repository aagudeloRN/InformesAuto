# Data Model: Cap 2.1 — Activar Sub-módulos Modulares

**Date**: 2026-08-20 | **Feature**: 003-cap21-activar-submodulos

No hay cambios al modelo de datos en esta feature. Los tipos `Cap21Globales`, `Cap21Regionales`, `Cap21Startups` y `Cap21Jugadores` ya existen en `src/ic/shared/types.py` y no se modifican.

## Sector Cache Key

El cache sectorial reutiliza la tabla de checkpoints existente (`CheckpointRepository`). No se crea ningún schema nuevo.

**Clave de sector**: `f"sector_{sector_gics_code}_{sub_gics or 'any'}"` (ej. `"sector_3020_3020"`)

Los sub-capítulos se persisten bajo las claves:
- `cap2_21_globales` → objeto `Cap21Globales` serializado
- `cap2_21_regionales` → objeto `Cap21Regionales` serializado
- `cap2_21_startups` → objeto `Cap21Startups` serializado

## API change: Generate21Startups

| Parámetro | Antes | Después |
|-----------|-------|---------|
| `entidad_repo` | `EntidadRepository` (required) | `EntidadRepository \| None = None` |
| `db_factory` | — | `Callable \| None = None` (nuevo, opcional) |

**Invariante**: se debe pasar exactamente uno de `entidad_repo` o `db_factory`. Si ambos son `None`, el sub-módulo opera sin startups locales (degradado silencioso).
