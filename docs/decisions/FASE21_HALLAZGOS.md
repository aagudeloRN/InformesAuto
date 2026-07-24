# FASE 21 — Hallazgos: Calidad de Contenido (Sprint A + A')

**Fecha:** 2026-07-24 · **Branch:** `feature/fase21-calidad-contenido`

> Fase de **contenido**: aquí SÍ se tocan prompts de chains, assembler y wrappers. Cada cambio
> con test unitario y documentado en `docs/prompts/`. Alcance: las 8 tareas T21.1–T21.8, incluido
> T21.6 (2.3 Mercado), decidido con el humano en Plan Mode.

**Gate de entrada:** ruff 0 · `pytest -m "not slow"` = 305 passed / 2 skipped. ✅
**Gate de salida:** ruff 0 · `pytest -m "not slow"` = **321 passed / 2 skipped** (+16 tests F21). ✅

---

## 1. Objetivo

Cerrar el hallazgo raíz de Fase 20 (variabilidad brutal por sector: Alpina ~11–13/cap dentro del
corpus; avianca/bancolombia ~5–7/cap y 0 tablas). F21 ataca las causas (b) prompts con sesgo
alimentos y (c) secciones del patrón ausentes. La causa (a) — cobertura del corpus por sector —
es F23.

---

## 2. Cambios por tarea (1 commit atómico cada uno)

| Tarea | DT | Commit | Resumen |
|---|---|---|---|
| T21.1 | DT-035 | `1a96d7b` | `search_depth` parametrizable (WebConnector + CachedWebConnector) y queries de competidores con `advanced`. Firma pública intacta (default `basic`). |
| T21.2 | DT-036 | `e64c107` | Constraint sectorial en casos locales de `chain_04` + query web sectorial en `generate_tendencias`. |
| T21.5 | DT-043 | `f927ac8` | Des-sesgado de `chain_03`/`chain_04` por `{sector_gics}` (fuera "bienes de consumo/FoodTech/agroindustrial"). `chain_03` recibe ahora `sector_gics`. |
| T21.7 | DT-045 | `a97b029` | Secciones formales **Metodología** y **Aviso sobre el uso de IA** en `assembler.py`. |
| T21.8 | DT-046 | `beecd9c` | Rediseño de `chain_05` a movimientos corporativos **4.1–4.5** (3 eventos por subcap: título + ejecución + capacidad estratégica + vulnerabilidad mitigada). |
| T21.6 | DT-044 | `7883ec6` | **Cap 2.3 Mercado**: chain `chain_03b_mercado` + tipo `CapMercado` + use case `GenerateMercado` + cableado N1 (`max_workers=4`) + interleave en `assembler` entre 2.2 y 2.4. |
| T21.3 | — | `9a27820` | Runbook `BUSQUEDA_FUENTES.md` reconciliado con los scripts reales (ya existía con las ecuaciones de `source_prompts/0`). |

Documentación de prompts actualizada: `prompt-03-benchmarking.md`, `prompt-04-tendencias.md`,
`prompt-05-ecosistema.md`, nuevo `prompt-03b-mercado.md`, `README.md` (9/9 chains).

---

## 3. Decisiones de diseño

- **`search_depth` en la clave de caché** (`CachedWebConnector`): solo se diferencia cuando no es
  `basic`, para no invalidar las claves ya cacheadas de búsquedas básicas.
- **2.3 Mercado como chain N1 separada** (no dentro de `chain_03`): permite paralelizarla y aplicar
  RN-001 de forma independiente. El interleave se hace en el assembler (`_insert_before_subheading`,
  ancla `prefix="2.4"`); si el retrieval es insuficiente, la sección se omite.
- **Cap 4 reescrito, no parcheado**: la estructura vieja (actores Local/Global/Disruptores) se
  reemplaza por completo por los 5 subcaps de movimientos del patrón Noel. `renumber_subheadings`
  ya maneja la numeración; el assembler no cambió para Cap 4.
- **RN-001 preservada en todo**: mercado, Cap 4 y casos locales emiten "Dato no disponible en
  fuentes consultadas" cuando faltan datos. Ninguna afirmación se apoya en el conocimiento del LLM.

---

## 4. Estado de la deuda técnica

| ID | Estado | Nota |
|---|---|---|
| DT-035 | ✅ cerrada | `search_depth` + queries de competidor `advanced`. |
| DT-036 | ✅ cerrada | Constraint sectorial + query dedicada de casos locales. |
| DT-043 | ✅ cerrada | Prompts Cap 2/3 des-sesgados por `{sector_gics}`. |
| DT-044 | ✅ cerrada | 2.3 Mercado implementada y ensamblada. |
| DT-045 | ✅ cerrada | Metodología + Aviso IA como secciones formales. |
| DT-046 | ✅ cerrada | Cap 4 rediseñado a 4.1–4.5. |

Deuda que permanece para fases posteriores (sin cambio de alcance): DT-047 (áreas Cap 5, F22),
DT-048 (LLM-judge de la rúbrica, F22), DT-034 (lote EMIS completo, F23).

---

## 5. Validación E2E (T21.4 + cross-sector)

<!-- RESULTADOS_E2E -->
**Corrida real: Alpina S.A.S. (3020)** — `output/alpina_sas_informe.docx`, 662 s, costo API $0
(modelos free), 55.330 tokens in / 33.339 out.

**Criterios estructurales F21 — TODOS cumplidos:**

| Criterio | Resultado |
|---|---|
| 2.3 Mercado ensamblada (entre 2.2 y 2.4) | ✅ heading "2.3. Mercado" + **tabla 5×4** (Región/Tamaño/Crecimiento/Año) |
| Metodología (sección formal) | ✅ presente |
| Aviso sobre el uso de IA (sección formal) | ✅ presente |
| Cap 4 rediseñado a 4.1–4.5 | ✅ 4.1 Inversiones / 4.2 Integraciones / 4.3 M&A / 4.4 JV / 4.5 Alianzas |
| Cap 3 sin casos KPO/turismo (constraint sectorial) | ✅ 0 menciones de "KPO"/"turismo" |

**Hallazgo crítico de evidencia (→ DT-049):** el informe citó **solo 3 referencias** (2 documentos
compilados "Ruta N" + 1 web `todolicitaciones.cl`) con **18 "Dato no disponible"** y la sección
2.1 (fichas de competidor) en ausencia ("No se encuentra información al respecto en los documentos
proporcionados"). Diagnóstico en BD (2687 chunks): 3020 tiene 44 chunks sectoriales + 594 globales,
pero los 44 provienen de **un único documento compilado** → baja diversidad de fuentes citables.
**Causa confirmada:** el lote EMIS diverso (250 PDFs, p. ej. 3020 con 13 fuentes: CFA, EMIS,
Euromonitor, GlobalData…) **está en disco en `documentos_sectoriales/FuentesEMIS/` con su
`indice_emis.csv`, pero nunca se ingestó** (DT-034); la BD solo tiene los compilados de Fase 13.
La búsqueda web ingestó **122 chunks pero solo 1 se citó** (resultados poco relevantes; el resto lo
purga ADR-013 "solo citado"). Las secciones granulares nuevas (fichas, tabla de mercado, eventos
M&A/JV) exigen datos que el corpus compilado no contiene. Comparación: la corrida Alpina previa
(Fase 18) citaba 4-5 refs; la baja a 3 es varianza del web + el mismo techo de corpus, no una
regresión de código de F21. **Registrado como DT-049** — la mitad de corpus se resuelve
**ingestando el lote EMIS ya disponible** (T23.1/DT-034:
`uv run python scripts/ingest_batch.py --dir documentos_sectoriales --csv documentos_sectoriales/FuentesEMIS/indice_emis.csv`);
la mitad de retrieval/breadth → F22 (T22.4). Este es el trabajo de mejora que sigue.

_Cross-sector (avianca 2030 / bancolombia 4010) con la rúbrica: pendiente de corrida manual (§5.1);
mismo techo de corpus aplica._

### 5.2 Prueba A/B — ingesta del sector 3020 (2026-07-24)

Se ingestó el lote EMIS del sector 3020 (con el fix DT-051 de bytes NUL): **44 → 286 chunks en
14 documentos distintos** (EMIS Colombia F&B 121, CFA 49, compilado viejo 44, GlobalData 11, 10
Euromonitor "Sector Capsule"). Se re-corrió el E2E de Alpina (`output/alpina_sas_post_emis.docx`).

| Métrica | Antes (pre-EMIS) | Después (post-EMIS 3020) |
|---|---|---|
| Tablas Word | 1 | **16** |
| Cap 2.1 fichas de competidor | ausente | **14 fichas en tabla** |
| Radar de posicionamiento | placeholder | **datos reales del LLM (6 comp., 5 dims)** |
| Referencias citadas | 3 | **3 (sin cambio)** |
| "Dato no disponible" | 18 | 23 |

**Lectura:** el corpus enriquecido **mejoró mucho el contenido** (fichas de competidor, radar real,
tablas), lo que valida ingestar el lote EMIS completo (F23/DT-034). Pero **la citación no siguió al
corpus**: las 14 fuentes EMIS nuevas no aparecen en Referencias ni en el texto (Euromonitor/CFA/
GlobalData = 0 menciones), 0 chunks web citados (123 descartados por ADR-013) y hay una cita
huérfana. Es un problema de **atribución/trazabilidad (RN-001)**, no de disponibilidad de corpus →
**DT-052**, a resolver en F22 junto con el breadth de retrieval (T22.4/DT-049). El aumento de
"Dato no disponible" (18→23) viene de que las secciones granulares (2.3 tabla por región, Cap 4
eventos) ahora intentan más celdas y reportan honestamente las que faltan.

### 5.1 Procedimiento reproducible

```bash
# Alpina (sector 3020, dentro del corpus):
uv run python scripts/run_pilot.py --empresa "Alpina S.A.S."
# Cross-sector (fuera del corpus food):
uv run python scripts/run_pilot.py --empresa "Bancolombia S.A."
```

Criterios de aceptación:
1. Cap 2 (Alpina) con ≥1 ficha de competidor con datos reales (no solo "Dato no disponible").
2. Cap 3 (Alpina) sin casos de KPO ni turismo (sectores ajenos a alimentos).
3. Ensamblado incluye **2.3 Mercado** + **Metodología** + **Aviso de uso de IA**.
4. Cross-sector: Cap 2 y Cap 4 ≥ 11/15 según `docs/eval/RUBRICA_CALIDAD.md`.

> Nota: la cobertura sectorial del corpus (causa raíz (a), F23) limita el score alcanzable de
> empresas fuera de alimentos; F21 elimina el sesgo de prompts y añade las secciones, pero el
> techo de datos por sector se sube en F23 (corpus EMIS).

---

## 6. Métricas de cierre

| | Fase 20 | Fase 21 |
|---|---|---|
| Fast tests | 305 | **321** (+16) |
| ruff | 0 | 0 |
| Chains operativas | 8 | **9** (`chain_03b_mercado`) |
| Secciones del patrón faltantes | 2.3 Mercado, Metodología, Aviso IA, Cap 4 | **0** (todas implementadas) |
| Deuda §5 de contenido viva (F21) | DT-035/036/043/044/045/046 | **0 (todas cerradas)** |
| Deuda nueva descubierta en el E2E | — | **DT-049** (evidencia RAG delgada / diversidad de fuentes → F22+F23) |
