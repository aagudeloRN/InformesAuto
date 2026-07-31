# Fase 26 — Hallazgos y cierre

> Relevancia y granularidad de competidores (DT-061): fija el descubrimiento de Cap 2 (competidores
> irrelevantes / de industria ajena / ruido NER) aguas arriba, en el anclaje del KB, **sin
> reingesta ni re-embeber**. Rama `feature/fase26-dt061` desde `develop` (base `06ce66d`).
> Gate final: **ruff 0 (src/ tests/), 497 fast tests** (464 base + 33 nuevos), 2 skipped.

## §1 — DT-061: relevancia y granularidad de competidores (cerrado 2026-07-31)

### Problema (E2E Alpina 2026-07-30, ver FASE25_HALLAZGOS §1)
Alpina es **lácteos**. El anclaje del KB devolvía competidores de **industria ajena** (Postobón,
Coca-Cola, FEMSA — bebidas; Fedepalma — palma) y **ruido NER** (medios "… Industry News";
fragmentos de métrica OCR "ProfitMargin", "Profit perEmployee"), con **cero pares lácteos reales**.

**Raíz:** el anclaje llamaba `list_competidores_by_sector(g_code="3020")`, que en GICS es el
**industry group** "Alimentos, Bebidas y Tabaco" — demasiado grueso. Todo el sistema clasificaba
solo a ese nivel (25 grupos, 4 díg). El ranking por `n_menciones` premiaba publishers/adyacentes y
la stoplist de `aggregate` no atrapaba medios ni fragmentos de métrica.

### AVANCES (con números)

**T1 — Granularidad de sub-sector (`aef1c82`).**
- Columna `entidades.sub_gics` (sub-código GICS 6 díg): migración idempotente
  `ADD COLUMN IF NOT EXISTS` + índice; `EntidadRow.sub_gics` + upsert con `COALESCE` (no degrada).
- `resolve_sub_gics(descripcion, grupo)` **puro/determinista** (sin modelo, ADR-002): solo refina
  3020 hoy (food `302020` / beverage `302010` / tobacco `302030`); `None` fuera de 3020 o sin señal
  → **invariante** (anclaje a nivel de grupo). Cableado en `generate_n1._fn_cap2`.
- **Sin reingesta:** el sub-código lo cargan solo la empresa analizada (1 clasificación en tiempo de
  informe) y los pares sembrados verificados; los candidatos NER siguen en el grupo.

**T2 — Filtro de relevancia + exclusión de ruido (`915cebc`).**
- `domain/kb/relevance.py` (puro): `es_ruido_competidor` (medios + fragmentos de métrica) +
  `filter_rank_competidores` (excluye ruido; si hay sub-código resuelto **restringe** a la
  sub-actividad/verificados → cae la industria ajena; orden verificado → sub → señal).
- `entidad_repo.list_competidores_by_sector` trae columnas y **delega** en el filtro puro
  (data→domain para un helper sin BD; sin ciclo).
- `aggregate._clasificar_signal` reusa `es_ruido_competidor` → los merges futuros ya no admiten
  medios/métricas.

**T3 — Curación + siembra mínima de pares reales (`59fdb2e`).**
- `shared/data/pares_sectoriales.py`: semilla **mínima** de pares food reales (Colanta, Alquería,
  Nestlé, Danone, Nutresa, Lactalis…) con `sub_gics=302020` y `nombre_normalizado` precalculado con
  la clave de dedup del NER (test lo verifica). Mismo esquema que consumirá la base Colombia
  (DT-050). Alpina omitida (empresa analizada).
- `entidad_repo.descartar_ruido_competidores`: marca `descartado` el ruido (predicado puro),
  idempotente y con guard `estado <> verificado` (RN-001, no degrada).
- `scripts/curar_kb_competidores.py`: orquesta purga + siembra (`verificado` + provenance
  `usuario/curado`), `--dry-run`. Idempotente (upsert dedup por nombre+sector).

### E2E de verificación (anclaje BD real, 2026-07-31)

Medido en el **locus del fix** (la lista anclada), no en el informe completo (18 min) — es
determinista y aísla el efecto. KB real (17 260 entidades):

| Anclaje 3020 | ANTES (pre-curación) | DESPUÉS (post-curación) |
|---|---|---|
| Sub food (302020) | `Noel, Alpina` (2; uno es la analizada) | `Danone, Colombina, Colanta, Alquería, Coolechera, Colácteos, Freskaleche, Parmalat` (**8/8 pares food reales**) |
| Sin sub (grupo) | `Noel, Alpina, Postobón, FEMSA, Coca-Cola, Fedepalma, Sports Drinks, Nutresa` (**5/8 industria ajena**) | `Danone, Colombina, Noel, Alpina, Colanta, Alquería, Coolechera, Colácteos` (**0 ajenos** en top-8) |

- **Ruido descartado:** 247 entidades (media/métricas: "financial times", "wall street journal",
  "revenue forecast", "fortune business insights"…). **Pares sembrados:** 18.
- **Industria ajena en el anclaje food: 5/8 → 0/8.** **Pares reales: 0 → 8.**
- **Idempotencia:** re-purga (dry-run) marca **0**; el upsert de siembra no duplica (ON CONFLICT).

### RETOS / lecciones
- **La granularidad no cabía en la taxonomía existente** (solo 25 industry groups). Se resolvió con
  un sub-código que **solo** cargan la empresa analizada y los pares sembrados → granularidad real
  sin re-clasificar el corpus ni reingerir (eso habría sido DT-060).
- **`data→domain` para un helper puro** es la dirección correcta de clean-architecture (data depende
  del core), no una violación: `relevance.py` no importa nada de `ic.*`.
- **El KB había evolucionado** desde el informe original (ya no tenía "… Industry News"), pero
  seguía con industria ajena (Postobón/FEMSA/Coca-Cola/Fedepalma) en el top del grupo — el fix la
  elimina del anclaje food.
- **El loop DT-059 seguía sin poder fabricar evidencia**: el fix es aguas arriba (relevancia), no en
  el loop.

### RECOMENDACIONES (siguiente ventana) — reordenadas tras DT-061b

Con el eje `alcance`, cada tier del informe tiene su fuente:

1. **DT-062 (sucesor recomendado) — descubrimiento LLM de competidores globales.** El LLM recomienda
   actores globales representativos del sector (`candidato`/`fuente=llm`), **corroborados por web
   dirigida** (Tavily, no corpus EMIS que está sesgado a lo local), sembrados `alcance=global`. Es el
   **motor principal** del componente de clase mundial (2.1.1); la semilla curada de DT-061b es el
   cold-start. Mejora recall/representatividad (p. ej. que Nestlé no quede fuera del top-8).
2. **DT-050 — base Colombia (98k):** `FuentesEMIS/EmpresasColombia` → tabla `empresas_co` (upsert por
   NIT, sector→GICS vía `ciiu_gics`), fuente `verificado` `alcance=local` del componente **regional**
   (2.1.2). Reusa el esquema `sub_gics`/`alcance`; no es reingesta.
3. **DT-060 — reingesta paralela A/B:** mejor extracción (tablas/estructura EMIS) sube el techo de
   evidencia (fichas, Cap 4 vacíos); paralelizable como se vio en corridas previas.

### DT-061b — eje `alcance` global/local (refinamiento, 2026-07-31, commit `f6ab4d6`)

Decisión del usuario tras revisar el resultado: **este componente es para competidores de CLASE
MUNDIAL**; los jugadores locales grandes (Colanta, Alquería…) son **otro componente** (2.1.2 /
DT-050). DT-061 mezclaba ambos bajo `verificado`, así que el anclaje mostraba lácteas locales en vez
de actores globales. Se separa el eje **alcance** del eje sub-actividad:

- Columna `entidades.alcance` (`global`/`local`; migración idempotente); `filter_rank_competidores`
  gana **filtro duro por alcance** (la lista de clase mundial no se diluye con locales);
  `generate_n1._fn_cap2` ancla con `alcance=global`.
- Semilla re-scopeada: globales (Nestlé, Danone, Lactalis, FrieslandCampina, Fonterra, Arla, Yili,
  Mengniu, Saputo, Savencia, Grupo Lala, Parmalat, **Nutresa** como frontera global) vs. locales
  (Colanta, Alquería, Coolechera, Colácteos, Freskaleche, Gloria, Colombina, Team Foods, Casa Luker,
  Ramo). **Global/local es un juicio de curación** ("¿es referencia mundial?"), no país de sede.
- **E2E anclaje world-class:** `[Saputo, Savencia, Grupo Lala, Danone, Yili, Mengniu, Parmalat,
  Nutresa]` — **8/8 globales, 0 locales, 0 ajenos**; el componente local queda aparte. Re-run
  idempotente. Gate ruff 0, **501 fast tests**.
- **Refinamiento pendiente (→ DT-062):** el `limit=8` con orden por evidencia deja algunos globales
  icónicos (Nestlé) fuera del top-8; el motor LLM de DT-062 mejora recall/representatividad.
- **Corpus sesgado a lo local:** para el componente global la corroboración debe ser vía **web**
  (Tavily), no vía corpus EMIS (que no menciona a Yili/Fonterra) → clave para DT-062.

### Verificación
- `uv run ruff check src/ tests/` → 0. `uv run pytest -m "not slow" -q` → **501 passed**, 2 skipped.
- Invariante: sin sub-código (sector no resuelto) → anclaje a nivel de grupo, solo ruido excluido;
  sin `alcance` pedido → no se filtra por alcance (otros componentes intactos).
- Migración `ADD COLUMN IF NOT EXISTS` (sub_gics, alcance) + índice, idempotente. Sin tocar
  vectores, sin `down -v`.

---

## §2 — Prompt de arranque de la siguiente ventana (DT-062 — descubrimiento LLM de competidores globales)

```
## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto): informes de
inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas). DT-061 +
DT-061b (relevancia, granularidad y alcance de competidores) están CERRADOS y MERGEADOS a develop
(rama feature/fase26-dt061 + feature/fase26-dt061b-alcance): sub-código GICS (sub_gics +
resolve_sub_gics), filtro de relevancia puro (domain/kb/relevance.py: es_ruido_competidor +
filter_rank_competidores con sub_gics y alcance), eje alcance global/local (columna alcance), curación/
siembra (scripts/curar_kb_competidores.py + shared/data/pares_sectoriales.py). E2E: anclaje
world-class de Alpina 8/8 globales, 0 locales, 0 ajenos. Gate: ruff 0 (src/ tests/), 501 fast tests.

Hoy ejecutas DT-062 — DESCUBRIMIENTO LLM DE COMPETIDORES GLOBALES (motor principal del componente de
clase mundial, 2.1.1). Rama nueva feature/fase27-dt062 desde develop.

## PROBLEMA / OPORTUNIDAD
La semilla de globales de DT-061b es un cold-start MÍNIMO y curado a mano; no escala por sector y el
limit=8 con orden por evidencia deja fuera globales icónicos (Nestlé). El LLM tiene alto recall de
actores globales famosos (bajo riesgo de alucinar el NOMBRE), y el corpus EMIS está sesgado a lo
local (no menciona Yili/Fonterra). Idea: el LLM RECOMIENDA actores globales representativos del
sector → se siembran como candidato/fuente=llm → la búsqueda WEB dirigida (Tavily) los corrobora →
solo los corroborados se citan (RN-001/TIER 4). El nombre lo aporta el LLM; los atributos, la
evidencia.

## RESTRICCIONES (CLAUDE.md TIER 1)
- Sin nombres de modelo en código (gateway/config, ADR-002). domain/ no importa SQLAlchemy/httpx/
  Streamlit; librería externa por wrapper en infrastructure/. BD compartida: esquema propio, migración
  idempotente ensure_*, NUNCA down -v. RN-001: candidato (llm) vs verificado (corroborado); provenance
  fuente=llm; NUNCA citar un nombre sin corroboración de evidencia.
- Corroboración vía WEB, no corpus (el corpus es local). PLAN MODE obligatorio (cadena LCEL nueva +
  gate de corroboración + siembra alcance=global → decisiones de diseño).

## TAREAS (afinar en Plan Mode)
T1 — Cadena LCEL chain_02c_pares_globales(sector_gics, sub-actividad) → array JSON de actores
  globales representativos (patrón chain_02b_entidades: parser puro, cota, dedup). Modelo inyectado.
T2 — Gate de corroboración: cada candidato del LLM dispara búsqueda web dirigida; si hay evidencia
  suficiente (umbral existente) → sembrar verificado/alcance=global; si no → queda candidato/fuente=llm
  (no citable). Reusar el patrón identificar→enriquecer de generate_benchmarking.
T3 — Cablear como fuente del anclaje world-class (complementa la semilla curada; el LLM lidera el
  recall, la semilla es fallback/cold-start). Flag para activarlo; invariante OFF = comportamiento
  DT-061b actual.
T4 (stretch) — Persistir alcance=global desde el LLM en el KB con provenance, idempotente.

## PRUEBAS POR TAREA (gate = ruff 0 + pytest -m "not slow")
- Parser puro de la cadena (fixtures; no fabrica, dedup, cota). Sin BD ni modelo real.
- Gate de corroboración: candidato con evidencia → verificado; sin evidencia → candidato (no citable).
- Invariante: flag OFF → anclaje = DT-061b (solo semilla curada). Sin romper sub_gics/alcance/ruido.

## DONE
1. El componente de clase mundial recibe globales recomendados por LLM y corroborados por web.
2. Ningún nombre se cita sin evidencia (RN-001/TIER 4). 3. Gate verde. 4. 1 commit atómico por tarea.
5. Docs/roadmap/memoria (DT-062). 6. Decidir siguiente (DT-050 base Colombia local, o DT-060 reingesta).

## LECTURAS OBLIGATORIAS
- docs/decisions/FASE26_HALLAZGOS.md §1/§1b (este cierre + eje alcance) +
  docs/architecture/PROPUESTA_KNOWLEDGE_BASE.md §1.4.
- Código: domain/chains/chain_02b_entidades.py (patrón de cadena+parser), domain/use_cases/
  generate_benchmarking.py (_identificar_entidades/_buscar_por_entidad), domain/kb/relevance.py
  (filtro por alcance), data/repositories/entidad_repo.py (upsert alcance, list_competidores_by_sector),
  shared/data/pares_sectoriales.py (semilla curada), scripts/curar_kb_competidores.py (patrón).
- memory: project_fase26_dt061_estado, project_fase24_dt056_estado, feedback_modelos_llm.

## CIERRE DOCUMENTADO
FASE27_HALLAZGOS.md con AVANCES/RETOS/RECOMENDACIONES + números (nº globales recomendados vs
corroborados por sector; cobertura del componente world-class). Sincronizar ROADMAP + PROPUESTA §1.4.
Merge a develop --no-ff tras aprobación. Dejar prompt de la siguiente ventana (DT-050 base Colombia)
con esta MISMA estructura.
```
