# Auditoría de Arquitectura — Sistema de Informes IC
## Versión 2 — Incorpora `docs/decisions/` FASE0 a FASE28

**Auditor:** Antigravity / Senior Software Architect
**Fecha:** 2026-08-03  
**Base de análisis:** Commit activo en `develop` (Fase 30, DT-063 cerrado)
**Alcance:** `src/ic/`, `docs/`, `tests/`, `CLAUDE.md`, `PRIME DIRECTIVE.md`, ADR-001–015, FASE0–FASE30 hallazgos

---

## Impacto de leer `docs/decisions/`

> [!IMPORTANT]
> La primera versión de esta auditoría **no leyó sistemáticamente `docs/decisions/`** (FASE0 a FASE28). Solo se usó FASE28 más el ROADMAP como proxy del historial. Los hallazgos que siguen **corrigen y precisan** las conclusiones anteriores en 6 puntos críticos.

### ¿Qué cambia respecto a la v1?

| Punto | v1 (sin decisions/) | v2 (con decisions/) |
|---|---|---|
| Violación SoC en `presentation/` | ⚠️ Menor — solo `_check_services` hace HTTP | 🔴 **Mayor** — `app.py` importa `SessionLocal` + repositorios en 3 funciones (DT-038 de FASE19, no resuelto) |
| Cobertura `domain/` < 80% | "No re-medida desde Fase 19" | **Confirmada en 69% — es la línea base del proyecto desde FASE19** |
| Deuda del orchestrator 576L | "Regresión no documentada" | **Documentada desde FASE19 (DT-039, 438L → hoy 576L); el plan de extracción `generate_n3.py` existe pero no se ejecutó** |
| DT-042 (LCEL en domain) | "Sin ADR formal" | **Confirmado: DT-042 abierto en FASE19, agendado para F22, finalmente no cerrado formalmente** |
| `gateway.py` 503L y pricing | "Zona gris" | **DT-037/DT-040 de FASE19, agendados para F22; solo se parcheó superficialmente (el split propuesto no se hizo)** |
| Estado HITL | "No implementado" | **Correcto. ADR-015 fiel por diseño; FASE25 implementó solo el self-review loop (selfreview_enabled OFF)** |

---

## 1 — Diagnóstico de Salud Actualizado

| Dimensión | Puntuación | Cambio desde v1 |
|---|---|---|
| Cumplimiento TIER 1 (Reglas Duras) | **82 %** | ⬇️ Baja: `presentation/` accede a `data/` directamente (DT-038, alta) |
| Alineación ADRs (001-015) | **80 %** | ≈ Igual — ADR-009 regresión conocida; ADR-014 doc desactualizado |
| SoC entre capas | **65 %** | ⬇️ Baja: `presentation/` acoplada a `data/` directamente es más grave de lo indicado |
| Cobertura de tests | **69 %** | ⬇️ Confirmada (no estimada): dato real de FASE19, no re-medida |
| Deuda técnica activa | **Alta** | ⬆️ Sube: DT-037 a DT-042 (FASE19) están abiertos o parcialmente cerrados |
| Preparación Fase 9+ | **70 %** | ⬇️ Baja: más deuda activa de la estimada |

**Alineación global revisada: 74 % (antes: 79 %)**

---

## 2 — Correcciones y Precisiones a la Matriz de Inconsistencias

### 2.1 🔴 NUEVA SEVERIDAD — `presentation/app.py` accede directamente a `data/`

**Hallazgo de FASE19 §3.4 (DT-038)** — Elevado de ℹ️ a 🔴

El informe v1 solo detectó que `_check_services()` hace HTTP a Ollama sin wrapper. Pero FASE19 §3.4 ya documentó la violación **real**: `app.py` importa `SessionLocal` y repositorios directamente en 3 lugares:

```python
# app.py:60-61 — _render_repositorio()
from ic.data.database import SessionLocal as _SL
from ic.data.repositories.empresa_repo import EmpresaRepository as _ER

# app.py:132-133 — _render_repositorio()
from ic.data.database import SessionLocal
from ic.data.repositories.documento_repo import DocumentoRepository

# app.py:212-213 — _render_historial()
from ic.data.database import SessionLocal
from ic.data.repositories.informe_repo import InformeRepository
```

**Este es el acoplamiento más grave del sistema**: la capa de presentación (Streamlit) conoce y usa el ORM directamente, violando SoC de forma manifiesta. DT-038 lo registró en FASE19 con destino **F26**, pero F26 no lo cerró (se cerró DT-063 de contenido). **La deuda sigue abierta.**

---

### 2.2 🔴 CONFIRMADO — Cobertura `domain/` en 69% — Dato de FASE19, no estimación

FASE19 §3.3 midió formalmente: `pytest -m "not slow" --cov=src/ic/domain` → **69% (883 stmts, 273 sin cubrir)**. Los módulos sin cobertura real son:

| Módulo | Cobertura | Causa del hueco |
|---|---|---|
| `generate_n1.py` | **0%** | Solo ejercido por E2E `@slow` |
| `generate_informe.py` | **34%** | Orquestación cubierta solo por E2E `@slow` |
| `generate_empresa_description.py` | **40%** | Rama fallback CJK/ausencia |
| `chain_01_descripcion.py` | **47%** | Builder de cadena sin unit test directo |
| `assembler.py` / `markdown_parser.py` | **69%** | Ramas de tabla/figura parcialmente cubiertas |

> [!WARNING]
> Este dato tiene 6 fases de antigüedad (FASE19 → FASE25 añadió 64 tests → FASE27-28 añadieron 18 más). La cobertura puede haber subido ligeramente, pero los módulos del orquestador y N1 siguen siendo `@slow`. **Medir de nuevo es obligatorio (P0).**

---

### 2.3 🟡 PRECISIÓN — DT-039 es deuda conocida y documentada, no "regresión silenciosa"

FASE19 §4.3 registró la regresión del orchestrator (438L en FASE19 → 576L hoy) como **DT-039** con propuesta de extracción: "`generate_n3.py` (patrón de `generate_n1.py`), dejando `_run_n3` como orquestador delgado". Esta deuda fue agendada para F22, pero en F22 se priorizaron otras DTs más urgentes. No es silenciosa — es una deuda consciente con plan explícito que no se ejecutó.

---

### 2.4 🟡 PRECISIÓN — DT-042 (LCEL en domain) es deuda conocida de FASE19

La "excepción tácita" de LCEL en `domain/chains/` fue identificada en FASE19 §3.4 como DT-042 y catalogada como "decidir: documentar excepción explícita o interfaz de cadena en `infrastructure/`". Agendada para F22 o backlog. No fue decidida formalmente en ninguna fase posterior. **La deuda existe pero el equipo la dejó explícitamente abierta.**

---

### 2.5 🟡 PRECISIÓN — `gateway.py` pricing (DT-040) es zona gris conocida

FASE19 §3.4 detectó que `gateway._PRICING` hardcodea IDs de modelo y que `check-hardcoded-models.sh` tiene puntos ciegos (no detecta `nemotron`, `gpt-oss`, formas con guion). DT-040 agendado para F22. No está resuelto formalmente.

---

### 2.6 ℹ️ CONFIRMADO — `app.py` 487L: DT-038 vs DT-038 (split + SoC)

FASE19 §4.2 estableció que la solución de DT-038 no es solo un split de vistas (`presentation/views/`), sino también **enrutar el acceso a `data/` por casos de uso**. La fase destino era F26 (cuando se reabriera `app.py` para estilo). F26 no lo abordó. El problema de tamaño es secundario; el acoplamiento SoC es el problema real.

---

## 3 — Mapa Completo de Deuda Técnica Conocida (DT viva desde FASE19)

La siguiente tabla consolida las DTs de FASE19 que el equipo registró y cuyo estado en el commit actual **no está cerrado**:

| ID | Descripción original (FASE19) | Fase destino original | Estado actual |
|---|---|---|---|
| **DT-037** | `gateway.py` 503L → paquete `llm/` + fachada re-export | F22 | 🔴 **Abierto** — gateway.py está en 503L (sin cambio); el split propuesto no ocurrió |
| **DT-038** | `app.py` 487L → `presentation/views/` + enrutar acceso `data/` por casos de uso | F26 | 🔴 **Abierto** — app.py accede a SessionLocal directamente en 3 funciones |
| **DT-039** | `generate_informe.py` 438L / `_run_n3` 157L → extraer `generate_n3.py` | F22 | 🔴 **Abierto** (agravado: 438L → 576L) |
| **DT-040** | `gateway._PRICING` hardcodea IDs + hook con puntos ciegos (`nemotron`, guiones) | F22 | 🟡 **Parcial** — los precios siguen hardcodeados; el hook sigue con puntos ciegos |
| **DT-041** | Cobertura `domain/` 69% < 80% | F22 | 🔴 **Abierto** — no re-medida formalmente desde FASE19 |
| **DT-042** | LCEL en `domain/chains/` sin ADR formal o interfaz en `infrastructure/` | F22/backlog | 🟡 **Abierto (por diseño)** — el equipo lo dejó como decisión pendiente |

> [!CAUTION]
> DT-037, DT-038, DT-039, y DT-041 son las 4 deudas estructurales principales. Ninguna fue cerrada a pesar de haber sido agendadas para F22. El foco de F22–F30 fue sobre evidencia/KB/contenido. **Esto no es un error, es priorización, pero la deuda crece con el tiempo.**

---

## 4 — Hallazgos de Comportamiento del Sistema (desde E2E en decisions/)

Esta sección no estaba en v1 — los hallazgos son información de comportamiento real que afecta la evaluación de calidad.

### 4.1 Calidad de contenido por sector (FASE20)

La rúbrica de calidad (v1.0, FASE20) medida sobre 3 informes reales:

| Empresa | Sector | Score Cap 2 | Score Cap 4 | Problema principal |
|---|---|---|---|---|
| Alpina | 3020 (dentro del corpus) | 12/15 | 10/15 | Cap 4 estructura divergente |
| Avianca | 2030 (fuera del corpus) | 5/15 | 6/15 | **Sin datos — corpus sectorial ausente** |
| Bancolombia | 4010 (fuera del corpus) | 5/15 | 6/15 | **Sin datos — corpus sectorial ausente** |

**Esto revela una limitación de diseño fundamental no documentada en los ADRs**: el sistema produce informes de calidad aceptable solo para el sector 3020 (alimentos) donde tiene corpus. Para cualquier otro sector, la calidad cae a 5/15 ("plano, sin tablas"). Esta es la razón de ser de DT-034 (lote EMIS completo, aún parcialmente ejecutado).

### 4.2 Loop de self-review (FASE25)

El loop de auto-revisión (DT-059) fue implementado con `selfreview_enabled=False` por defecto. La corrida E2E de calibración (Alpina, 18.7 min) mostró resultados mixtos:

| Capítulo | Score inicial→final | Resultado |
|---|---|---|
| Cap 2 Competitivo | 6→10 | Mejora de +4, pero **no alcanza el gate (≥11)** por evidencia delgada |
| Cap 5 Convergencia | 6→14 | ✅ Mejora de +8, alcanza el gate |
| Cap 6 Accionables | 10→10 | 0 mejora — el loop descartó la revisión y conservó el original |

**Impacto en auditoría**: el self-review existe pero su efectividad está limitada por el techo del corpus (Cap 2 topa en 10 por escasez de evidencia). El loop es correcto; el problema es aguas arriba (DT-060: mejor extracción de PDF).

### 4.3 Resolución del problema de competidores de sector ajeno (FASE26-FASE30)

El bug más grave del sistema — competidores de tabaco apareciendo en informes de una láctea — fue resuelto progresivamente:
- **FASE26 (DT-061b)**: eje `alcance` global/local
- **FASE27 (DT-062)**: descubrimiento LLM + corroboración web
- **FASE28 (DT-062b)**: filtro sub-estricto por sub-actividad
- **FASE30 (DT-063)**: producto-driven discovery

El proceso fue **iterativo y reactivo** (cada corrida E2E reveló un nuevo bug). La arquitectura de la capa `kb/` (relevance, corroboration, aggregate) es sólida, pero la complejidad acumulada en `entidad_repo.py` (478L) refleja este proceso.

---

## 5 — Diagnóstico de Cumplimiento ADR Revisado

| ADR | Veredicto FASE19 | Veredicto actual (FASE30) |
|---|---|---|
| 001 RAG propio | ✅ fiel | ✅ sin cambio |
| 002 routing local-primero | ✅ (matizado ADR-010) | ✅ sin cambio |
| 003 fuentes doble vía | ✅ fiel | ✅ sin cambio |
| 004 LangChain orquestación | 🟠 divergente parcial (DT-042) | 🟠 **sin resolver** |
| 005 diseño retrieval | ✅ fiel | ✅ sin cambio |
| 006 presupuesto free-first | ✅ fiel | ✅ sin cambio |
| 007 memoria WSL2 | ✅ fiel | ✅ sin cambio |
| 008 orchestrator + on_step | ✅ fiel | ✅ sin cambio |
| 009 refactor _PipelineContext | 🟠 desactualizado (DT-039) | 🔴 **agravado** (438L → 576L) |
| 010 API-first GICS/Cap2 | ✅ fiel | ✅ sin cambio |
| 011 modelo documento + PDF | ✅ fiel | ✅ sin cambio |
| 012 filtrado sectorial | ✅ fiel | ✅ sin cambio |
| 013 web solo-citado | ✅ fiel | ✅ sin cambio |
| 014 caché + batch keep_alive | 🟠 tabla de estado obsoleta | 🟡 **mejor** (cableado confirmado en código) |
| 015 HITL post-gen | ✅ pendiente por diseño | ✅ sin cambio (aún pendiente de implementar) |

---

## 6 — Plan de Reorientación Revisado (P0/P1/P2)

### 🔴 P0 — Antes de Fase 9 (1 sesión máximo)

```
[P0.1] Medir cobertura domain/ actualizada
  → uv run pytest --cov=src/ic/domain --cov-report=term-missing -m "not slow" -q
  → Establecer la nueva línea base (probablemente 70-75% tras los tests de F22-F30)
  → Documentar módulos sin cobertura (generate_n1 sigue siendo 0% en suite rápida)

[P0.2] Decidir y documentar el orchestrator (DT-039, abierto desde FASE19)
  → Es la 4ª vez que se agenda esta deuda sin cerrarse
  → Opción A (recomendada): ADR-016 que formalice la excepción al límite 300L
    para el orquestador del DAG. Cierra la "Red Flag" sin refactor.
  → Opción B: Extraer _run_n3 → generate_n3.py (plan ya existe en DT-039).
    Reduce el archivo a ~490L con precedente de generate_n1.py.
```

### 🟡 P1 — Deuda estructural de FASE19 (2-4 sesiones)

```
[P1.1] DT-038: presentation/ → data/ acoplamiento CRÍTICO
  → Crear casos de uso intermedios para las 3 consultas de app.py:
    - ListarDocumentosUseCase
    - ListarEmpresasUseCase
    - ListarHistorialUseCase
  → app.py llama los use cases, no SessionLocal directamente
  → Esto también permite que las vistas usen datos sin depender del ORM

[P1.2] DT-037: gateway.py (503L) → paquete llm/
  → Separar en cost.py, ollama.py, openrouter.py, resilient.py, factory.py
  → gateway.py queda como fachada de re-export (preserva imports existentes)
  → Riesgo: muchos importadores → hacer con refactor automatizado

[P1.3] DT-042: ADR formal para LCEL en domain/chains/
  → Crear ADR-016 con los límites explícitos:
    - Solo langchain_core (no langchain_community)
    - El LLM siempre se inyecta desde gateway (no instanciado en chains)
    - Los prompts pertenecen al dominio (son lógica de negocio)
  → Cierra la deuda de diseño sin mover código

[P1.4] DT-040: pricing table / hook de hardcode
  → Documentar la tabla _PRICING como excepción de infrastructure/
  → Mejorar check-hardcoded-models.sh para detectar nemotron, guiones
```

### 🟢 P2 — Backlog

```
[P2.1] entidad_repo.py (478L): separar cuando se trabaje en DT-050b
[P2.2] Actualizar REGLAS_NEGOCIO.md: RN-007 y RN-013 ya implementadas
[P2.3] Actualizar ADR-014 tabla de estado (cableado ya ejecutado en FASE16)
[P2.4] PRIME DIRECTIVE §10.3: nota sobre puerto 5434
[P2.5] Strings de modelo en mensajes de usuario (generate_empresa_description:55)
```

---

## 7 — Resumen de Cumplimiento TIER 1 (Revisado)

| Regla TIER 1 | Estado | Evidencia |
|---|---|---|
| 1. No hardcodear modelos LLM | ✅ (2 strings de bajo riesgo en UI/doc) | No es lógica de routing; son mensajes de usuario |
| 2. No credenciales en código | ✅ | `.gitignore` + `.env.example` + grep limpio |
| 3. BD con esquema propio + puerto correcto | ✅ | `db_schema="informes_ic"`, port 5434 |
| 4. Ollama en host | ✅ | `http://127.0.0.1:11434`; no dockerizado |
| 5. Todo acceso externo vía wrapper | ⚠️ **2 excepciones** | `app.py._check_services()` → HTTP directo a Ollama; `app.py` importa `SessionLocal` + repos (DT-038) |

**Veredicto TIER 1: PASA con advertencia** — DT-038 viola la separación de capas pero no expone datos ni produce errores en producción.

---

## 8 — Veredicto Final (Revisado)

**Alineación global: 74 % (antes 79 %)**

El sistema es técnicamente sólido en su núcleo (DAG, retrieval, gateway, embeddings, RN-001). La deuda estructural es conocida, documentada, y fue **conscientemente postergada** para priorizar la entrega de funcionalidad de contenido (Fases 20-30). Esto es una decisión de producto válida, pero la deuda ahora amenaza la mantenibilidad:

- **3 archivos > 300L** con propuestas de refactor que llevan desde FASE19 sin ejecutarse
- **1 violación SoC crítica** (presentation → data) documentada y sin resolver
- **Cobertura de tests** sin medir desde FASE19

> [!NOTE]
> El sistema **puede continuar a Fase 9 (HITL UI)**, pero la Fase 9 no debería abrir más `app.py` sin primero resolver DT-038. Si HITL requiere más lógica en la UI, añadir más acceso directo a `data/` en `app.py` profundizaría la deuda estructural más crítica del proyecto.

**Recomendación:** antes de HITL, cerrar DT-038 (1 sesión de refactor de presentation/) como prerequisito.
