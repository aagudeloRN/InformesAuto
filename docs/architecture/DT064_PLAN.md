# DT-064 — Fichas de competidores ancladas y enriquecidas + persistencia + anti-variabilidad

> Plan de trabajo (propuesto 2026-07-31, para ejecutar mañana). Nace del E2E de Alpina con
> self-review: el conjunto de competidores ya es correcto (DT-063, lácteos), pero **las fichas
> escritas no lo usan** (salen Bavaria/BAT desde el RAG). Ver `FASE30_DT063_HALLAZGOS.md`.

## Problema (diagnóstico validado en el E2E)

1. **La síntesis del Cap 2 escribe las fichas desde el RAG** (`{retrieval_competidores}`), no desde la
   lista anclada. El RAG contiene cerveza/tabaco (queries genéricas de sector "Alimentos, bebidas y
   tabaco líderes globales"). El anclaje DT-063 guía la identificación de entidades + búsqueda
   dirigida, pero el prompt final NO recibe la lista de globales como sujetos obligatorios → el LLM
   elige del RAG contaminado. (Los locales SÍ reciben `{jugadores_locales}` desde DT-050, pero sin
   forzar que sean LAS fichas.)
2. **El self-review re-sintetiza sin el anclaje**: `review_web_cap` (`self_review_hooks.py`) regenera
   con `revise_chain` y **no recibe** `kb_competidores`/`jugadores_locales` → al rescatar reescribe
   desde RAG (volvieron Bavaria/BAT).
3. **Tenemos nombres, no datos**: las fichas se re-buscan cada corrida; los campos (país, ingresos,
   productos, cuota) no se extraen ni se persisten → no hay memoria ni reuso sectorial.
4. **Variabilidad del modelo**: el LLM gratuito a veces rehúsa ("con las fuentes proporcionadas no es
   posible…"). No hay detector; el self-review ayuda pero re-sintetiza mal (causa 2).

## Objetivo

Que las fichas de 2.1.1/2.1.2/2.1.3 sean sobre las empresas **ancladas** (correctas), con **datos**
reales cuando existan, **persistidos** para reuso, y con la **redacción estable** (anti-negativas).

## Tareas propuestas (afinar en Plan Mode)

- **T1 — Anclar los SUJETOS de las fichas (no solo enriquecer RAG).** Pasar al prompt de benchmarking
  (`chain_03_benchmarking`) la lista explícita de globales anclados (`kb_competidores`) como los
  actores obligatorios de "Referentes Globales", además del `{jugadores_locales}` que ya existe para
  regionales/startups. Instrucción dura: las fichas de 2.1.1 son EXACTAMENTE estas empresas; usar el
  RAG solo para llenar sus campos, no para elegir otras. Elimina Bavaria/BAT por construcción.
- **T2 — Self-review anclaje-aware.** `review_web_cap` debe recibir y reinyectar
  `kb_competidores`/`jugadores_locales` (y el bloque de sujetos) en la re-síntesis del Cap 2, para que
  el rescate no revierta a RAG. (Hoy `review_web_cap` ya acepta `kb_competidores` para la búsqueda;
  falta pasar los sujetos al prompt de re-síntesis.)
- **T3 — Extraer y PERSISTIR datos de ficha por competidor.** Tras (o durante) benchmarking, parsear
  los campos de cada ficha (país, ingresos, portafolio, cuota, propuesta de valor) → `entidad_atributos`
  del competidor con provenance (candidato). Idempotente. El próximo informe del sector reusa: nombres
  anclados + ficha pre-llena. Reusar el patrón DT-056 (atributos por entidad).
- **T4 — Pre-fill del prompt desde el KB.** Inyectar como contexto estructurado los datos de ficha ya
  conocidos del KB (como `{jugadores_locales}`) → el LLM escribe DESDE hechos, menos fabricación y
  menos negativas. Cierra el ciclo: cada corrida enriquece; la siguiente parte de más.
- **T5 — Detector de negativas/ausencia.** Predicado puro que detecte respuestas de rechazo del LLM
  ("lo siento, no es posible", "no se puede determinar", capítulo casi todo "Dato no disponible") →
  tratarlo como fallo (como `has_cjk_characters`): forzar retry / escalar de modelo, no emitir.

## Verificación / DONE

- Puros con fixtures: parser de campos de ficha; detector de negativas.
- E2E Alpina (lácteos) con `anclaje_local_enabled + discover_globales_enabled + selfreview_enabled`:
  2.1.1 = Danone/Kellogg's/Fonterra/… (0 cerveza, 0 tabaco); 2.1.2 = Colanta/Alquería; fichas CON
  datos; atributos persistidos en el KB (verificable por consulta); re-corrida reusa (menos búsquedas).
- **E2E en un SEGUNDO SECTOR distinto de alimentos/lácteos** (obligatorio, para no sesgar la
  validación hacia food). Candidatos: banca (p. ej. `Bancolombia`, GICS 4010), automotor (`Sofasa`,
  2510), software (`Sofka`, 4510) o energía (`Ecopetrol`, 1010). Confirmar que en ESE sector: los
  globales anclados son del dominio correcto (no food), las fichas los usan (0 ajenos), y los
  locales/startups del directorio salen re-rankeados por producto. El mecanismo es genérico (DT-063
  no es food-specific) — este E2E lo demuestra y evita bias.
- Confirmar además la disjunción por sub-actividad dentro de 3020: cervecera y tabacalera (pendiente
  de DT-063).
- Gate: ruff 0, `pytest -m "not slow"` verde.

## Estado del repo al cerrar hoy (2026-07-31)

Rama `develop`. Últimos commits de la sesión (orden cronológico):
- `f9b159b` fix(dt050) índice nombre+sector parcial · `c445b95` docs(dt050b)
- `082ed82` feat(dt063) T1 productos · `1de8560` feat(dt063) T2+T3 motor · `731275c` fix(dt063) cableado
  · `8a9b914` docs(dt063) · `feat(dt063) NurtureKB quick-win`
- (docs de cierre de hoy, este commit)

Directorio local sembrado en BD: ~98k EmpresasColombia + 388 StartIA + backfill entidad_sectores.
KB globales 3020: mezcla previa sin `productos_perfil` (se auto-sanan al descubrir). Alpina guardada
por NurtureKB (`alcance=local` + `productos_perfil`). Deuda viva: **DT-050b** (reconciliación
EMIS↔NER + HITL, y migrar el path global al JOIN `entidad_sectores`).

---

## PROMPT DE ARRANQUE — ventana limpia (mañana)

> ROL: Eres Claude Code, ingeniero de InformesAuto (`~/Test/InformesAuto`): informes de inteligencia
> competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas). Lee primero
> `docs/architecture/DT064_PLAN.md` y las memorias `project_dt064_plan`, `project_fase30_dt063_estado`,
> `feedback_discovery_producto_driven`.
>
> CONTEXTO: DT-050 (directorio local EMIS+StartIA) y DT-063 (descubrimiento de competidores guiado por
> **producto/servicio**, retira el sub-código GICS como driver) están CERRADOS en `develop`. El
> conjunto de competidores anclados ya es correcto (E2E Alpina: globales lácteos Danone/Kellogg's/
> Fonterra, 0 tabaco). El self-review (DT-059) rescata capítulos (Cap 2 6→11) pero **re-sintetiza sin
> el anclaje** y la síntesis escribe las fichas desde el RAG contaminado → en el .docx salen Bavaria
> (cerveza) y British American Tobacco (tabaco) en 2.1.1.
>
> HOY EJECUTAS **DT-064** (Plan Mode obligatorio): fichas de competidores **ancladas** (los sujetos de
> 2.1.1/2.1.2/2.1.3 son la lista anclada, no lo que surge del RAG) + **enriquecidas y persistidas**
> (extraer país/ingresos/portafolio/cuota → `entidad_atributos`, reuso sectorial + pre-fill del prompt)
> + **anti-variabilidad** (detector de negativas → retry/escala; self-review anclaje-aware). Tareas
> T1–T5 en `DT064_PLAN.md`.
>
> RESTRICCIONES (CLAUDE.md TIER 1): sin nombres de modelo en código; wrappers en `infrastructure/`;
> migraciones idempotentes `ensure_*`, nunca `down -v`; provenance + candidato/verificado (RN-001);
> **nunca `git add -A`** (respetar `documentos_sectoriales/FuentesExternas/` sin trackear); Plan Mode
> para lo no trivial; 1 commit atómico por tarea; gate ruff 0 + `pytest -m "not slow"`.
>
> ARCHIVOS CLAVE: `domain/chains/chain_03_benchmarking.py` (slot `{jugadores_locales}` ya existe →
> añadir sujetos globales), `domain/use_cases/generate_benchmarking.py`, `domain/use_cases/
> self_review_hooks.py` (review_web_cap — pasar sujetos a la re-síntesis), `domain/use_cases/
> generate_n1.py` (cableado), `data/repositories/entidad_repo.py` (persistir/leer atributos de ficha),
> `shared/text_productos.py`, `domain/kb/relevance.py`. E2E: `scripts/run_pilot.py --empresa "Alpina
> Productos Alimenticios S.A." --ciiu 1040` con los 3 flags. Confirmar disjunción con cervecera y
> tabacalera. **IMPORTANTE (usuario 2026-07-31):** el E2E de validación NO puede ser solo Alpina —
> correr también un **segundo sector no-alimentos** (p. ej. Bancolombia/4010, Sofasa/2510, Sofka/4510
> o Ecopetrol/1010) para asegurar que el mecanismo es genérico y no hay sesgo hacia food/lácteos.
> Sucesor vivo: **DT-050b** (reconciliación + HITL).
