# Fase 29 — DT-050: Base Colombia local + StartIA (componente LOCAL)

> Cierre 2026-07-31. Rama `feature/fase29-dt050` (4 commits). Gate: ruff 0 (src/ tests/),
> 539 fast tests (baseline 522 + 17 nuevos). Flag `anclaje_local_enabled` default-OFF (invariante).

## Contexto

Con DT-062/DT-062b (mergeados) el tier de **clase mundial** (2.1.1) tiene motor. DT-050 construye el
**componente LOCAL** (`alcance=local`): un directorio de empresas colombianas + startups que alimenta
los tiers **regional (2.1.2)** y **startups (2.1.3)**, cerrando la mitad local de DT-049 (evidencia
local delgada) y dando **memoria** (hoy los locales se recomputan por web cada corrida y ADR-013 los
purga).

## Hallazgos

1. **El "Sector (Local)" del Excel trae el CIIU embebido.** EmpresasColombia (97.941 filas, header en
   la fila 8) codifica la clasificación como texto con el código CIIU Rev.4 entre paréntesis
   ("…(M7010)", "…(F4111)", "…(A0141)"), extraíble por regex en el **99.5 %** de las filas
   (97.935 con NIT). No hace falta un mapeo texto→GICS manual sobre 21.431 etiquetas distintas.
2. **El mapeo por sección era demasiado grueso.** `ciiu_gics.py` mapea a nivel de **sección** CIIU
   (letra) → multivaluado (sección C → 10 grupos GICS): sirve para *acotar* al LLM, no para *asignar*
   un sector único. Se añadió grano por **división (2 díg)** (`ciiu_division_to_gics`), con overrides
   de **clase (4 díg)** para la ambigüedad del comercio (alimentos/farmacia → 3010 básicos, no 2550
   discrecional). Grupo 3020 refina food/beverage/tobacco con `resolve_sub_gics` (reuso DT-061).
3. **Multi-sector es real y es feature.** Filas EMIS con varias actividades ("…(M7010); …(M7020)") y
   startups multi-vertical ("FINTECH; HRTECH") → **N membresías** por entidad en la tabla nueva
   `entidad_sectores` (dedup por NIT en `entidades`). `n_sectores` pasa de proxy a COUNT real.
4. **StartIA arregla el tier 2.1.3 en general.** Las 32 verticales del catálogo resuelven a GICS;
   341/388 startups obtienen membresía (food gana 32; casi todos los grupos quedan cubiertos).
5. **Ranking local por tamaño.** Los locales no tienen `n_chunks`/`n_menciones`; se ordenan por
   verificado → match de sub → **ingreso operativo** (proxy numérico: se recorta en la coma decimal y
   se dejan dígitos).

## Decisiones (confirmadas con el usuario en Plan Mode)

- **Anclaje = AMBOS** (T3): contexto estructurado (`{jugadores_locales}`) **y** búsqueda web dirigida
  por las top-N locales. No diluye el global: el path global usa `alcance=global`; el local su propio
  método `list_locales_by_sector(alcance=local)`.
- **entidad_sectores = core ahora** (T4): tabla de membresías con provenance; el anclaje local hace
  JOIN. **Pero** el path del tier GLOBAL (`list_competidores_by_sector`) **no se migró** al JOIN: se
  conserva leyendo `entidades.sector_gics` para no arriesgar el invariante DT-062b sin poder correr el
  E2E 3020 aquí (cláusula del plan / TIER 2). El backfill ya pobló entidad_sectores para el KB
  existente (idempotente); migrar la consulta global al JOIN queda para el sucesor, con el E2E de gate.

## Componentes

| Capa | Archivo | Rol |
|---|---|---|
| model | `data/models/entidad.py` | tabla `entidad_sectores` + columna `segmento` (ensure_* idempotente) |
| shared | `shared/constants/ciiu_gics.py` | `extract_(all_)ciiu_from_text`, `ciiu_division_to_gics` |
| shared | `shared/constants/startia_gics.py` | crosswalk Vertical→GICS (cp1252) |
| shared | `shared/ingest/` | DTOs puros + parsers EMIS/StartIA (normalizador inyectado) |
| infra | `infrastructure/sources/excel_reader.py` | wrapper openpyxl (read_only) |
| data | `data/repositories/entidad_repo.py` | `upsert_sector_membership`, `list_locales_by_sector`, `backfill_*`, `recompute_n_sectores` |
| domain | `domain/kb/relevance.py` | `LocalRow` + `format_jugadores_locales` (puro) |
| domain | `domain/chains/chain_03_benchmarking.py` | slot `{jugadores_locales}` |
| domain | `domain/use_cases/generate_benchmarking.py` | params `kb_locales` + `jugadores_locales_ctx` |
| domain | `domain/use_cases/generate_n1.py` | cableado `_fn_cap2` (flag OFF = invariante) |
| config | `shared/config.py` | `anclaje_local_enabled`, `anclaje_local_top_n` |
| scripts | `scripts/seed_empresas_colombia.py`, `seed_startia.py`, `backfill_entidad_sectores.py` | siembra/backfill offline con `--dry-run` |

## Verificación E2E (manual, pendiente en máquina del usuario)

1. `uv run python scripts/seed_empresas_colombia.py --dry-run` (~98k, muestra de mapeos) → real en tmux.
2. `uv run python scripts/seed_startia.py --dry-run` (388) → real.
3. `uv run python scripts/backfill_entidad_sectores.py` (idempotente; ya ejecutado sobre el KB
   existente durante el smoke → 17.281 membresías, re-run 0).
4. Re-correr E2E 3020 con `discover_globales_enabled` → confirmar invariante DT-062b intacto.
5. Con `anclaje_local_enabled=true` (Alpina/3020): fichas 2.1.2/2.1.3 pobladas con jugadores del
   directorio (Nutresa, Colombina…), 0 huérfanas, tier global sin locales.

## Deuda / sucesores

- **DT-050b (migrar global al JOIN):** unificar `list_competidores_by_sector` sobre `entidad_sectores`,
  con el E2E 3020 (disjuntas food/beverage/tobacco + restore) como gate duro.
- **Startups globales** (scaleups/unicornios) → sub-tier del componente GLOBAL (patrón DT-062). Parqueado.
- **Curación humana** del directorio (panel HITL, F24/F25): pasar `candidato`→`verificado`.
- **Rendimiento de la siembra:** los upserts commitean por-llamada (~98k). Correr en tmux/nohup; si
  molesta, batchear commits.

---

## Prompt de arranque — siguiente ventana

> ROL: Eres Claude Code, ingeniero de InformesAuto (`~/Test/InformesAuto`): informes de inteligencia
> competitiva (RAG local pgvector + Ollama, LangChain, capas). **DT-050 CERRADO y MERGEADO** a
> `develop`: directorio LOCAL (EmpresasColombia + StartIA) → tiers 2.1.2/2.1.3. Modelo: KB `entidades`
> (dedup NIT, `alcance=local`, `segmento`) + tabla `entidad_sectores` (multi-sector, provenance,
> `n_sectores`=COUNT). Mapeo CIIU **por división** (`ciiu_division_to_gics`). Anclaje local vía flag
> `anclaje_local_enabled` (default OFF). El path GLOBAL sigue leyendo `entidades.sector_gics` (no
> migrado al JOIN para no arriesgar el invariante DT-062b sin E2E). Ver `FASE29_HALLAZGOS.md`,
> memoria `project_fase29_dt050_estado`.
>
> PRIMERO (manual, si no se ha hecho): sembrar EMIS (`scripts/seed_empresas_colombia.py`, tmux/nohup)
> + StartIA (`scripts/seed_startia.py`) + `scripts/backfill_entidad_sectores.py`; luego E2E 3020 con
> `anclaje_local_enabled=true` para validar fichas 2.1.2/2.1.3 (Nutresa/Colombina…, 0 huérfanas,
> global sin locales) y `discover_globales_enabled` para reconfirmar el invariante DT-062b.
>
> ELIGE la siguiente tarea (Plan Mode): **(A) DT-050b** — migrar `list_competidores_by_sector` global
> al JOIN `entidad_sectores` (unificar el modelo), con el E2E 3020 (food/beverage/tobacco disjuntas +
> restore) como gate duro; **(B) DT-060** — revisión RAG + reingesta gated A/B (metadata posicional,
> chunking estructural, tablas EMIS); **(C) HITL Fase 24** (Gap Auditor, ADR-015) — incluye la
> curación del directorio (`candidato`→`verificado`). Confirmar restricciones TIER 1 (sin nombres de
> modelo, wrappers en `infrastructure/`, migraciones idempotentes, nunca `git add -A` — respetar
> `documentos_sectoriales/FuentesExternas/` sin trackear).
