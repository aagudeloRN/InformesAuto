# Handoff — próxima sesión (arranque en chat limpio)

> Estado al cierre 2026-08-06. Rama `develop`, sincronizada con GitHub (último commit `df229b2`).
> Copia el bloque "PROMPT DE ARRANQUE" de abajo en un chat nuevo.

## Dónde quedamos
- **DT-UI04b CERRADO**: anclaje local **multi-sector** (grupo LLM ∪ grupo canónico del CIIU),
  `list_locales_by_sector` acepta `Sequence[str]` con `ANY`+dedup. E2E ERCO/HolaDr OK.
- **Estilo CERRADO**: `soften_caps` (MAYÚSCULAS StartIA) + tono **propositivo** en Cap 5 y Cap 6.
- **Despliegue CERRADO**: UI en `http://192.168.0.99:8503` (server), BD `informes_ic` migrada,
  casos de estudio sembrados. Runbook: `docs/runbooks/DESPLIEGUE_SERVIDOR.md`.
- Suite `not slow`: 643 passed. Gate verde.

## Foco recomendado: DT-UI04f (dev, localhost) — completar multi-sector 2.1.1 + exclusión por aliases
Continúa lo de hoy y mejora la parte más visible del informe (sección 2.1). Todo dev/testable, sin
depender del server ni de fuentes nuevas.

**Bloqueado (NO tocar hasta tener fuentes):** casos de éxito globales e inversiones pobres.

---

## PROMPT DE ARRANQUE (copiar en chat limpio)

```
ROL: Claude Code, ingeniero senior de InformesAuto (rama `develop`).
Proyecto en /home/aagudelo/Test/InformesAuto. Localhost/dev (WSL2).

CONTEXTO (sesión previa 2026-08-06, commit df229b2, todo en GitHub):
- DT-UI04b cerrado: anclaje LOCAL multi-sector. `sectores_ancla_local(g_code, ciiu)` en
  shared/constants/ciiu_gics.py une el grupo del LLM con el grupo canónico del CIIU (por
  división). `list_locales_by_sector` (data/repositories/entidad_repo.py) acepta
  str|Sequence[str] con `es.sector_gics = ANY(:sectores)` + re-rank por solape + dedup por
  nombre. Cableado en domain/use_cases/generate_n1.py.
- Estilo cerrado: soften_caps (shared/text_utils.py) + tono propositivo en Cap 5/6.
- App desplegada en el server (192.168.0.99:8503); esto NO afecta el trabajo de hoy (es dev).

TAREA — DT-UI04f: completar el anclaje multi-sector en el tier GLOBAL y las fichas, y
endurecer la exclusión de la empresa focal por aliases.

  FASE 1 — Multi-sector en globales (2.1.1) + fichas:
   - `list_competidores_by_sector` (globales) sigue single-sector (`e.sector_gics = :sector`).
     Extenderla a multi-sector igual que `list_locales_by_sector` (aceptar str|Sequence[str],
     `= ANY(:sectores)`, dedup por nombre), reusando `sectores_ancla_local`.
   - `list_ficha_atributos_by_sector` usa `e.sector_gics = :sector` (single) → un local/global
     traído de un sector secundario no encuentra su ficha. Extender a multi-sector.
   - Cablear en generate_n1.py: pasar `sectores_local` (o el equivalente) también al path global
     y al de fichas. Verificar que ERCO@1010 traiga globales de energía de 5510 sin diluir.

  FASE 2 — DT-UI04a por aliases:
   - `_clave_exclusion` (entidad_repo.py) solo compara el `nombre`. "HOLADR." NO se excluye vs
     "HOLA DOCTOR S.A.S." (normalizan distinto, sin tokens comunes). Cotejar también contra los
     `aliases` (jsonb) de la entidad: si la clave de exclusión de la focal empata el nombre O
     algún alias, se excluye. Verificar con HolaDr E2E aislado (list_locales/list_competidores).

LECTURAS OBLIGATORIAS antes de proponer cambios:
 - src/ic/data/repositories/entidad_repo.py — `list_competidores_by_sector`,
   `list_ficha_atributos_by_sector`, `list_locales_by_sector` (patrón multi-sector ya hecho),
   `_clave_exclusion` (+ cómo se leen `aliases`).
 - src/ic/shared/constants/ciiu_gics.py — `sectores_ancla_local` (reusar).
 - src/ic/domain/use_cases/generate_n1.py — dónde se llama cada método (global/local/fichas).
 - src/ic/data/models/entidad.py — columna `aliases` (jsonb) de `entidades`.
 - tests/test_kb_entidades.py — tests de exclusión + multi-sector (calcar).

PROCESO:
 - Plan Mode (CLAUDE.md TIER 2). Reproducir aislado contra la BD real ANTES de tocar:
   instanciar EntidadRepository y comprobar globales/fichas por sector para ERCO (1010) y
   HolaDr (3510), y la exclusión de "HOLADR.". Si la realidad no coincide con la hipótesis,
   DETENERSE y replantear (como pasó con UI04b).
 - Cambios atómicos, capas respetadas (presentation→domain→data→infrastructure). Sin hardcodear
   modelos (ADR-002).

CRITERIOS DE ÉXITO:
 1. `list_competidores_by_sector(["1010","5510"], alcance="global", productos_terms=…)` para ERCO
    trae globales de energía reales (no diluye con otro sector); dedup sin duplicados.
 2. Fichas de un jugador de sector secundario se resuelven (no quedan vacías por g_code).
 3. "HOLADR." NO aparece como su propia competencia cuando la focal es "HOLA DOCTOR S.A.S."
    (exclusión por alias), sin romper los tests UI04a existentes.
 4. Nuevos tests en tests/test_kb_entidades.py (multi-sector global + fichas + alias-exclusión).

GATE DE CIERRE:
 - `ruff check src/ tests/` limpio.
 - `uv run pytest -m "not slow" -q` verde (baseline: 643 passed, 2 skipped).

QUICK-WINS opcionales si queda tiempo:
 - Trackear documentos_sectoriales/FuentesExternas/CatalogoVerticalesStartIAGICS.csv en git.
 - Fix packaging: `uv sync` deja el wheel `ic` incompleto (la app corre por sys.path de app.py);
   revisar [tool.hatch/setuptools packages] en pyproject.toml para que instale todo el paquete.

DOCUMENTAR AL CERRAR: DT_UI04f (o sección en ROADMAP.md) + 1 línea en memoria
project_roadmap_ago2026. NO tocar ROADMAP_FASE9+.
```
