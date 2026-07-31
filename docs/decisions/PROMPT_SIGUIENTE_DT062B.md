# Prompt de arranque — DT-062b (reuso de globales por sub-actividad)

> Pegar como primer mensaje de una ventana limpia. Misma estructura que el prompt DT-062.
> Secuencia: **DT-062b (esta) → DT-050 (base Colombia local, prompt en `PROMPT_SIGUIENTE_DT050.md`) → DT-060**.

## ROL
Eres Claude Code, ingeniero del proyecto InformesAuto (~/Test/InformesAuto): informes de
inteligencia competitiva (RAG local pgvector + Ollama, LangChain, arquitectura por capas). DT-062
(descubrimiento LLM de competidores globales corroborado por web) está CERRADO y MERGEADO a develop
(merge `45ba54d`): el tier de clase mundial (2.1.1) recibe globales recomendados por LLM y
corroborados por web (`chain_02c_pares_globales`, `domain/kb/corroboracion.py` con match por núcleo,
`DiscoverGlobales`, flag `discover_globales_enabled` default-OFF, `scripts/descubrir_globales_llm.py`).
Gate: ruff 0 (src/ tests/), 518 fast tests.

Hoy ejecutas DT-062b — REUSO DE GLOBALES POR SUB-ACTIVIDAD (no por grupo). Rama nueva
`feature/fase28-dt062b` desde develop.

## PROBLEMA / OPORTUNIDAD
El reuso de DT-062 es hoy **por grupo GICS (3020), no por sub-actividad**: una empresa de **tabaco**
(302030) vería globales de **lácteos/bebidas**. Verificado empíricamente (food 302020 / beverage
302010 / tobacco 302030 devuelven la MISMA lista). Dos causas raíz:

1. **Mal etiquetado al sembrar.** `_descubrir_globales` (en `generate_n1`) y el script siembran TODOS
   los globales del LLM con el `sub_gics` de la empresa analizada, aunque el LLM (al recibir el código
   crudo `302020` + el nombre del grupo completo) recomiende bebidas/tabaco. → Heineken/Tyson quedan
   etiquetados food.
2. **`verificado` puentea el filtro de sub.** En `domain/kb/relevance.py::filter_rank_competidores`,
   la cláusula `verificado OR sub_gics == sub_gics` deja pasar cualquier `verificado` sin importar su
   sub. Como todo lo sembrado es `verificado`, tabaco ve food.

Objetivo: que el ancla 2.1.1 dé globales de la MISMA sub-actividad que la empresa analizada, se
descubra **una vez por sub-actividad** (no por grupo), y no se re-descubra para empresas similares.

## RESTRICCIONES (CLAUDE.md TIER 1 + TIER 2)
- Sin nombres de modelo en código (ADR-002). domain/ no importa SQLAlchemy/httpx. BD compartida:
  esquema propio, migración idempotente `ensure_*`, NUNCA `down -v`. RN-001: provenance + estado.
- **PLAN MODE obligatorio + Chesterton's Fence:** DT-062b toca una **regla cerrada de DT-061** (el
  puente `verificado` sobre el filtro de sub). Entender por qué existe (curados sin sub deben mostrar)
  antes de cambiarla; documentar la decisión. NUNCA `git add -A` (respetar
  `documentos_sectoriales/FuentesExternas/` sin trackear).

## TAREAS (afinar en Plan Mode)
T1 — **Etiqueta legible de sub-actividad al prompt.** Mapa puro `sub_code → label`
  (`302020→"alimentos procesados y lácteos"`, `302010→"bebidas"`, `302030→"tabaco"`) en
  `shared/constants/gics_groups.py` (junto a `resolve_sub_gics`). `chain_02c_pares_globales` recibe la
  **etiqueta**, no el código crudo (hoy pasa `sub_gics or "general"`). Así el LLM recomienda los
  globales de esa sub.
T2 — **Filtro sub-estricto para el tier global.** En `filter_rank_competidores`: cuando `alcance` está
  pedido (tier de clase mundial) y hay `sub_gics` resuelto, exigir match de sub (sin puente
  `verificado`). Decidir en Plan Mode: ¿el fallback "si no hay relevantes, conserva grupo" debe
  DESACTIVARSE en el tier global? (Sí probablemente: mejor ancla vacía que sub ajena → el guard
  dispara el descubrimiento de esa sub). Verificar que NO rompe los tests DT-061 (ya comprobado: sus
  `verificado` tienen el sub correcto).
T3 — **Guard + siembra por sub.** El guard de coste (`generate_n1._fn_cap2`) ya consulta por
  `sub_gics`; con el filtro estricto, cada sub-actividad dispara su propio descubrimiento una vez.
  Confirmar que el tag al sembrar (sub de la empresa analizada) ya es veraz gracias al steering de T1.
T4 (verificación) — Re-siembra E2E por sub (food/beverage/tobacco) demostrando aislamiento: tabaco NO
  ve lácteos; cada sub tiene su propia lista; re-run idempotente. Purgar la verificación al cerrar
  (como en DT-062).

## PRUEBAS POR TAREA (gate = ruff 0 + pytest -m "not slow")
- Mapa sub→label puro (fixtures). `filter_rank_competidores` sub-estricto: tabaco/302030 con solo
  globales food/302020 devuelve **[]** (o cae a grupo si así se decide), no lácteos. Invariante food:
  una empresa food sigue viendo food. Sin romper los tests DT-061 existentes.
- Invariante flag OFF (DT-061b) intacto.

## DONE
1. El ancla 2.1.1 reusa por sub-actividad: tabaco no ve lácteos. 2. Se descubre una vez por sub, no
por grupo. 3. Gate verde. 4. 1 commit atómico por tarea. 5. Docs (FASE28_HALLAZGOS + ROADMAP +
PROPUESTA §1.4 + memoria). 6. Merge `--no-ff` tras aprobación. 7. Dejar prompt de la siguiente
ventana (DT-050) — ya existe en `PROMPT_SIGUIENTE_DT050.md`, revalidarlo.

## LECTURAS OBLIGATORIAS
- `docs/decisions/FASE27_HALLAZGOS.md` (§ "Limitación detectada → DT-062b" + "Persistencia y reuso").
- Código: `domain/kb/relevance.py` (`filter_rank_competidores` — la regla a tocar),
  `domain/chains/chain_02c_pares_globales.py` (prompt, `{sub_actividad}`),
  `domain/use_cases/discover_globales.py` + `generate_n1.py::_descubrir_globales` (siembra/guard),
  `data/repositories/entidad_repo.py::list_competidores_by_sector`,
  `shared/constants/gics_groups.py` (`resolve_sub_gics`, dónde añadir el mapa de etiquetas),
  `shared/data/pares_sectoriales.py` (semilla curada, sub-tags).
- memory: `project_fase27_dt062_estado`, `project_fase26_dt061_estado`, `feedback_extract_gics_code`,
  `feedback_modelos_llm`.

## CIERRE DOCUMENTADO
`FASE28_HALLAZGOS.md` con AVANCES/RETOS/RECOMENDACIONES + números (ancla por sub food/beverage/tobacco
tras el fix: listas distintas, aislamiento verificado). Sincronizar ROADMAP + PROPUESTA §1.4. Merge a
develop `--no-ff` tras aprobación. Dejar/validar el prompt de DT-050 (base Colombia local + startia).
