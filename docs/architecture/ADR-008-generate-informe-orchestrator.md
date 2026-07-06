# ADR-008: GenerateInforme — Use Case Orquestador + Patrón on_step Callback

**Status:** Aceptado
**Fecha:** 2026-07-06
**Autores:** aagudeloRN + Claude Sonnet 4.6

---

## Contexto

Hasta Fase 5F, la lógica completa del pipeline (Cap 1→GICS→N1 paralelo→N2→N3→ensamblado)
vivía inline en `scripts/run_pilot.py`. Esto violaba SoC (PRIME DIRECTIVE §1.1): el CLI
contenía lógica de dominio. Para introducir la UI Streamlit (Fase 6) sin duplicar código,
era necesario extraer el pipeline a una capa reutilizable.

---

## Decisión

Se crea `src/ic/domain/use_cases/generate_informe.py` que expone:

```python
@dataclass
class InformeParams:
    empresa: str
    ciiu: str | None = None
    output_path: str | None = None

@dataclass
class InformeResult:
    ruta_docx: str
    n_referencias: int
    costo_usd: float
    tokens_in: int
    tokens_out: int
    tiempo_total_s: float
    cost_records: list

StepCallback = Callable[[int, int, str], None]  # (n, total, label) → None

class GenerateInforme:
    TOTAL_PASOS = 10

    def __init__(self, settings) -> None: ...

    def run(
        self,
        params: InformeParams,
        on_step: StepCallback | None = None,
    ) -> InformeResult: ...
```

El callback `on_step(n, total, label)` desacopla el reporte de progreso de la ejecución:
- CLI: imprime a stdout con tiempos por paso
- UI Streamlit: actualiza `st.progress()` y un `st.empty()` placeholder
- Tests: puede ser `None` (sin overhead)

`run_pilot.py` se convierte en un thin wrapper (~100 líneas) que solo hace:
argparse → verificación de servicios → `GenerateInforme.run()` → impresión de resumen.

---

## Consecuencias

### Positivas
- CLI y UI comparten exactamente el mismo pipeline — cero duplicación
- El progreso es completamente desacoplado de la ejecución (inversión de control)
- `InformeResult` es un DTO limpio que cualquier cliente puede consumir
- Testeable de forma aislada (pasar `on_step=None`, mockear deps)

### Negativas / Trade-offs
- `GenerateInforme.run()` acumula ~300 líneas (punto de presión arquitectónica)
  → Deuda técnica: refactorizar en métodos privados `_run_n1()`, `_run_n2()`, `_run_n3()`
  → Ver §"Deuda técnica" más abajo
- Los imports de dominio están diferidos dentro de `run()` para evitar imports circulares
  → Overhead mínimo (primera llamada), no afecta rendimiento

---

## Alternativas consideradas

### A — Pasar el pipeline como generador (`yield`)
Ventaja: la UI puede iterar `for step in pipeline.run(params)`.
Desventaja: Streamlit no es compatible con generadores en el hilo principal; requeriría
`threading.Thread` + `queue.Queue`, complejizando la UI.

### B — Callbacks asíncronos (`async def on_step`)
Ventaja: evita bloqueos en UIs async.
Desventaja: LangChain LCEL y Ollama gateway son síncronos; introduce `asyncio.run()` anidado
con comportamiento impredecible en contextos ya async (Streamlit, pytest-asyncio).

### C — Mantener lógica en `run_pilot.py` + copiar a `app.py`
Rechazado: duplicación directa de ~300 líneas críticas de negocio. Viola DRY y PRIME
DIRECTIVE §2.4 (atomicidad).

---

## Deuda técnica registrada

| ID | Descripción | Prioridad |
|----|-------------|-----------|
| DT-001 | `generate_informe.py` tiene 348 líneas (Red Flag PRIME DIRECTIVE §IX). Refactorizar `run()` en métodos privados `_setup_infra()`, `_run_n1()`, `_run_n2()`, `_run_n3()` usando un `_PipelineContext` dataclass para pasar estado. | Alta — Fase 7 |
| DT-002 | `run()` llama a `scripts/ingest_pdf.py` via `sys.path` manipulation (violación SoC). Mover la lógica de ingesta a `infrastructure/sources/pdf_ingestor.py`. | Media — Fase 7 |
| DT-003 | Los imports de dominio están diferidos dentro de `run()`. Investigar si la circularidad se puede resolver reestructurando el grafo de imports. | Baja — Fase 8 |

---

## Patrón de referencia para futuros use cases de alto nivel

```python
# Patrón GenerateInforme — replicar en casos similares
class OrchestratorUseCase:
    def __init__(self, settings) -> None:
        self._settings = settings

    def run(
        self,
        params: ParamsDTO,
        on_step: Callable[[int, int, str], None] | None = None,
    ) -> ResultDTO:
        # 1. Setup infra (wiring interno)
        # 2. Ejecutar pasos llamando on_step(n, total, label) antes de cada uno
        # 3. Retornar DTO de resultado (nunca mutables, nunca side effects externos)
        ...
```

---

## Archivos relacionados

- `src/ic/domain/use_cases/generate_informe.py` — implementación
- `scripts/run_pilot.py` — thin wrapper CLI
- `src/ic/presentation/app.py` — thin wrapper UI
- `tests/test_generate_informe.py` — tests del orchestrator
