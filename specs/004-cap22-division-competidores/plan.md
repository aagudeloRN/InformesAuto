# Implementation Plan: Cap 2.2 — División de Competidores (Grupos Estratégicos)

**Branch**: `spec-driven-experiment` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Módulo independiente para el Subcapítulo 2.2 del informe de Inteligencia Competitiva. Genera una matriz 2×2 de grupos estratégicos clasificando exhaustivamente los competidores de Cap 2.1, con síntesis de presión competitiva. Grounding estricto: lista cerrada de empresas, sin alucinación.

## Summary

Cap 2.2 es un nodo N1 analítico que consume el output estructurado de Cap 2.1 (`Cap21Jugadores`) y el contexto de Cap 1 (`DescripcionEmpresa`) para producir una matriz de grupos estratégicos 2×2 + síntesis narrativa. El LLM clasifica; un validador determinista post-generación garantiza la lista cerrada. El módulo sigue el patrón `chain → use_case → assembler → tipos` de Cap 2.1 y se integra en el DAG de N1 sin romper el flujo existente.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: LangChain Core (LCEL), SQLAlchemy (vía wrapper existente), OpenRouter (inyectado como `llm` desde config)

**Storage**: PostgreSQL / esquema `informes_ic` — tabla `capitulos_checkpoint` vía `CheckpointRepository` existente

**Testing**: pytest con `_FakeSession` y stubs del LLM (patrón existente)

**Target Platform**: Linux server (WSL2 en dev, Docker en producción)

**Project Type**: Módulo de dominio dentro de un pipeline de generación de informes

**Performance Goals**: Generación de sección 2.2 en < 60 segundos para datasets de hasta 30 competidores

**Constraints**: Modelo LLM de config (nunca hardcodeado); sin retrieval adicional (usa datos ya en memoria de 2.1); checkpoints de Cap 1 y 2.1 inmutables durante la ejecución

**Scale/Scope**: 5-30 competidores por informe; 1-3 regeneraciones por sesión de revisión

## Constitution Check

*GATE: Evaluado contra constitución v1.0.0 antes de Phase 0.*

| Principio | Evaluación | Acción requerida |
|-----------|-----------|-----------------|
| **I. SoC** | ✅ PASS — chain en `domain/chains/`, use_case en `domain/use_cases/`, assembler puro en `domain/kb/`, tipos en `shared/types.py`. Ningún módulo > 300 líneas esperado. | Ninguna |
| **II. Agnosticismo de dependencias** | ✅ PASS — LLM inyectado como dependencia; ningún import de `langchain` en `domain/` directamente (se inyecta el objeto ya construido desde la capa de infraestructura). | Ninguna |
| **III. Integridad del dato** | ✅ PASS — lista cerrada inyectada en el prompt + validador post-gen + regla de datos ausentes si Cap 2.1 vacío. El gate anti-envenenamiento RN-001 aplica por herencia (los datos vienen del KB ya validado de 2.1). | Ninguna |
| **IV. Sin credenciales ni hardcode** | ✅ PASS — modelo leído de config; `check-hardcoded-models.sh` bloqueará si se escapa algún nombre de modelo. | Ninguna |
| **V. Calidad / Tests** | ✅ PASS — tests en el mismo PR (6 escenarios mínimo, ≥80% cobertura en domain/). | Ninguna |
| **VI. Cambios atómicos** | ✅ PASS — se añade `cap_22_division` a `InformePiloto` como `Optional` con default `None`; no rompe código existente. | Ninguna |

**Resultado**: VERDE — no hay violaciones ni justificaciones pendientes.

*Re-check post-Phase 1*: arquitectura confirmada en `data-model.md`; todos los principios siguen cumplidos.

## Project Structure

### Documentation (this feature)

```text
specs/004-cap22-division-competidores/
├── plan.md              # Este archivo
├── research.md          # Phase 0 — decisiones de diseño
├── data-model.md        # Phase 1 — entidades y contratos de entrada/salida
├── quickstart.md        # Phase 1 — guía de validación E2E
├── contracts/
│   └── markdown-output.md   # Contrato de formato de la sección 2.2
└── tasks.md             # Phase 2 output (/speckit-tasks — pendiente)
```

### Source Code (repository root)

```text
src/ic/
├── shared/
│   └── types.py                          # MODIFICAR: añadir CuadranteKey, ClasificacionCompetidor,
│                                         #   Cap22Division; modificar InformePiloto
├── domain/
│   ├── chains/
│   │   └── chain_cap2_22_division.py     # CREAR: cadena LLM (prompt + parser JSON)
│   ├── use_cases/
│   │   ├── generate_22_division.py       # CREAR: orchestrator (validate → chain → validate → persist)
│   │   └── generate_n1.py                # MODIFICAR: añadir Generate22Division al executor
│   └── kb/
│       └── seccion22_assembler.py        # CREAR: assembler determinista (JSON → markdown + validación)
└── (infrastructure/: sin cambios — LLM wrapper existente se reutiliza sin modificación)

tests/
└── test_generate_22_division.py          # CREAR: 6+ escenarios unitarios

docs/prompts/
└── prompt-02b-division-competidores.md  # CREAR: documentación del prompt
```

**Structure Decision**: Single-project, layout existente. Todos los archivos nuevos siguen el patrón de Cap 2.1. Sin nuevas dependencias externas.

## Complexity Tracking

> No hay violaciones de constitución. Tabla vacía.

---

## Flujo de ejecución

```
generate_n1.py (ThreadPoolExecutor)
        │
        ├── Generate22Division.__call__(run_key, cap21, empresa, feedback=None)
        │         │
        │         ├── [guard] cap21.retrieval_suficiente?
        │         │     NO → return Cap22Division(texto=ABSENT_PARAGRAPH, retrieval_suficiente=False)
        │         │
        │         ├── build_closed_list(cap21) → list[str]
        │         │
        │         ├── chain_cap2_22_division.invoke({closed_list, fichas, empresa, feedback})
        │         │     └── LLM → JSON {cuadrantes, intro, sintesis_incumbente, sintesis_entrante}
        │         │
        │         ├── parse_llm_json(raw) [retry x2 si malformado]
        │         │
        │         ├── validate_closed_list(parsed, closed_list)
        │         │     → warnings_nombres_ajenos: list[str]
        │         │     → cuadrantes filtrados (nombres ajenos eliminados)
        │         │
        │         ├── seccion22_assembler.assemble(parsed, closed_list)
        │         │     → markdown: str  [+ CoverageError si falta alguna empresa → retry o ausencia]
        │         │
        │         ├── CheckpointRepository.save_capitulo(run_key, "cap_2_2", payload)
        │         │
        │         └── return Cap22Division(texto, clasificaciones, n_empresas, ...)
        │
        └── [otros N1: cap3, cap4, cap5 en paralelo — no afectados]
```

## Decisiones clave

1. **LLM produce JSON, no markdown raw**: el assembler convierte a markdown → parsing robusto.
2. **Closed list injection en el prompt**: el prompt enumera explícitamente las empresas a clasificar, reduciendo la probabilidad de alucinación antes de la validación post-gen.
3. **Validador determinista post-gen**: segunda barrera de seguridad, independiente del prompt.
4. **Retry x2 en JSON malformado**: antes de degradar a ausencia; balance entre resiliencia y costo.
5. **`cap_22_division: Optional` en `InformePiloto`**: backward-compatible; informes generados sin Cap 2.2 siguen siendo válidos.
6. **Assembler puro**: `seccion22_assembler.py` no tiene I/O; solo transforma datos — fácil de testear en aislamiento.
