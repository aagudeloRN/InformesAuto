# Fase 27 — Hallazgos y cierre

> Descubrimiento LLM de competidores globales corroborado por web (DT-062): el **motor de recall**
> del componente de clase mundial (2.1.1). El LLM recomienda actores globales representativos del
> sector (nombres); la búsqueda web dirigida (Tavily) los corrobora; solo los corroborados se
> siembran `verificado`/`alcance=global` con provenance `fuente=llm` (RN-001/TIER 4). La semilla
> curada de DT-061b pasa a ser el cold-start/fallback. Rama `feature/fase27-dt062` desde `develop`
> (base `3eb48ca`). Gate final: **ruff 0 (src/ tests/), 516 fast tests** (501 base + 15 nuevos),
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

### E2E de verificación (dry-run en vivo, 2026-07-31, sector 3020)

`descubrir_globales_llm.py --sector 3020 --sub 302020 --dry-run` (LLM vía OpenRouter, corroboración
Tavily `advanced`, **sin escribir en BD**):

| Métrica | Valor |
|---|---|
| Globales **recomendados** por el LLM | **12** |
| **Corroborados** por web (≥2 fuentes) | **12 (100%)** |
| No corroborados | **0** |
| Rango de `hits` de corroboración | 3–5 por candidato |

Recomendados: **Nestlé, PepsiCo, Unilever, Kraft Heinz, Danone, Mars, Mondelez, JBS, Tyson Foods,
Cargill, Anheuser-Busch InBev, Heineken.** De ellos, **10 son nuevos** frente a la semilla curada de
3020 (solo Nestlé y Danone se solapan) → el pool de anclaje del sector crece de **14 curados → ~24
globales distintos**, y **Nestlé** (que DT-061b señaló fuera del top-8) entra corroborado.
**Cobertura del componente world-class:** de cold-start manual mono-sector a motor de recall
general por sector.

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
- `uv run ruff check src/ tests/` → 0. `uv run pytest -m "not slow" -q` → **516 passed**, 2 skipped.
- Invariante: `discover_globales_enabled` default **False** → anclaje = DT-061b (solo semilla curada);
  sin romper `sub_gics`/`alcance`/ruido. No corroborado nunca recibe `alcance=global` (RN-001).
- Sin migración nueva (reusa `sub_gics`/`alcance`/`FUENTE_LLM`); sin reingesta, sin `down -v`.
