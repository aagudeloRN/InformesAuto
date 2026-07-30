# Fase 25 — Hallazgos y cierre

> Loop de auto-revisión por-nodo (DT-059): extiende T22.7/DT-048 con el LLM-judge que
> faltaba + la arista de revisión sobre el DAG ya construido. Rama `feature/fase25-dt059`
> desde `develop` (base `2f64c9d`). Gate final: **ruff 0 (src/ tests/), 464 fast tests**
> (438 base + 26 nuevos), 2 skipped. Sin reingesta, sin re-embeber, sin `down -v`.

## §1 — DT-059: loop de auto-revisión (cerrado 2026-07-30)

Cierra el lazo de calidad **por-nodo dentro de UNA corrida**: cada capítulo se puntúa con la
rúbrica v1.0 (F20) y, si no pasa el gate, se revisa y re-juzga hasta 3 veces conservando la
**mejor** versión por score. No re-litiga ADRs; monta el juez + la arista de revisión sobre
el DAG existente (N1 web → N2/N3 integración), tras un flag **default-OFF** (invariante).

### AVANCES (con números)

**T1 — Juez con rúbrica (`f3eb387`).**
- `rubric_score.py` (puro): `RubricScore` (E/P/V/F/T 0–3) + `parse_rubric_score` (tolera
  fences/JSON malformado, clamp 0–3, dimensión ausente = 0) + `pasa_gate` (≥11/15 y sin
  dimensión en 0, regla de la rúbrica §1). RN-001: salida del juez no parseable → peor caso
  (total 0, no acepta) en vez de fabricar un score alto.
- `chain_judge.py`: cadena LCEL con **criterios por capítulo** derivados de `RUBRICA_CALIDAD.md
  §2` (Caps 2/3/4/5/6). Modelo inyectado (ADR-002; sin nombres de modelo en código).
- Config: `selfreview_enabled=False` (default-OFF) + `selfreview_min_total=11` +
  `selfreview_max_iter=3`. **El LLM-judge que T22.7/DT-048 dejó planeado y nunca se implementó.**

**T2 — Loop puro guardar-el-mejor (`7c87bbd`).**
- `self_review.py` (puro, callables inyectados): `run_self_review(generate_fn, judge_fn,
  revise_fn, min_total, max_iter)` → `(mejor_cap, RevisionTrace)`. Conserva la **mejor** versión
  por score (no la última). Parada: `umbral` (pasa el gate) · `sin_mejora` (una revisión no
  supera el mejor score) · `max_iter`. `RevisionTrace` registra intentos, iteración ganadora y
  motivo (insumo de la trazabilidad T4).
- **Selectivo**: el caller solo entra al loop para el cap cuyo score inicial no pasa el gate.

**T3 — Dos sabores + cableado tras flag OFF (`ec85dd0`).**
- `chain_revise.py`: cadena genérica reusada por todos los caps (borrador + faltantes del juez
  + evidencia → reescritura anclada en evidencia, RN-001).
- `self_review_hooks.py` (aísla LLM/store/red del núcleo puro, patrón `checkpoint_hooks`):
  - **`review_web_cap`** (Caps 2/3/4): Reflexion con herramientas — cada faltante del juez
    dispara una **búsqueda web dirigida**; reusa el **anclaje del KB de DT-056** (perfiles de
    competidores canónicos); re-recupera y re-sintetiza con evidencia enriquecida.
  - **`review_integration_cap`** (Caps 5/6): solo re-sintetiza sobre la evidencia ya recuperada
    (sin nuevo retrieval; los N2 consumen los N1 ya refinados por orden del DAG → "web sólidos
    antes de integrar" sale gratis).
- Cableado en `generate_n1` (dentro del thread con el `store` vivo) y `_run_n2`. **Invariante
  testeado**: con el flag OFF el cap se devuelve intacto y el loop no se invoca.

**T4 — Trazabilidad en BD (`fd7d5e4`).**
- `revision_capitulo.py`: tabla `revisiones_capitulo` (run_key, capítulo, sabor, n_iteraciones,
  iter_ganadora, score_inicial/final, motivo_parada, dimensiones/faltantes JSONB) + migración
  idempotente `ensure_revisiones_tables` (patrón `entidad.py`, esquema propio, IF NOT EXISTS).
- `revision_repo.py`: `RevisionRepository.save_revision` (append-only: cada corrida deja su
  historial, TIER 4). Enganchado en `_persist_trace` con **fallo suave** (nunca aborta la
  corrida; patrón checkpoint) + log de una línea (`Δ score, nº iter, motivo`) para inspección.

### RETOS / lecciones

- **El juez/rúbrica existían solo como documento.** El grep confirmó que T22.7/DT-048 (LLM-judge)
  nunca llegó a código y `eval_gate`/`retrieval_metrics` mide *retrieval*, no calidad de capítulo.
  DT-059 tuvo que **construir** el juez, no solo cerrar el loop.
- **Sesión SQLAlchemy no thread-safe → la revisión web vive dentro del thread.** El `store` N1 se
  crea por-thread en `_store(fn)` y muere al cerrar la sesión; por eso `review_web_cap` se invoca
  **dentro** de cada `_fn_capN` (store vivo), no después de recolectar resultados.
- **Atomicidad T3/T4.** `_persist_trace` acopla el hook (T3) con el repo (T4); se mantuvo como stub
  en T3 y se completó en T4 para que cada commit compile y corra por separado.
- **E2E real pendiente (marcado `slow`).** Los tests fast usan juez/revisor mockeados; la validación
  con Ollama/OpenRouter real (Δ score por cap, nº de revisiones, cuántos caps mejoran) queda como
  corrida `slow` a ejecutar con `selfreview_enabled=True` sobre 1 sector (ver RECOMENDACIONES).

### RECOMENDACIONES

1. **Correr el E2E `slow` con el flag ON** (1 sector) para medir el Δ real de la rúbrica y calibrar
   `min_total`/`max_iter`; registrar los números aquí.
2. **Panel HITL** (F24/F25): exponer `revisiones_capitulo` en el historial (score inicial→final,
   motivo, faltantes) para que el analista audite dónde el loop mejoró.
3. **DT-060 (reingesta A/B)**: mejor extracción (tablas/estructura) reduce el ruido del NER → menos
   faltantes de evidencia que el sabor web debe re-buscar (sinergia con este loop).

### Verificación

- `uv run ruff check src/ tests/` → 0.  `uv run pytest -m "not slow" -q` → **464 passed**, 2 skipped.
- Invariante: `selfreview_enabled=False` (default) → cap intacto, loop no invocado (testeado en
  `test_fase25_flavors`).
- Migración `ensure_revisiones_tables` idempotente (fake engine, doble llamada, IF NOT EXISTS). Sin
  tocar vectores, sin `down -v`.

---

## §2 — Prompt de arranque de la siguiente ventana

El usuario decide entre **DT-060 (reingesta RAG gated por A/B)** y **HITL F24/F25** (Gap Auditor +
Consistency Checker, que ya pueden apoyarse en el panel de `revisiones_capitulo`).

```
## ROL
Eres Claude Code, ingeniero de InformesAuto (~/Test/InformesAuto): inteligencia competitiva (RAG
local pgvector + Ollama, LangChain, capas). DT-059 (loop de auto-revisión) está CERRADO y mergeado
(rama feature/fase25-dt059): juez con rúbrica v1.0 (rubric_score + chain_judge), loop puro
guardar-el-mejor (self_review), dos sabores (web re-busca reusando KB DT-056; integración solo
re-sintetiza), trazabilidad en revisiones_capitulo. Flag selfreview_enabled default-OFF
(invariante). Gate base: ruff 0, 464 fast tests.

Hoy ejecutas <DT-060 reingesta A/B | HITL F24/F25>. Rama nueva desde develop.

## RESTRICCIONES (CLAUDE.md TIER 1)
- Sin nombres de modelo en código (config/.env/routing, ADR-002). domain/ no importa
  SQLAlchemy/httpx/Streamlit; librería externa por wrapper en infrastructure/. Sin credenciales.
- Cambios atómicos: 1 commit por tarea, gate verde tras cada uno (ruff 0 + pytest -m "not slow").
  Plan Mode. BD: esquema propio, migraciones idempotentes ensure_*, NUNCA down -v.

## LECTURAS OBLIGATORIAS
- docs/decisions/FASE25_HALLAZGOS.md (este cierre). docs/architecture/PROPUESTA_KNOWLEDGE_BASE.md.
- memory: project_fase25_dt059_estado, roadmap.

## DONE
1. <objetivo de la ventana>. 2. Gate verde. 3. 1 commit atómico por tarea. 4. Docs/memoria
   actualizados. 5. Decidir siguiente ventana.
```
