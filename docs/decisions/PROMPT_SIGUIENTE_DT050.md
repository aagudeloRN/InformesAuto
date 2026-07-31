# Prompt de arranque — DT-050 (base Colombia local + startia)

> Pegar como primer mensaje de una ventana limpia. Misma estructura que el prompt DT-062.
> **Orden:** esta ventana va DESPUÉS de DT-062b (reuso por sub-actividad). DT-062 **y** DT-062b ya
> están CERRADOS y MERGEADOS a develop (F27 merge `45ba54d`, F28 rama `feature/fase28-dt062b`).

## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto): informes de
inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas). DT-062
(descubrimiento LLM de globales corroborado por web) y DT-062b (reuso por **sub-actividad**, no por
grupo) están CERRADOS y MERGEADOS a develop: el tier de clase mundial (2.1.1) recibe globales
recomendados por LLM y corroborados por web, restringidos a la sub-actividad de la empresa analizada
(`chain_02c_pares_globales` steereado con `sub_gics_label`, `domain/kb/corroboracion.py`,
`filter_rank_competidores` sub-estricto en el tier global, `DiscoverGlobales`, flag
`discover_globales_enabled`, `scripts/descubrir_globales_llm.py`). Gate: ruff 0 (src/ tests/), 522
fast tests.

Hoy ejecutas DT-050 — BASE COLOMBIA LOCAL + STARTIA (el componente LOCAL, `alcance=local`, tiers
2.1.2 regional y 2.1.3 startups). Rama nueva `feature/fase29-dt050` desde develop.

## PROBLEMA / OPORTUNIDAD
Con el eje `alcance`, el tier global ya tiene motor (DT-062). Falta el **local**: hoy los jugadores
regionales se recomputan por web cada corrida (ADR-013 los purga). El usuario aportó activos:
`FuentesEMIS/EmpresasColombia` (~98k empresas colombianas: nombre, sector local, actividad, ingreso,
ciudad, empleados, NIT) y `FuentesExternas/startia_clean.xlsx` (388 startups Medellín).

## RESTRICCIONES (CLAUDE.md TIER 1)
- Sin nombres de modelo en código. domain/ no importa SQLAlchemy/httpx. BD compartida: esquema
  propio, migración idempotente `ensure_*`, NUNCA `down -v`. Provenance + estado candidato/verificado
  (RN-001). Reusa el esquema `sub_gics`/`alcance` de DT-061/061b (esto NO es reingesta de vectores).
- PLAN MODE obligatorio (nuevas tablas/ingesta + mapeo Sector-Local→GICS + dedup por NIT → decisiones).

## DECISIONES YA TOMADAS (memory `project_dt050_fuentes_decisiones`)
- Componente LOCAL (`alcance=local`). `DBCamaraComercio` DESCARTADA.
- **Modelo:** entidad canónica única (dedup por **NIT**) + tabla `entidad_sectores` (entidad_id,
  sector_gics, sub_gics, vertical, fuente) con provenance; multi-sector es feature, no duplicado.
- **startia** `segmento=startup`, sector vía crosswalk `CatalogoVerticalesStartIAGICS.csv`
  (Vertical→nombre grupo GICS→`extract_gics_code`, con la ruta fallback-por-nombre del
  `feedback_extract_gics_code`); trae ETAPA/ULTIMA_RONDA/web para la ficha 2.1.3.
- Startups globales (scaleups/unicornios) PARQUEADAS (sub-tier global futuro, patrón DT-062).

## TAREAS (afinar en Plan Mode)
T1 — Ingesta EmpresasColombia → KB (upsert por NIT, `alcance=local`, sector local→GICS vía
  `ciiu_gics`/crosswalk). Idempotente, script offline (patrón `curar_kb_competidores.py`).
T2 — Ingesta startia (`segmento=startup`, crosswalk vertical→GICS, atributos ETAPA/ronda/web).
T3 — Anclaje del tier local: `list_competidores_by_sector(alcance='local')` alimenta 2.1.2/2.1.3
  (extender el cableado de `generate_n1`, flag/invariante como DT-062).
T4 (stretch) — tabla `entidad_sectores` para membresías multi-sector con provenance.

## PRUEBAS / DONE
Parsers/mapeos puros con fixtures (sin BD). Anclaje local devuelve locales, no diluye el global.
Gate ruff 0 + pytest -m "not slow" verde. 1 commit atómico por tarea. Docs FASE28_HALLAZGOS +
ROADMAP + PROPUESTA + memoria. Merge `--no-ff` tras aprobación. Dejar prompt de la siguiente ventana.

## LECTURAS OBLIGATORIAS
- `docs/architecture/PROPUESTA_BASE_EMPRESAS.md` (diseño completo DT-050) + `PROPUESTA_KNOWLEDGE_BASE.md §1`.
- Código: `data/models/entidad.py` (esquema, `alcance`/`sub_gics`), `data/repositories/entidad_repo.py`
  (upsert por NIT, `list_competidores_by_sector`), `scripts/curar_kb_competidores.py` (patrón siembra),
  `shared/constants/gics_groups.py` (`extract_gics_code`, crosswalk), `domain/use_cases/generate_n1.py`
  (anclaje). `documentos_sectoriales/FuentesEMIS/EmpresasColombia/` y `FuentesExternas/startia_clean.xlsx`.
- memory: `project_dt050_fuentes_decisiones`, `project_fase27_dt062_estado`, `feedback_extract_gics_code`,
  `feedback_modelos_llm`.
