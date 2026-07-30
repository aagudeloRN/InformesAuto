# Fase 24 — Hallazgos y cierre

> KB de entidades (DT-056): merge/verificación sobre el sustrato `entidad_menciones` poblado por
> DT-057. Rama `feature/fase24-dt056` desde `develop` (base `490dd77`). Gate final: **ruff 0
> (src/ tests/), 438 fast tests** (412 base + 26 nuevos), 2 skipped. Sin reingesta, sin re-embeber,
> sin `down -v`.

## §1 — DT-056: KB de entidades (cerrado 2026-07-30)

Consolida el sustrato ruidoso (59.647 menciones candidatas, 20.430 distintas, 25 sectores) en un KB
de entidades canónicas con provenance por campo y gate candidato/verificado (RN-001), y lo cablea
en el pipeline de Cap 2 para anclar la lista de competidores antes de buscar (cierra causas A/E/D
del diagnóstico F22).

### AVANCES (con números)

**T1 — Entidad canónica + atributos con provenance (`b5abd15`).**
- Tablas `entidades` (dedup por NIT o `(nombre_normalizado, sector_gics)`, `aliases` JSONB,
  contadores de señal, estado candidato/verificado) y `entidad_atributos` (un atributo por fila con
  procedencia: `fuente`, `confianza`, `documento_id`, `estado`). Migración `ensure_entidades_tables`
  idempotente en esquema propio.
- `EntidadRepository`: `upsert_entidad` idempotente y **no degrada estado** (verificado nunca baja a
  candidato), fusiona `aliases` (unión); `add_atributo` idempotente por `(entidad, clave, fuente)`
  (una valor actual por fuente → prioridad de conflicto usuario>emis>web resuelta en consulta, sin
  borrar lineage); `list_competidores_by_sector` (excluye `descartado`, ordena por señal).

**T2 — Agregador puro + merge (`8f8440e`).**
- `domain/kb/aggregate.py` (puro, testeable): agrupa por `nombre_normalizado`, cuenta menciones /
  chunks distintos / sectores, elige sector dominante y forma display (variantes → `aliases`), y
  clasifica una **señal**: `competidor` vs `publisher` vs `ruido`. Heurística documentada:
  dispersión cross-sector (≥8 sectores) + **stoplist curada** de fuentes/editores (Fitch,
  Euromonitor, MarketLine, OECD, IMF, TBRC, DANE, Deloitte, Mapfre, Infiniti…) por token de marca o
  nombre completo, + geografías/genéricos + fragmentos de título de informe + acrónimos. RN-001:
  solo consolida lo presente; no fabrica ni fusiona sin evidencia.
- `scripts/merge_kb_entidades.py`: agrega **global** (el umbral publisher depende de la dispersión
  cross-sector) y persiste solo los `competidor` con atributo `origen_ner` (lineage, candidato).
  `--dry-run`, `--sector`, `--min-sectores`.
- **Corrida real en BD:** 59.647 menciones → 20.430 consolidadas = **17.258 competidor + 700
  publisher + 2.472 ruido**. Persistidos: **17.258 entidades** (estado candidato) + 17.258 atributos
  `origen_ner`. **Re-ejecución = 0 nuevas** (idempotencia verificada: 17.258 → 17.258).

**T3 — Anclaje de competidores en Cap 2 (`9b9c41b`).**
- `GenerateBenchmarking` acepta `kb_competidores`: la lista canónica del KB por sector **lidera** la
  búsqueda dirigida por entidad y se completa con lo que el LLM ancla en evidencia (dedup casefold,
  cota `MAX_ENTIDADES`). `None`/`[]` = **comportamiento B1 idéntico** (invariante testeado).
- `generate_n1._fn_cap2` consulta el KB con sesión propia por thread; si falla, cae a B1 (el KB es
  un boost, nunca rompe la corrida). RN-001 intacto: los nombres del KB provienen de evidencia y
  `chain_02b` sigue exigiendo presencia en evidencia (y excluye fuentes/genéricos) para el texto.
- **Anclaje real por sector (top-8):** sector **2510 (autos) limpio** — Toyota, Renault, Hyundai,
  Volkswagen, Mazda, General Motors, Nissan; sector **3020 (alimentos) decente** — Postobón, FEMSA,
  Coca-Cola, Fedepalma (+ ruido). Sectores 1010/4020 aún ruidosos (ver RETOS).

**T4 — Base viva (`7ba31cd`).**
- `NurtureKB`: cada corrida hace upsert de la empresa principal como entidad `tipo='empresa'`
  `estado='verificado'` (identidad pedida por el usuario → prioridad usuario) + descripción (web/LLM)
  como atributo `candidato` con procedencia. Idempotente. Enganchado en `generate_informe._run_n0`
  con fallo suave. Cierra la causa D (sin memoria entre corridas): la empresa de hoy = competidor
  anclado de mañana. (Se ejercita en corridas reales; `verificadas=0` en BD hasta la primera corrida
  post-merge.)

### RETOS / lecciones

- **La dispersión cross-sector sola no basta.** Casas de análisis concentradas en pocos sectores
  (IEA↔energía, Euromonitor↔consumo, Fitch, CEPAL, Mapfre) no superan el umbral de 8 sectores → se
  añadió una **stoplist curada** (tokens de marca + nombres completos). Subió publishers filtrados
  de 130 (solo dispersión) a **700**. Es curación honesta (no invención), consistente con el prompt
  de `chain_02b`.
- **Ruido residual de frases genéricas** en el anclaje de algunos sectores ("Oil & Gas", "Data
  Table", "Group", "Food and Beverage Industry News", "Profit perEmployee"). Origen: el NER crudo
  etiquetó como ORG títulos de sección, métricas OCR-pegadas y sustantivos de sector. **Contención
  por diseño (RN-001):** entran como `candidato`, y el `chain_02b` de generación filtra a evidencia
  y excluye fuentes/genéricos/productos → no llegan al texto como hechos. **No se persiguió
  perfección con listas estáticas** (whack-a-mole sin fin); la limpieza fina es curación humana
  (HITL F24/F25) y mejor extracción (DT-060: tablas/estructura/layout).
- **Ambigüedad marca/empresa/persona:** el sustrato es ORG-only sin NIT → la reconciliación se
  resolvió por nombre normalizado + captura de `aliases` (variantes superficiales). La
  reconciliación por NIT/ciudad con la base DT-050 queda como gancho (columnas listas en el modelo).

### RECOMENDACIONES

1. **Curación HITL del KB (F24/F25):** promover a `verificado` los competidores reales por sector y
   marcar `descartado` el ruido residual. El gate y `list_competidores_by_sector` ya lo respetan.
2. **Boost/relajar el gate de anclaje cuando el retrieval es delgado:** hoy el anclaje solo actúa si
   el retrieval inicial es suficiente (B1-invariante conservador). El mayor valor del KB es cuando la
   evidencia local es pobre → evaluar anclar incluso ahí (los nombres del KB ya están pre-anclados).
3. **DT-060 (reingesta gated A/B):** preservar tablas/cifras EMIS y metadata posicional mejoraría la
   calidad del NER (menos frases genéricas) — solo si un A/B en 1 sector lo justifica.
4. **UI de captura manual** (PROPUESTA §5): staging `fuente="manual"` → validación/dedup/merge; el
   modelo de entidad ya está listo.

### Verificación

- `uv run ruff check src/ tests/` → 0.  `uv run pytest -m "not slow" -q` → **438 passed, 2 skipped**.
- Merge idempotente en BD real: 0 → 17.258 (1ra), 17.258 → 17.258 nuevas=0 (2da). Sin tocar vectores.
- Anclaje verificado por `list_competidores_by_sector` en 4 sectores (2510 limpio).

---

## §2 — Prompt de arranque de la siguiente ventana

El usuario decide entre **DT-059 (loop de auto-revisión)** y **DT-060 (reingesta RAG gated por A/B)**.
Recomendación: **DT-059** — el juez/rúbrica (T22.7/F20) y `eval_gate` ya están sólidos, y cierra el
lazo de calidad por-nodo; DT-060 es más caro y gated por A/B.

### (Opción recomendada) Prompt — DT-059: loop de auto-revisión (Reflection/Reflexion por-nodo)

```
## ROL
Eres Claude Code, ingeniero de InformesAuto (~/Test/InformesAuto): inteligencia competitiva (RAG
local pgvector + Ollama, LangChain, capas). DT-056 (KB de entidades) está CERRADO y mergeado
(rama feature/fase24-dt056): entidades canónicas con provenance + estado candidato/verificado;
17.258 competidores consolidados (700 publishers + 2.472 ruido filtrados); anclaje cableado en
Cap 2 (B1-invariante); base viva (NurtureKB). Gate base: ruff 0, 438 fast tests.

Hoy ejecutas DT-059 — loop de auto-revisión (extiende T22.7/DT-048). Rama nueva
`feature/fase25-dt059` desde develop (tras mergear DT-056).

## RESTRICCIONES (CLAUDE.md TIER 1)
- Sin nombres de modelo en código (config/.env/routing, ADR-002). domain/ no importa
  SQLAlchemy/httpx/Streamlit; librería externa por wrapper en infrastructure/. Sin credenciales.
  Evaluador OpenRouter/Nemotron (Ollama fallback), nombres en config.
- Cambios atómicos: 1 commit por tarea, gate verde tras cada uno (ruff 0 + pytest -m "not slow").
  Plan Mode.

## TAREAS (afinar en Plan Mode)
T1 — Grafo cíclico por-nodo: generar → juez con rúbrica v1.0 → revisar → repetir. Guardar el MEJOR
  (rúbrica-scored), no el último. Parada: score≥umbral O sin mejora O 3 iteraciones. Selectivo:
  solo el cap que no pasa el gate.
T2 — Dos sabores: caps web RE-BUSCAN en el loop (Reflexion con herramientas: el juez pide un dato
  faltante → búsqueda dirigida por entidad, reusa el anclaje del KB); caps de integración solo
  RE-SINTETIZAN. Por-nodo dentro de UNA corrida (no mezclar caps de corridas → coherencia; Cap6
  sintetiza 2/3/4/5).
T3 — Evaluador OpenRouter/Nemotron (config), Ollama fallback. Rúbrica v1.0 (F20) + eval_gate ya
  existen. Persistir score/iteraciones por cap (trazabilidad BD).

## LECTURAS OBLIGATORIAS
- docs/architecture/PROPUESTA_KNOWLEDGE_BASE.md §4 (auto-revisión) + Fuentes (Reflexion/LangGraph).
- docs/decisions/FASE24_HALLAZGOS.md (este cierre). Rúbrica F20, eval_gate (F15/F16), T22.7.
- memory: project_kb_entidades_plan, project_fase24_dt056_estado.

## DONE
1. Loop por-nodo, guardar-el-mejor, selectivo, máx 3 iter. 2. Gate verde (≥438 + nuevos). 3. 1
   commit atómico por tarea. 4. Roadmap/memoria actualizados. 5. Decidir siguiente ventana.

## REGLAS DURAS
- [ ] ¿Por-nodo en UNA corrida (no full-report×3-cherry-pick)?
- [ ] ¿Guardar el mejor por rúbrica, no el último? ¿Selectivo (solo el cap que falla)?
- [ ] ¿Evaluador en config (sin nombre de modelo en código)? ¿Gate verde tras cada commit?
```

### (Alternativa) DT-060 — reingesta RAG gated por A/B
Metadata posicional, chunking estructural, tablas/cifras EMIS, doc-summary vector, (tras benchmark)
embedder. Regla dura: cambiar pipeline → reingerir 1 sector → A/B con `eval_retrieval.py` → escalar
solo si sube precisión + mix. Mejoraría la calidad del NER (menos ruido genérico en el KB). Más caro.
