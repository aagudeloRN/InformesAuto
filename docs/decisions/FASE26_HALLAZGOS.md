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

### RECOMENDACIONES (siguiente ventana)
1. **DT-050 — base Colombia (98k):** indexar `FuentesEMIS/EmpresasColombia` (10 xlsx) como tabla
   relacional `empresas_co` (upsert por NIT, sector→GICS vía `ciiu_gics`) → fuente `verificado` de
   pares **regionales** (arregla también fichas 2.1.2). Reusa el esquema `sub_gics`; no es reingesta.
2. **DT-062 — semilla LLM gated:** el LLM propone pares **globales** (`candidato`/`fuente=llm`),
   citables solo si la búsqueda dirigida los corrobora (RN-001/TIER 4). Recall global sin alucinar.
3. **DT-060 — reingesta paralela A/B:** mejor extracción (tablas/estructura EMIS) sube el techo de
   evidencia (fichas 2.1.2/2.1.3, Cap 4 vacíos); paralelizable como se vio en corridas previas.

### Verificación
- `uv run ruff check src/ tests/` → 0. `uv run pytest -m "not slow" -q` → **497 passed**, 2 skipped.
- Invariante: sin sub-código (sector no resuelto) → anclaje a nivel de grupo, solo ruido excluido.
- Migración `ADD COLUMN IF NOT EXISTS` + índice, idempotente. Sin tocar vectores, sin `down -v`.

---

## §2 — Prompt de arranque de la siguiente ventana (DT-050 — base Colombia)

```
## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto): informes de
inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas). DT-061
(relevancia y granularidad de competidores) está CERRADO y MERGEADO a develop (rama
feature/fase26-dt061): sub-código GICS (sub_gics + resolve_sub_gics), filtro de relevancia puro
(domain/kb/relevance.py: es_ruido_competidor + filter_rank_competidores), curación/siembra
(scripts/curar_kb_competidores.py + shared/data/pares_sectoriales.py). E2E: anclaje food de Alpina
0/8 ajenos, 8/8 pares reales. Gate: ruff 0 (src/ tests/), 497 fast tests, 2 skipped.

Hoy ejecutas DT-050 — BASE DE EMPRESAS COLOMBIA (fuente verificada regional para el anclaje).
Rama nueva feature/fase27-dt050 desde develop.

## PROBLEMA / OPORTUNIDAD
La semilla de pares de DT-061 es MÍNIMA y global. Hay ~98k empresas colombianas con sector en
documentos_sectoriales/FuentesEMIS/EmpresasColombia (10 xlsx). Indexarlas da pares REGIONALES
verificados (arregla fichas 2.1.2 Regionales) y una base viva que las corridas enriquecen con lo
hallado en web. NO es reingesta ni embeddings: es una TABLA RELACIONAL en el esquema propio.

## RESTRICCIONES (CLAUDE.md TIER 1)
- Sin nombres de modelo en código. domain/ no importa SQLAlchemy/httpx/Streamlit; librería externa
  por wrapper en infrastructure/. BD compartida: esquema propio, migración idempotente ensure_*,
  NUNCA down -v, datos en bind mount. RN-001: verificado (registro) vs candidato (web), provenance.
- PLAN MODE obligatorio (nueva tabla + mapping sector→GICS + wiring al anclaje → decisiones).

## TAREAS (afinar en Plan Mode)
T1 — Leer las columnas reales de los xlsx (NIT, nombre, sector CIIU/GICS/texto, ciudad, tamaño).
  Definir tabla empresas_co en el esquema propio (upsert idempotente por NIT).
T2 — Mapear sector del Excel → GICS (grupo) y, si es CIIU, → sub-actividad (reusar ciiu_gics.py).
T3 — Script de indexación (batch, idempotente, --dry-run) de las ~98k. NO embeddings.
T4 — Cablear empresas_co como fuente verificada del anclaje (list_competidores_by_sector /
  siembra) por sector+sub_gics+geografía, reusando el filtro de relevancia de DT-061.
T5 (stretch) — Enriquecimiento: las búsquedas web de la corrida actualizan atributos (candidato).

## PRUEBAS POR TAREA (gate = ruff 0 + pytest -m "not slow")
- Parsing/mapping puros (sin BD): fixture de filas → EntidadRow/empresas_co con GICS+sub correctos.
- Idempotencia del upsert por NIT (fake session / re-run = 0 nuevas).
- Anclaje: dado empresas_co sembrado, pares regionales del sector real; invariante sin sector.

## DONE
1. empresas_co indexada e idempotente. 2. Anclaje usa pares regionales verificados. 3. Gate verde.
4. 1 commit atómico por tarea. 5. Docs/roadmap/memoria (DT-050). 6. Decidir siguiente (DT-062 LLM
   gated o DT-060 reingesta).

## LECTURAS OBLIGATORIAS
- docs/decisions/FASE26_HALLAZGOS.md (este cierre) + docs/architecture/PROPUESTA_BASE_EMPRESAS.md.
- Código: data/repositories/entidad_repo.py (upsert, list_competidores_by_sector, sub_gics),
  domain/kb/relevance.py, shared/data/pares_sectoriales.py, shared/constants/ciiu_gics.py +
  gics_groups.py (resolve_sub_gics), scripts/curar_kb_competidores.py (patrón).
- memory: project_fase26_dt061_estado, project_fase24_dt056_estado, feedback_extract_gics_code.

## CIERRE DOCUMENTADO
FASE27_HALLAZGOS.md con AVANCES/RETOS/RECOMENDACIONES + números (nº empresas indexadas, cobertura
por sector, pares regionales añadidos al anclaje). Sincronizar ROADMAP + PROPUESTA. Merge a develop
--no-ff tras aprobación. Dejar prompt de la siguiente ventana con esta MISMA estructura.
```
