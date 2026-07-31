# Fase 28 — Hallazgos y cierre

> Reuso de globales por **sub-actividad**, no por grupo (DT-062b). DT-062 descubría globales por
> LLM+web y los reusaba entre corridas, pero el reuso era **por grupo GICS (3020)**: una empresa de
> tabaco (302030) o bebidas (302010) veía los globales de lácteos/food (302020). DT-062b lo corrige
> con tres piezas: (1) steering del prompt con la **etiqueta legible** de la sub-actividad, (2)
> **filtro sub-estricto** en el tier de clase mundial (sin puente `verificado`), (3) el guard de
> coste pasa a contar **por sub** → el descubrimiento se dispara una vez por sub-actividad. Rama
> `feature/fase28-dt062b` desde `develop` (base `45ba54d`). Gate: **ruff 0 (src/ tests/), 522 fast
> tests** (518 base + 4 nuevos), 2 skipped. Sin migración, sin reingesta, sin `down -v`.

## §1 — DT-062b: reuso por sub-actividad (cerrado 2026-07-31)

### Problema (FASE27_HALLAZGOS § "Limitación detectada → DT-062b")
El reuso de DT-062 era **por grupo, no por sub-actividad**. Dos causas raíz, ambas verificadas
empíricamente (food/beverage/tobacco devolvían la MISMA lista):

1. **Steering pobre del prompt.** `DiscoverGlobales.discover` pasaba `sub_actividad = sub_gics or
   "general"` — el **código crudo** `302020`. El LLM no lo interpreta como food/lácteos; el recall
   se dispersa al grupo entero (bebidas: Heineken/AB InBev; cárnicos: JBS/Tyson).
2. **`verificado` puenteaba el filtro de sub.** En `filter_rank_competidores`, la cláusula
   `r.verificado or r.sub_gics == sub_gics` dejaba pasar cualquier `verificado` sin mirar su sub.
   Como los globales de DT-062 se siembran `verificado`, tabaco veía los food.

### Chesterton's Fence (regla cerrada de DT-061 que se tocó)
El puente `verificado OR sub` se introdujo en DT-061/T2 para que **pares curados SIN `sub_gics` tag**
igualmente aparezcan (curación honesta). En la práctica (DT-061b) toda la semilla de
`pares_sectoriales.py` **sí** trae `sub_gics`, así que el puente hoy solo es red de seguridad del
path **grupo/local**. **Decisión:** conservarlo intacto en el path sin `alcance` (compat DT-061) y
**eliminarlo solo en el tier de clase mundial** (cuando se pide `alcance`). Los 6 tests DT-061 no
cambian (sus `verificado` traen el sub correcto).

### AVANCES (con números)

**T1 — Etiqueta legible de sub-actividad al prompt (`3d899ac`).**
- `shared/constants/gics_groups.py`: mapa puro `SUB_GICS_LABELS` (`302020`→"alimentos procesados y
  lácteos", `302010`→"bebidas", `302030`→"tabaco") + helper `sub_gics_label(sub_code)` (None o
  desconocido → "general"). `DiscoverGlobales.discover` lo usa para `sub_actividad`. 2 tests puros.

**T2 — Filtro sub-estricto para el tier de clase mundial (`7fd1f59`).**
- `domain/kb/relevance.py::filter_rank_competidores`: cuando se pide `alcance`, la restricción por
  sub es **estricta** (`r.sub_gics == sub_gics`), sin puente `verificado` ni fallback a grupo. El
  ancla puede quedar vacía (mejor que sub ajena: el guard dispara el descubrimiento de esa sub). El
  path sin `alcance` conserva puente + fallback (invariante DT-061). 2 tests nuevos: tabaco/302030
  con solo globales food/302020 `verificado`/`global` → `[]`; invariante food intacta.

**T3 — Guard + siembra por sub (`24b33f7`, solo comentario).**
- El guard (`generate_n1._descubrir_globales`) y la query del ancla (`_fn_cap2`) ya pasaban
  `sub_gics=sub_code`; con el filtro estricto de T2 la cuenta de "KB caliente ≥8" es ahora **por
  sub** → el descubrimiento se dispara una vez por sub-actividad, no por grupo. El tag
  `sub_gics=sub_code` al sembrar es veraz gracias al steering de T1. Sin cambio funcional.

### T4 — Verificación E2E por sub (real, luego purgada)

Snapshot → siembra real por sub (LLM + web Tavily) → query de aislamiento → re-run idempotente →
**restore exacto** al baseline (script temporal `_verify_dt062b.py`, no commiteado, con purga
snapshot/restore para no tocar el KB compartido — TIER 1). Números:

**Steering por sub (recall del LLM, disjunto por sub-actividad):**
- `food` (302020) → 9 recomendados / 9 corroborados: Nestlé, Danone, Lactalis, Yili, Mengniu,
  Kraft Heinz, Unilever, Saputo, Savencia, Grupo Lala, Parmalat, Grupo Nutresa…
- `beverage` (302010) → 12/12: The Coca-Cola Company, PepsiCo, Anheuser-Busch InBev, Heineken N.V.,
  Diageo, Carlsberg, Asahi, Kirin, Pernod Ricard, Constellation Brands, Molson Coors, Suntory.
- `tobacco` (302030) → 7 recomendados / 6 corroborados: Philip Morris International, Japan Tobacco
  International, Imperial Brands, Altria Group, Swedish Match, China National Tobacco. (British
  American Tobacco cayó a `hits=1` en la corroboración → `candidato`, no entra al ancla.)

**Aislamiento (`list_competidores_by_sector(3020, sub, alcance=global)` sobre lo sembrado):**
- `tabaco ∩ food = ∅`, `bebidas ∩ food = ∅`, `bebidas ∩ tabaco = ∅`. **Tabaco NO ve lácteos.** Cada
  sub devuelve su propia lista.

**Idempotencia (re-run, KB caliente):** `food` (15 globales ≥8) y `beverage` (12 ≥8) → el guard
**salta** (no re-descubre); `tobacco` (6 <8) dispararía otra vez (artefacto de corroboración de BAT,
no un bug de sub). El guard es **por sub**: cada sub-actividad decide de forma independiente.

**Restore:** 3020 vuelve a **390 entidades / 392 atributos** (idéntico al baseline) y **0 atributos
`fuente=llm`** en todo el KB → la verificación no dejó residuo (como en DT-062).

### RETOS / lecciones
- **La regla cerrada de DT-061 se tocó con bisturí, no con hacha.** En vez de borrar el puente
  `verificado` (que rompería el path grupo/local y los tests DT-061), se bifurcó por presencia de
  `alcance`. El tier de clase mundial es el único que exige sub-estricto.
- **El aislamiento se garantiza en dos capas.** Aunque el KB tuviera globales mal etiquetados, el
  filtro sub-estricto de T2 (capa de consulta) ya impide que tabaco vea food. T1 (capa de siembra)
  asegura además que lo sembrado tenga el sub correcto. Defensa en profundidad.
- **Ancla vacía es una feature, no un bug.** En el tier global, vacío significa "esta sub aún no se
  descubrió" → el guard dispara su descubrimiento. Preferible a rellenar con sub ajena.

### RECOMENDACIONES (siguiente ventana)
1. **DT-050 — base Colombia local + startia.** Componente LOCAL (`alcance=local`): `EmpresasColombia`
   (~98k, upsert por NIT) + `startia_clean.xlsx` (388 startups Medellín). Alimenta 2.1.2 (regional)
   y 2.1.3 (startups). Ver `PROMPT_SIGUIENTE_DT050.md` y memory `project_dt050_fuentes_decisiones`.
2. **Precalentar el KB de los 25 sectores** por sub-actividad (script offline, una corrida por
   sub-actividad relevante) ahora que el steering es fino.
3. **DT-060 — reingesta paralela A/B:** sube el techo de evidencia (fichas, Cap 4 vacíos).

### Verificación
- `uv run ruff check src/ tests/` → 0. `uv run pytest -m "not slow" -q` → **522 passed**, 2 skipped.
- Invariante: `discover_globales_enabled` default **False** → anclaje = DT-061b (solo semilla
  curada); path sin `alcance` sin cambios (tests DT-061 intactos).
- Sin migración nueva (reusa `sub_gics`/`alcance`/`FUENTE_LLM`); sin reingesta, sin `down -v`.
