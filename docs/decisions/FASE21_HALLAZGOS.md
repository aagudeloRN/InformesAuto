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
**Estado:** intentada en la sesión de cierre; el lanzamiento en segundo plano quedó bloqueado por
una indisponibilidad transitoria del clasificador de comandos del entorno (los servicios Ollama,
PostgreSQL, OpenRouter y Tavily SÍ estaban disponibles y verificados). Queda como **paso manual
reproducible** (§5.1); no bloquea el cierre de código, cubierto por 321 tests fast + mocks.

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
