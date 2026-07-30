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
- **Los tests fast escribían a la BD compartida.** `test_fase25_flavors` corría el `_persist_trace`
  real (Postgres) al completar una revisión con el flag ON → contaminaba `revisiones_capitulo` con
  filas de fixtures. Corregido: se parchea `_persist_trace` a no-op en esos tests (los fast NO tocan
  la BD; la persistencia se prueba aparte con engine/sesión falsos). Filas de test purgadas.

### E2E de calibración (Alpina S.A., `selfreview_enabled=True`, 2026-07-30)

Corrida real **completa** (Ollama + OpenRouter free + Tavily): informe entero generado en **1120 s
(~18.7 min)**, `output/alpina_sa_informe.docx`+`.pdf`, 11 referencias, anti-mezcla `ajeno=0`. Hubo un
`ResourceExhausted 502` transitorio del tier free en N2, resuelto por el **fallback de tiers**
(`ResilientChatModel`) sin abortar. Datos de `revisiones_capitulo` (5 caps review-elegibles, ambos
sabores):

| Capítulo | Sabor | Score | Iter | Parada | Resultado |
|----------|-------|-------|------|--------|-----------|
| Cap 3 Tendencial | web | 13→13 | 0 | umbral | pasa el gate a la 1ª → **no se revisa** (selectivo) |
| Cap 4 Ecosistema | web | 12→12 | 0 | umbral | pasa a la 1ª → no se revisa |
| Cap 2 Competitivo | web | **6→10** | 2 | sin_mejora | falla el gate; re-busca 2× → **+4**; conserva el mejor (10), no el último |
| Cap 5 Convergencia | integración | **6→14** | 1 | umbral | falla el gate; re-sintetiza 1× → **+8**, alcanza el gate |
| Cap 6 Accionables | integración | 10→10 | 1 | sin_mejora | falla el gate; 1 revisión NO mejora → **conserva el original** (iter_ganadora=0), no la revisión |

**Lo que valida:** (1) selectivo (2/5 caps que pasan no se re-generan); (2) guardar-el-mejor + las dos
paradas (`umbral` ×3, `sin_mejora` ×2) — Cap 6 demuestra que una revisión que **no** mejora se
descarta (se conserva el original); (3) de los 3 caps revisados, **2 mejoran** (Cap 2 web +4, Cap 5
integración +8); (4) ambos sabores ejercidos en una corrida real que produce el informe entero.
**Señal recurrente:** la dimensión **V (Evidencia/Citación)** puntúa bajo en los caps web (corrobora
DT-049: evidencia RAG delgada) → el sabor web ayuda (Cap 2 +4) pero **topa en 10** cuando el corpus
no da más (liga con DT-060: mejor extracción = más techo). Umbral `min_total=11` y `max_iter=3` se
comportan bien; no requieren recalibración por ahora.

### RECOMENDACIONES

1. **Subir el techo del sabor web (DT-060):** Cap 2 mejoró +4 pero topó en 10 (<11) por evidencia
   delgada; mejor extracción (tablas/estructura EMIS) le daría margen para alcanzar el gate.
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

### Revisión del usuario (2026-07-30) — falencias observadas en el informe → trabajo de mañana

El usuario revisó `alpina_sa_informe.docx`: **mejoró mucho** vs. corridas previas, pero persisten
falencias serias en el **descubrimiento de competidores** y varios capítulos aún salen **sin
información**. Evidencia extraída del log y del `.docx`:

- **Competidores irrelevantes / de industria ajena (raíz identificada).** La lista anclada del KB para
  Alpina (empresa de **lácteos**) fue:
  `['Food and Beverage Industry News', 'Postobón SA', 'Beverage Industry News', 'Fomento Económico
  Mexicano', 'Coca-Cola Co', 'Profit perEmployee', 'ProfitMargin', 'Fedepalma']` (KB=8, LLM=3).
  Problemas: (a) **ruido NER** — medios ("… Industry News") y fragmentos de métrica OCR-pegados
  ("Profit perEmployee", "ProfitMargin"); (b) **industria equivocada** — Postobón/Coca-Cola/FEMSA
  (bebidas azucaradas), Fedepalma (palma); (c) **cero pares lácteos reales** (Colanta, Alquería,
  Nestlé, Danone, Parmalat ausentes). También se coló "Bavaria (Cervecería)" como actor en Cap 4.2.
- **Causa raíz: granularidad del sector.** El anclaje usa `sector_gics=3020`, que en GICS es el
  **industry group "Food, Beverage & Tobacco"** — agrupa alimentos + bebidas + tabaco. Anclar a ese
  nivel trae bebidas/tabaco/palma como "competidores directos" de una láctea. El criterio de
  **actividad/producto** del KB (DT-056 §1.4: sector, tamaño, geografía, **actividad**) **no se está
  aplicando**; y el ranking por señal (`n_menciones`) premia publishers/industrias adyacentes sobre
  los pares reales.
- **Capítulos/subsecciones sin información.** En el `.docx`: fichas 2.1.2 (Regionales) y 2.1.3
  (Startups) con "todos los campos: Dato no disponible", 2.5 Brechas vacío, 3.3 Casos Locales vacío,
  y Cap 4 (4.1–4.5) casi todo "Dato no disponible" para Monto/Año de eventos. El principio de datos
  ausentes (ADR-002) funciona, pero **dispara demasiado** por evidencia delgada (DT-049) y por falta
  de fuentes estructuradas de eventos/perfiles (DT-054/DT-060).
- **El loop de auto-revisión ayudó pero no puede fabricar evidencia.** Cap 2 subió +4 (6→10) re-
  buscando, pero **topó bajo el gate** porque ni el corpus ni la web dirigida devolvieron pares
  lácteos. El fix es **aguas arriba** (relevancia del KB + granularidad de sector + corpus/extracción),
  no en el loop.

**Trabajo de mañana (nueva DT-061 — relevancia y granularidad de competidores):** ver §2 (prompt de
arranque). Palancas: (1) anclar por **sub-industria/producto** (lácteos) y no por industry group 3020;
(2) aplicar el criterio de **actividad** en `list_competidores_by_sector` (DT-056 §1.4); (3) **purgar/
curar** el ruido del KB (medios, fragmentos de métrica) y **sembrar pares reales** (DT-050); (4) subir
el techo de evidencia (DT-049/DT-060) para que las fichas y Cap 4 dejen de salir vacías.

---

## §2 — Prompt de arranque de la siguiente ventana (DT-061)

Tras revisar el informe de Alpina, el usuario decidió que **mañana se trabaja el componente de
descubrimiento de competidores** (falencias: competidores irrelevantes/de industria ajena +
capítulos sin información). Prompt completo abajo (misma estructura que el prompt DT-059).

```
## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto): informes de
inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas). DT-059
(loop de auto-revisión por-nodo) está CERRADO y MERGEADO a develop (merge 442dd90 + 172f0a0/a369662,
rama feature/fase25-dt059): juez con rúbrica v1.0 (domain/eval/rubric_score.py + domain/chains/
chain_judge.py), loop puro guardar-el-mejor (domain/eval/self_review.py), dos sabores (web re-busca
reusando KB DT-056; integración re-sintetiza — domain/use_cases/self_review_hooks.py), trazabilidad
en informes_ic.revisiones_capitulo. Flag selfreview_enabled default-OFF (invariante). Gate base:
ruff 0 (src/ tests/), 464 fast tests, 2 skipped.

Hoy ejecutas DT-061 — RELEVANCIA Y GRANULARIDAD DE COMPETIDORES (fix del descubrimiento de Cap 2 +
capítulos vacíos). Rama nueva feature/fase26-dt061 desde develop.

## PROBLEMA (evidencia real, E2E Alpina 2026-07-30 — ver FASE25_HALLAZGOS.md §1 "Revisión del usuario")
Alpina es LÁCTEOS. El KB ancló como competidores:
['Food and Beverage Industry News','Postobón SA','Beverage Industry News','Fomento Económico
Mexicano','Coca-Cola Co','Profit perEmployee','ProfitMargin','Fedepalma'] (KB=8, LLM=3).
- (a) RUIDO NER: medios ("… Industry News"), fragmentos de métrica OCR-pegados ("Profit perEmployee",
  "ProfitMargin"). (b) INDUSTRIA AJENA: Postobón/Coca-Cola/FEMSA (bebidas azucaradas), Fedepalma
  (palma), y "Bavaria (Cervecería)" en Cap 4.2. (c) CERO pares lácteos reales (Colanta, Alquería,
  Nestlé, Danone, Parmalat).
- RAÍZ: el anclaje usa sector_gics=3020, que en GICS es el INDUSTRY GROUP "Food, Beverage & Tobacco"
  → demasiado grueso; agrupa alimentos+bebidas+tabaco. El criterio de ACTIVIDAD/PRODUCTO del KB
  (DT-056 §1.4: sector, tamaño, geografía, ACTIVIDAD) NO se aplica; el ranking por señal (n_menciones)
  premia publishers/industrias adyacentes sobre los pares reales.
- ADEMÁS capítulos/subsecciones salen sin información (fichas 2.1.2/2.1.3, 2.5 Brechas, 3.3 Casos
  Locales, Cap 4 4.1–4.5) → evidencia delgada (DT-049) + faltan fuentes estructuradas (DT-054/060).
- El loop DT-059 ayudó (Cap 2 +4) pero NO fabrica evidencia: si el corpus/web no traen pares lácteos,
  topa bajo el gate. El fix es AGUAS ARRIBA (relevancia KB + granularidad de sector + corpus).

## RESTRICCIONES (CLAUDE.md TIER 1 — verificar antes de cada acción)
- Sin nombres de modelo en código (config/.env/routing, ADR-002). domain/ no importa SQLAlchemy/httpx/
  Streamlit; toda librería externa por wrapper en infrastructure/. Sin credenciales en código ni git.
- BD compartida: esquema propio SIEMPRE; NUNCA down -v; migraciones idempotentes ensure_*; datos en
  bind mount. Ollama en host (127.0.0.1:11434). No reingesta/re-embeber salvo que se decida (eso es
  DT-060, gated por A/B).
- RN-001 (no envenenar): el KB acumula con provenance + estado candidato/verificado; corregir sin
  fabricar. Curación honesta (marcar descartado), no invención.
- Cambios atómicos: 1 commit por tarea, gate verde tras cada uno (ruff 0 + pytest -m "not slow").
  PLAN MODE obligatorio (toca KB + granularidad GICS + anclaje del retrieval → decisiones de diseño).

## TAREAS (afinar en Plan Mode con el usuario)
T1 — Granularidad de sector para el anclaje: hoy se ancla por industry group (3020). Evaluar bajar a
  sub-industria/producto (p.ej. "lácteos"/GICS 302020 Food Products o un tag de actividad) para que
  los pares sean de la MISMA actividad, no del industry group. Revisar shared/constants/gics_groups
  (extract_gics_code — ojo feedback: devuelve nombre sin código, mantener fallback) y chain_02_gics.
T2 — Filtro de relevancia por actividad en EntidadRepository.list_competidores_by_sector (DT-056
  §1.4): que el KB devuelva pares por actividad/producto de la empresa analizada, excluyendo ruido
  (medios, fragmentos de métrica) y ordenando por relevancia, no solo por n_menciones.
T3 — Curación/purga del KB + siembra de pares reales: marcar descartado el ruido residual (medios,
  "ProfitMargin", genéricos) por sector; sembrar pares lácteos reales desde la base de empresas
  (DT-050 / documentos_sectoriales) con estado verificado. Idempotente, provenance.
T4 (stretch / puede ir a DT-060) — Subir el techo de evidencia para fichas 2.1.2/2.1.3 y Cap 4:
  medir cuánto de "Dato no disponible" es evidencia delgada (DT-049) vs. gating (DT-058) y proponer.

## PRUEBAS POR TAREA (gate = ruff 0 + pytest -m "not slow")
- Anclaje: dado un KB sembrado, list_competidores_by_sector(actividad='lácteos') devuelve pares
  lácteos y EXCLUYE bebidas/tabaco/medios/métricas (fixtures deterministas, sin BD real).
- Curación: marcar descartado es idempotente y no degrada verificado (RN-001).
- Invariante: sin sub-sector/actividad → comportamiento actual (no romper otros sectores).
- E2E slow (marcado): re-correr Alpina y verificar que la lista anclada mejora (pares lácteos > ruido).

## DONE
1. Competidores de Cap 2 relevantes al sector real (menos industria ajena/ruido, más pares reales).
2. Gate verde (≥464 + nuevos). 3. 1 commit atómico por tarea. 4. Roadmap/PROPUESTA/memoria
   actualizados (DT-061). 5. E2E de verificación (Alpina) con números antes/después. 6. Decidir
   siguiente ventana (DT-060 reingesta A/B para el techo de evidencia, o HITL F24/F25 curación).

## REGLAS DURAS (checklist)
- [ ] ¿Anclaje por actividad/sub-sector real, no por industry group grueso?
- [ ] ¿Filtro de relevancia excluye medios/métricas/industria ajena? ¿Ordena por relevancia?
- [ ] ¿Curación con provenance + estado (RN-001, no degrada verificado)? ¿Sin fabricar?
- [ ] ¿Invariante: sectores sin actividad definida = comportamiento actual?
- [ ] ¿Migración idempotente en esquema propio? ¿Sin down -v? ¿Sin reingesta (eso es DT-060)?
- [ ] ¿Gate verde (ruff 0 + pytest -m "not slow") tras cada commit?

## LECTURAS OBLIGATORIAS
- docs/decisions/FASE25_HALLAZGOS.md §1 (Revisión del usuario) + §2 (este prompt).
- docs/architecture/PROPUESTA_KNOWLEDGE_BASE.md §1 (KB entidades) + §1.4 (anclaje/relevancia) +
  PROPUESTA_BASE_EMPRESAS.md (DT-050, base de empresas para sembrar pares reales).
- docs/decisions/FASE24_HALLAZGOS.md (cierre DT-056: stoplist, señal competidor/publisher/ruido).
- Código: domain/use_cases/generate_benchmarking.py (_identificar_entidades, kb_competidores) +
  generate_n1.py _fn_cap2; data/repositories/entidad_repo.py (list_competidores_by_sector);
  domain/kb/aggregate.py (señal/stoplist); shared/constants/gics_groups.py (extract_gics_code);
  domain/chains/chain_02_gics.py + chain_02b_entidades.py.
- memory: project_fase25_dt059_estado, project_fase24_dt056_estado, project_kb_entidades_plan,
  feedback_extract_gics_code, roadmap.

## CIERRE DOCUMENTADO
FASE26_HALLAZGOS.md con AVANCES/RETOS/RECOMENDACIONES + números (lista anclada antes/después por
sector, % ruido/industria ajena eliminado, pares reales añadidos). Sincronizar ROADMAP (DT-061 →
estado) y PROPUESTA §1.4. Mergear a develop --no-ff tras aprobación. Dejar el prompt de la
siguiente ventana con esta MISMA estructura.
```
