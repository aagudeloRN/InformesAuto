# DT-UI04b — Tier local (2.1.2/2.1.3) vacío pese a datos presentes — HALLAZGOS

> Rama `develop`. Sesión 2026-08-06. Continúa DT-UI04 (bugs E2E ERCO del 2026-08-05).
> Estado: **fix de código CERRADO + validado contra BD real**; validación E2E en `.docx` en curso.

## TL;DR

El tier local de la sección 2.1 salía **vacío** en el `.docx`. La causa **NO** era el repo, ni el
JOIN, ni `g_code`, ni ausencia de datos (todas hipótesis previas, refutadas con datos). La causa raíz
fue **de configuración**: los flags `ANCLAJE_LOCAL_ENABLED`, `SECCION21_DETERMINISTA_ENABLED` y
`DISCOVER_GLOBALES_ENABLED` **no estaban en `.env`** → default `False` → el guard
`if s.anclaje_local_enabled and g_code:` (`generate_n1.py`) cortaba todo el anclaje local.

Al habilitarlos apareció un **segundo problema, más profundo**: para ERCO, clasificada coloquialmente
como **Energía (GICS 1010)**, el tier local se llenaba con pares **irrelevantes** (minería,
construcción, lubricantes), porque la data energética curada (EPM, Celsia, Isagen) fue sembrada bajo
**Servicios públicos / Utilities (GICS 5510)**. Fix: **anclaje local multi-sector** (grupo del LLM ∪
grupo canónico del CIIU), con re-rank por solape de producto y dedup por nombre.

## Diagnóstico (proceso ordenado por sospecha, refutando hipótesis)

Reproducción aislada contra la BD real (`EntidadRepository` + BD compartida, esquema `informes_ic`):

| Sospecha (heredada de DT-UI04b 2026-08-05) | Verificación | Veredicto |
|---|---|---|
| JOIN `es.sector_gics` roto / CIIU largo vs 4 díg | `list_locales_by_sector("5510")` y `("3510")` aislado devuelven 6 regionales + 6 startups cada uno | ❌ refutada — el repo y el JOIN funcionan |
| `g_code` vacío o nombre sin código | `extract_gics_code` resuelve `Servicios públicos`→`5510` y `Equipos y servicios de atención médica`→`3510`, con y sin `(GICS ….)` | ❌ refutada |
| Sector sin datos | `entidad_sectores`: 5510=563 locales/23 startups; 3510=3253/42; 1010=342/17 | ❌ refutada — poblados |
| **Flag `anclaje_local_enabled`** | `get_settings()` → `anclaje_local_enabled=False` (flags ausentes de `.env`) | ✅ **CAUSA RAÍZ** |

**Mecanismo:** en `generate_n1.py` el guard `if s.anclaje_local_enabled and g_code:` es `False` cuando
el flag no está en `.env`; `regionales`/`startups` quedan `[]`, `jugadores_locales_ctx=""`,
`kb_locales=[]`. La sección 2.1.2/2.1.3 sale sin jugadores locales. No hay bug de código: la feature
(DT-050/DT-063/DT-066) nunca se habilitó.

### Segundo hallazgo: routing de sector para ERCO (Energía 1010 vs Utilities 5510)

Al habilitar los flags, ERCO (aclaración del usuario: **es Energía, no Servicios públicos**) clasifica
a **1010**. Pero:

- **GICS canónico:** las eléctricas — incluidas renovables/solar — son **Utilities (55 / 5510)**;
  **Energy (10 / 1010)** es petróleo, gas, carbón y minería. La intuición "es energía" es coloquial.
- El mapa CIIU→GICS del proyecto ya lo refleja: **CIIU D3511 (generación eléctrica) → `5510`**
  (`ciiu_division_to_gics("3511") == "5510"`; división 35 → 5510). El seed EMIS usó ese mapa, por eso
  los pares curados (EPM, Celsia, Isagen, Enerbit) viven en **5510**, y **1010** quedó poblado por
  mineras/refinación (correcto para GICS Energy).

Evidencia cuantitativa (con `productos_terms` de ERCO = solar/generación/fotovoltaica y exclusión de la
focal — la ruta real del pipeline):

| Tier | ERCO **@1010** (single) | ERCO **@[1010,5510]** (multi-sector, fix) |
|---|---|---|
| Regionales | M&M Metals **Gold**, Hidrológica, Vías y Explanaciones, Sator, Navar, **Stracon** (minería/vías) ❌ | **Enerbit, Celsia, Isagen, Nitro Energy, Espacio Productivo, Hidroeléctrica Ituango** ✅ |
| Startups | GOLDEN ENERGY, ENERGY MASTER, AZIMUT, POWERP, BATX ✅~ | GOLDEN ENERGY, COVATIO, ECOLUMEN, ENERGY MASTER, AZIMUT, POWERP ✅ |

HolaDr@3510 sale limpio con y sin multi-sector (CIIU 8610/8690 → división 86 → **3510**, mismo sector →
**sin regresión**): clínicas + healthtechs.

## Fix implementado

Config-first para el defecto literal; código para el routing multi-sector.

1. **`.env` (config, ADR-002; gitignored):** habilitados `ANCLAJE_LOCAL_ENABLED=true`,
   `SECCION21_DETERMINISTA_ENABLED=true`, `DISCOVER_GLOBALES_ENABLED=true`. (Los nombres uppercase
   mapean directo a los campos de `Settings`; pydantic-settings case-insensitive.)

2. **`shared/constants/ciiu_gics.py` — `sectores_ancla_local(g_code, ciiu)` (puro):** une el grupo del
   LLM con el grupo **preciso** del CIIU por división (`ciiu_division_to_gics`, single y sin ruido —
   8610→3510 no arrastra 2020, a diferencia del section-map multivaluado). Orden estable, sin
   duplicados; sin CIIU → solo el grupo (invariante). No fabrica sectores.

3. **`data/repositories/entidad_repo.py` — `list_locales_by_sector`** ahora acepta
   `str | Sequence[str]`: JOIN con `es.sector_gics = ANY(:sectores)`; las filas de todos los sectores se
   juntan en un pool y compiten por **solape de producto** (re-rank de dominio ya existente); **dedup
   por nombre normalizado** (`_clave_exclusion`) → una entidad multi-sector aparece una vez y colapsa
   duplicados cross-sector (p. ej. "ERCO ENERGIA"×2). Prefetch escalado ×nº de sectores (que un sector
   grande no desplace del window a los pares relevantes del otro antes del re-rank). Compat total con
   los callers `str`.

4. **`domain/use_cases/generate_n1.py`:** computa `ciiu_ancla = ctx.empresa.actividad_ciiu or
   ctx.params.ciiu` (el CIIU resuelto en N0 vía RUES vive en `ctx.empresa.actividad_ciiu`, no en
   `params`) y `sectores_local = sectores_ancla_local(g_code, ciiu_ancla)`; pasa `sectores_local` a los
   dos `list_locales_by_sector` (regionales + startups). El guard sigue exigiendo `g_code`.

## Tests

- `tests/test_fase14_ciiu_gics.py`: `sectores_ancla_local` — une energía 1010+5510; sin regresión
  cuando coinciden (3510); sin CIIU → solo grupo; sin grupo → solo CIIU.
- `tests/test_kb_entidades.py`: multi-sector usa `ANY(:sectores)` y pasa la lista + prefetch escalado;
  acepta `str` (compat); **dedup por nombre normalizado**; `[]`/`""` cortocircuita sin tocar BD.
- Suite `not slow`: **638 passed, 2 skipped, 14 deselected** (baseline 630 + 8 nuevos). `ruff` limpio.

## Validación E2E (✅ 2026-08-06, ambas empresas, `--refresh`)

`--refresh` para invalidar la caché durable (una corrida previa con flags OFF pudo persistir Cap 2 sin
tier local). Criterios: (1) capítulos inician con prosa/encabezado (UI04c); (2) focal excluida de sus
tiers (UI04a); (3) 2.1.2/2.1.3 con pares locales del sector (UI04b).

- **ERCO `--ciiu 3511`** (`output/erco_energía_sas_informe.docx`): 2.1.2 Regionales = **Enerbit, EPM,
  Isagen, Neu Energy, BTG Pactual Energía, Vervantis** (pares energéticos reales vía 5510 — el fix
  multi-sector); startups = GOLDEN ENERGY, ECOCITY, TELEMETRIK, COVATIO, ECOLUMEN; globales (discover
  web) = BYD, EDF Renewables, First Solar, Fluence, AES, CATL, Enel Green Power. UI04c ✅ (6 caps con
  prosa) · UI04a ✅ (ERCO fuera de todo tier).
- **HolaDr `--ciiu 8690`** (`output/hola_doctor_sas_informe.docx`): 2.1.2 = Angiosur, Expert Médica, IQ
  Interquirófanos, Clínica Oftalmología Sandiego, Neurum, Clínica Genezen; startups = TERAL, MINDORA,
  COCO AI&E-HEALTH, SUNUBE, GEOMEDICAL, AIRA BIOTECH; globales = Doctolib, Ping An, Teladoc, Amwell,
  Practo. Sin regresión (sector único 3510). UI04c ✅ · UI04a ✅ — "HOLADR." **no** aparece como propia
  competencia (quedó fuera del top-6 por el re-rank; la debilidad de alias-exclusión no se materializó
  esta corrida pero sigue como deuda).

## Deuda técnica / problemas abiertos descubiertos

- **DT-UI04a — exclusión de "HOLADR."**: la focal "HOLA DOCTOR S.A.S." NO excluye la entidad KB
  "HOLADR." (forma pegada sin espacio → normaliza a `holadr` ≠ `hola doctor`, sin tokens en común). El
  match por subconjunto de tokens tampoco resuelve este caso. Fix real futuro: cotejar también contra
  los **aliases** de la entidad. Reaparece en 2.1.3 hasta entonces.
- **DT-050b — duplicados en KB**: "ERCO ENERGIA"×2, "ENERGY MASTER"×2 (distintos `id`, mismo nombre).
  El dedup por nombre de esta sesión los colapsa **en la lectura del anclaje**, pero la reconciliación
  real (por NIT) sigue pendiente (DT-050b).
- **Fichas cross-sector**: `list_ficha_atributos_by_sector` sigue usando `g_code` único (`e.sector_gics
  = :sector`); un local traído de un sector secundario (p. ej. Celsia@5510 con ERCO@1010) no encontrará
  su ficha por `g_code=1010`. Es un boost (el hole-filler rellena); documentado, no bloqueante.
- **Anclaje global (2.1.1) sigue single-sector**: `list_competidores_by_sector` NO se hizo
  multi-sector (scope acotado a locales). Para ERCO@1010 los globales pueden ser escasos (los globales
  verificados de energía están bajo 5510). Candidato a extensión con el mismo `sectores_ancla_local`.
- **Clasificación 1010 vs 5510**: si el LLM emite "(GICS 1010)" explícito, `classify_gics` lo respeta
  (aunque el CIIU sugiera 5510). El multi-sector lo hace robusto para el tier local, pero el resto del
  informe (queries de retrieval, globales) usa el `g_code` clasificado. Considerar si D35xx debería
  forzar 5510.
