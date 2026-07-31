# Fase 27 — Hallazgos y cierre

> Descubrimiento LLM de competidores globales corroborado por web (DT-062): el **motor de recall**
> del componente de clase mundial (2.1.1). El LLM recomienda actores globales representativos del
> sector (nombres); la búsqueda web dirigida (Tavily) los corrobora; solo los corroborados se
> siembran `verificado`/`alcance=global` con provenance `fuente=llm` (RN-001/TIER 4). La semilla
> curada de DT-061b pasa a ser el cold-start/fallback. Rama `feature/fase27-dt062` desde `develop`
> (base `3eb48ca`). Gate final: **ruff 0 (src/ tests/), 518 fast tests** (501 base + 17 nuevos),
> 2 skipped. Sin reingesta, sin re-embeber, sin `down -v`.

## §1 — DT-062: descubrimiento LLM de globales (cerrado 2026-07-31)

### Problema (FASE26_HALLAZGOS §1b)
El anclaje de clase mundial (2.1.1) se poblaba **solo** con la semilla curada a mano de DT-061b
(`shared/data/pares_sectoriales.py`): un **cold-start mínimo**, único sector 3020, que (a) no escala
a los 25 sectores y (b) con `limit=8` ordenado por evidencia deja globales icónicos fuera del top-8
(p. ej. Nestlé). El corpus EMIS está **sesgado a lo local** (no menciona Yili/Fonterra) → no sirve
para descubrir globales. Oportunidad: el LLM tiene **alto recall** de globales famosos y **bajo
riesgo de alucinar el nombre**; la web (no el corpus) los corrobora.

### AVANCES (con números)

**T1 — Cadena LCEL `chain_02c_pares_globales` (`f7fb049`).**
- `domain/chains/chain_02c_pares_globales.py`, espejo de `chain_02b_entidades`: `build_chain_pares_globales`
  (modelo inyectado, ADR-002) + `parse_pares_globales` **puro** (fences, dedup casefold, cota
  `MAX_GLOBALES=12`, `[]` si no hay array — RN-001: solo depura, no fabrica). 7 tests.

**T2 — Gate de corroboración web + `DiscoverGlobales` (`dbe61ad`).**
- `domain/kb/corroboracion.py` **puro**: `_fold` (minúsculas + sin acentos), `contar_corroboracion`
  (nº de resultados web cuyo contenido menciona el nombre) y `es_corroborado(hits, min)`. No importa
  `normalize_entity` de `infrastructure/` (no cruza capas).
- `domain/use_cases/discover_globales.py`: por cada candidato, búsqueda web dirigida → cuenta
  menciones. **Corroborado** (≥`min_corrob`) → ingiere evidencia + siembra `verificado`/`alcance=global`;
  **no corroborado** → siembra `candidato`/`fuente=llm` **sin `alcance=global`** (nunca entra a 2.1.1)
  y **sin ingerir** (sin evidencia). El caso de uso **no ve BD**: la persistencia se inyecta como
  callback. Constante `FUENTE_LLM`. 7 tests (mocks).

**T3 — Cableado tras flag + config + script offline (`d08f1f0`).**
- `config.py`: `discover_globales_enabled` (default **OFF** = invariante DT-061b) +
  `discover_globales_min_corrob=2`.
- `generate_n1._fn_cap2`: ejecuta el descubrimiento **antes** del anclaje solo si el flag está ON;
  **guard de coste** (no re-descubre si el KB ya tiene ≥8 globales del sector — KB caliente); envuelto
  en try/except best-effort (nunca rompe la corrida). El anclaje `alcance=global` devuelve entonces
  semilla curada **+** globales LLM corroborados.
- `scripts/descubrir_globales_llm.py`: reutiliza `DiscoverGlobales` para precalentar el KB por sector
  sin generar informe (`--sector`, `--sub`, `--dry-run` inerte). 1 test invariante (default OFF).

**T4 (plegado en T2/T3).** La persistencia idempotente de `alcance=global`/`fuente=llm` **es** el
`seed_repo_fn` corroborado (upsert `no degrada` verificado; atributo con provenance `FUENTE_LLM`).

### E2E de verificación (en vivo, 2026-07-31, sector 3020)

Tres corridas de `descubrir_globales_llm.py --sector 3020 --sub 302020` (LLM vía OpenRouter,
corroboración Tavily `advanced`):

| Corrida | Recomendados | Corroborados (≥2) | Nota |
|---|---|---|---|
| Dry-run (no persiste) | 12 | 12 (100%) | Nombres limpios ("JBS", "Tyson Foods") |
| **Siembra real #1** | 12 | **6** | Bug: el LLM emitió sufijos ("JBS S.A.", "Tyson Foods, Inc.") → falso negativo |
| **Siembra real #2 (post-fix)** | 12 | **12 (100%)** | Match por núcleo; "Molson Coors Beverage Company", "Mondelez International" corroboran |

**Hallazgo/fix (bug que el E2E reveló):** `contar_corroboracion` buscaba el nombre **literal** como
substring; cuando el LLM añade la forma legal ("JBS S.A."), la prosa web (que dice "JBS") no la
contiene → **falso negativo** (JBS, global obvio, quedó `hits=0` y fuera del ancla). **Fix**
(`domain/kb/corroboracion.py`): el match usa el **núcleo** del nombre (folded, sin puntuación, sin
artículo inicial ni sufijos societarios) con límite de palabra. 3 tests de regresión. Es la razón por
la que se decidió **sembrar de verdad** en el cierre (el dry-run ocultaba el bug por azar del LLM).

**Persistencia + reuso verificados (post-fix):** el KB quedó con **26 globales verificados** para 3020
(14 curados DT-061b + 12 LLM, menos solapes). La consulta del ancla —lo que un informe futuro lee
**sin re-descubrir** (query pura a BD)— devuelve top-8 mezclando LLM (PepsiCo, Danone, Kraft Heinz,
Heineken, Tyson) + semilla curada (Saputo, Savencia, Grupo Lala): el motor LLM y el cold-start
coexisten. **Nestlé** (fuera del top-8 en DT-061b) ahora corrobora y entra. **Cobertura del componente
world-class:** de cold-start manual mono-sector a motor de recall general, persistido y reusable.

### Persistencia y reuso entre corridas (diseño)

El **nombre** (la parte cara: recall del LLM + corroboración web) se guarda **durablemente** para
reusarlo en informes futuros del mismo sector; la **evidencia** sigue la política ADR-013 existente:

- **Entidad en el KB (ancla) → durable, cross-run.** Los globales corroborados se persisten en la
  tabla `entidades` vía `upsert_entidad` (sesión propia, commit inmediato, `verificado`/`alcance=global`
  + atributo `origen`/`FUENTE_LLM`). **No** los toca ADR-013 (que solo purga vectores web). Informes
  futuros del sector los reusan por `list_competidores_by_sector(alcance='global')`.
- **Guard de coste = mecanismo de reuso.** `generate_n1._fn_cap2` **solo descubre si el KB tiene <8
  globales del sector**; una vez sembrado, las siguientes corridas **saltan el LLM+web** y reusan el
  KB. Es decir: se descubre **una vez por sector**, no en cada corrida.
- **Evidencia web de corroboración → por-corrida (ADR-013).** El `store.ingest` de los corroborados
  estampa `session_id`; al ensamblar, lo **citado** se promueve durable y lo **no citado** se purga.
  El ancla persiste igual, y la corrida siguiente re-recupera evidencia por la búsqueda dirigida (los
  nombres del KB lideran esa búsqueda, DT-056). *Posible mejora futura:* exceptuar de la purga la
  evidencia de corroboración de un global verificado (hoy fuera de alcance).
- **`--dry-run` NO persiste** (usa un store inerte y omite el upsert): sirve para medir
  recomendados/corroborados sin escribir. La siembra real del cierre (arriba) sí persistió 3020.

### RETOS / lecciones
- **El sub-código numérico no steerea el prompt.** Se pasó `sub_actividad="302020"` como código
  crudo; el prompt recibió el nombre del **grupo** completo (3020 = "alimentos, bebidas y tabaco"),
  así que el recall incluyó bebidas (Heineken, AB InBev) y cárnicos (JBS, Tyson), no solo lácteos/food
  puro. Para una láctea (Alpina) el ideal sería food/dairy. **Recomendación:** pasar una **etiqueta
  legible** de la sub-actividad (mapa sub-código → nombre) al prompt, no el código.
- **Con nombres famosos el gate es permisivo** (12/12 corroboran fácil). Su valor real es filtrar
  candidatos oscuros/alucinados (aquí no hubo ninguno); el umbral ≥2 evita el falso-negativo en
  globales reales. Conviene medirlo en un sector menos icónico.
- **Corroboración por web, no por corpus** (confirmado): el corpus EMIS no menciona estos globales;
  Tavily sí. Alinea con la decisión de DT-061b.
- **Idempotencia y capas:** el caso de uso permanece en `domain/` sin ver BD (callback inyectado);
  `data→domain` para el gate puro (como en DT-061). El upsert existente no degrada `verificado`.

### RECOMENDACIONES (siguiente ventana)
1. **DT-050 (sucesor recomendado) — base Colombia local + startia.** Componente LOCAL
   (`alcance=local`): `EmpresasColombia` (~98k, upsert por NIT) + `startia_clean.xlsx` (388 startups
   Medellín, `segmento=startup`, sector vía crosswalk). Alimenta 2.1.2 (regional) y 2.1.3 (startups).
   Ver memory `project_dt050_fuentes_decisiones`.
2. **Refinamiento DT-062:** etiqueta legible de sub-actividad en el prompt (food vs beverage vs
   tobacco) para recall más fino; corrida por-sector para precalentar el KB de los 25 sectores.
3. **DT-060 — reingesta paralela A/B:** sube el techo de evidencia (fichas, Cap 4 vacíos).

### Verificación
- `uv run ruff check src/ tests/` → 0. `uv run pytest -m "not slow" -q` → **518 passed**, 2 skipped.
- Invariante: `discover_globales_enabled` default **False** → anclaje = DT-061b (solo semilla curada);
  sin romper `sub_gics`/`alcance`/ruido. No corroborado nunca recibe `alcance=global` (RN-001).
- Sin migración nueva (reusa `sub_gics`/`alcance`/`FUENTE_LLM`); sin reingesta, sin `down -v`.
