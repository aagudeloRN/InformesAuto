# DT-066 — Refactor: extraer query builders de entidad_repo.py

> Estado: **deuda pendiente**. Detectado durante DT-UI04f (2026-08-18, rama spec-driven-experiment).

## Problema

`src/ic/data/repositories/entidad_repo.py` tenía 527 líneas **antes** de DT-UI04f.
El límite arquitectónico del proyecto es 300 líneas (señal de violación de SoC definida en CLAUDE.md).

La violación es pre-existente al sprint actual; no se corrigió en DT-UI04f para no mezclar
refactor con funcionalidad (decisión D5 de `specs/001-multisector-benchmark/research.md`).

## Causa raíz

El archivo acumula:
- Queries SQL inline de 5+ métodos de consulta distintos
- Lógica de normalización y deduplicación post-fetch
- Helpers de ranking (`rank_by_product_overlap`)
- Helpers de exclusión (`_clave_exclusion`, `_es_focal`)

## Acción propuesta

Extraer en módulos separados dentro de `src/ic/data/repositories/`:

```
entidad_repo.py          ← orquestación, firma pública (target: ≤300 líneas)
_entidad_queries.py      ← builders de SQL (text() + parámetros)
_entidad_ranking.py      ← rank_by_product_overlap + helpers de scoring
```

Los helpers de exclusión (`_clave_exclusion`, `_es_focal`) son privados al repo
y pueden quedarse en el módulo principal si el resultado final cabe en 300 líneas.

## Criterios de aceptación

- `entidad_repo.py` ≤ 300 líneas tras el refactor
- 0 cambios en la interfaz pública (mismos métodos, mismas firmas)
- Todos los tests del proyecto pasan sin modificación
- ruff y black limpios

## Referencias

- `specs/001-multisector-benchmark/research.md` — decisión D5
- `specs/001-multisector-benchmark/plan.md` — sección Constitution Check, warning pre-existente
- CLAUDE.md §RED FLAGS: "Archivo o función que supera 300 líneas"
