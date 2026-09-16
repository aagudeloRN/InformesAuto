# Integration Test Contract: QA e Integración E2E

**Date**: 2026-08-21 | **Spec**: [spec.md](../spec.md)

Define exactamente qué verifica cada test de integración, cuáles son sus prerequisitos y cuál es el criterio de pass/fail. Este documento es la fuente de verdad para implementar los tests.

---

## Prerequisitos globales (verificados en `tests/integration/conftest.py`)

Antes de ejecutar cualquier test de integración, el `conftest.py` de sesión DEBE verificar:

1. **BD accesible**: `SELECT 1` contra `informes_ic` en `localhost:5434` con las credenciales de `.env`. Si falla → `pytest.skip("BD no disponible en localhost:5434 — arrancar PostgreSQL")`.
2. **LLM configurado**: El modelo definido en `.env` responde a un ping (ej. `curl http://127.0.0.1:11434/api/tags` si es Ollama, o validación de API key si es cloud). Si falla → `pytest.skip("LLM no disponible — verificar configuración en .env")`.
3. **Schema migrado**: La tabla `checkpoints` existe en `informes_ic`. Si no existe → `pytest.skip("Schema no migrado — correr migraciones")`.

---

## Test 1: Pipeline E2E completo

**Archivo**: `tests/integration/test_pipeline_e2e.py`
**Marker**: `@pytest.mark.integration`
**Prerequisito**: `IntegrationFixture` sembrado en BD (fixture de sesión).

### TC-001: InformePiloto contiene todos los capítulos

| Elemento | Valor esperado |
|----------|----------------|
| `informe.cap_benchmarking` | No `None`; `texto` no vacío o párrafo de ausencia estándar |
| `informe.cap_22_division` | No `None`; `texto` no vacío |
| `informe.cap_mercado` | No `None` (puede tener `retrieval_suficiente=False`) |
| Excepción lanzada | Ninguna |

### TC-002: Checkpoints persistidos en BD

| Checkpoint key | Condición de pass |
|---------------|-------------------|
| `cap2_21_globales` | Existe en tabla `checkpoints` bajo `run_key` del fixture |
| `cap2_21_regionales` | Existe en tabla `checkpoints` |
| `cap2_21_startups` | Existe en tabla `checkpoints` |
| `cap_2_2` | Existe en tabla `checkpoints` |

### TC-003: Cap 2.2 aparece entre 2.1 y la sección siguiente en el docx

| Elemento | Valor esperado |
|----------|----------------|
| Posición de `## 2.2.` en `ReportDocument.blocks` | Posterior al último bloque de `## 2.1.` y anterior al primer bloque de `## 2.3.` o `## 2.4.` |
| Heading `## 2.2.` duplicado | No existe (exactamente 1 ocurrencia) |

### TC-004: Segunda corrida sin error

| Elemento | Valor esperado |
|----------|----------------|
| Excepción | Ninguna |
| `updated_at` de checkpoints | Más reciente que tras la primera corrida |

**Tiempo máximo** (SC-001): 120 segundos por corrida.

---

## Test 2: Cache sectorial hit

**Archivo**: `tests/integration/test_sector_cache.py`
**Marker**: `@pytest.mark.integration`
**Prerequisito**: Primera corrida completada (checkpoints `cap2_21_*` en BD bajo clave sectorial del fixture).

### TC-005: Segunda corrida no invoca LLM para Cap 2.1

Setup:
1. Instalar spy sobre el método de invocación del LLM wrapper.
2. Ejecutar el pipeline para una segunda empresa del mismo sector GICS (diferente `run_key`).

| Elemento | Valor esperado |
|----------|----------------|
| `spy.call_count` para invocaciones de Cap 2.1 | `== 0` |
| `informe.cap_benchmarking` de segunda empresa | No `None` |
| Textos de `cap2_21_*` de segunda empresa | Idénticos a los de primera empresa (mismo sector, reutilizados) |

### TC-006: Cache inválido fuerza regeneración

Setup:
1. Marcar todos los checkpoints `cap2_21_*` del sector con `retrieval_suficiente=False`.
2. Instalar spy sobre el LLM wrapper.
3. Ejecutar pipeline para una tercera empresa del mismo sector.

| Elemento | Valor esperado |
|----------|----------------|
| `spy.call_count` para Cap 2.1 | `> 0` (se regeneró) |
| Nuevos checkpoints en BD | `updated_at` más reciente que los marcados como inválidos |

---

## Test 3: Concurrencia de Generate21Startups

**Archivo**: `tests/integration/test_concurrencia.py`
**Marker**: `@pytest.mark.unit` (no requiere BD real — usa fake `db_factory`)
**Prerequisito**: Ninguno de infraestructura.

### TC-007: db_factory crea sesiones independientes por thread

Setup:
1. Instanciar `Generate21Startups` con una `db_factory` fake que retorna mocks únicos y registra cuántas veces fue llamada.
2. Ejecutar `execute()` desde 3 threads concurrentes en `ThreadPoolExecutor(max_workers=3)`.

| Elemento | Valor esperado |
|----------|----------------|
| Excepciones durante ejecución | Ninguna (`DetachedInstanceError`, `InvalidRequestError`, etc.) |
| Número de sesiones creadas por `db_factory` | `== 3` (una por thread) |
| Resultados distintos entre threads | Cada thread retorna su propio objeto (no comparten referencia) |

### TC-008: 10 ejecuciones consecutivas sin fallo (SC-004)

Setup: Repetir TC-007 10 veces en loop.

| Elemento | Valor esperado |
|----------|----------------|
| Fallos en 10 iteraciones | `0` |
| Tiempo total | `< 30` segundos |

---

## Configuración de pytest requerida (cambio en pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-m 'not integration'"   # ← nuevo
env = [
    "OPENBLAS_NUM_THREADS=1",
    "OMP_NUM_THREADS=1",
]
markers = [
    "slow: tests que invocan Ollama real o red externa (excluir con -m 'not slow')",
    "integration: tests que requieren BD real y LLM activo (excluir con -m 'not integration')",  # ← nuevo
]
```

---

## Teardown contract

Al finalizar la sesión de tests de integración, el fixture de sesión DEBE:

1. Eliminar todos los registros de `checkpoints` con `run_key LIKE '__test__%'`.
2. Eliminar embeddings de entidades sembradas (si se crearon durante el test E2E).
3. Verificar que no quedan registros `__test__` en BD; si quedan, loguear advertencia (no fallar).

Si el teardown falla, el próximo `pytest -m integration` DEBE funcionar igualmente (el seed es idempotente: usa `INSERT OR REPLACE` / upsert).
