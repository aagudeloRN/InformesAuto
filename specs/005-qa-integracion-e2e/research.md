# Research: QA e Integración E2E + Deuda Estructural

**Date**: 2026-08-21 | **Updated**: 2026-09-15 | **Plan**: [plan.md](plan.md)

---

## Decisión 1: Estrategia de fixture de datos para tests E2E

**Decision**: Fixture de sector dedicado con `run_key` prefijado `__test__`, insertado en BD real (puerto 5434) y eliminado en teardown de sesión pytest.

**Rationale**:
- Usar datos de producción contaminaría checkpoints reales con corridas de test.
- Una BD SQLite en memoria no prueba el comportamiento real con pgvector y los tipos propios del schema `informes_ic`.
- El prefijo `__test__` permite identificar y limpiar datos de test incluso si el teardown falla (limpieza manual trivial: `DELETE FROM checkpoints WHERE run_key LIKE '__test__%'`).

**Alternatives considered**:
- A) Datos de producción reales → descartado: riesgo de contaminación y side effects visibles para usuarios.
- C) BD separada solo para escritura → descartado: complejidad de mantener dos conexiones; el schema de test es idéntico al de producción.

**Implementation note**: El seed script usa `CheckpointRepository` y `EntidadRepository` existentes (capa `data/`) — no escribe SQL crudo. El fixture pytest tiene `scope="session"` para sembrar una vez y compartir entre todos los tests E2E.

---

## Decisión 2: Ubicación tests de integración

**Decision**: Subdirectorio `tests/integration/` con `conftest.py` propio.

**Rationale**:
- `pyproject.toml` ya configura `testpaths = ["tests"]` — `tests/integration/` es recogido automáticamente.
- Un `conftest.py` propio en `tests/integration/` puede registrar el marker `integration` y verificar prerequisitos (BD + LLM) sin afectar los tests unitarios existentes.
- El `addopts = -m "not integration"` en `[tool.pytest.ini_options]` excluye los tests de integración de la corrida por defecto.

**Alternatives considered**:
- A) `tests_integration/` en raíz → descartado: rompe la convención del proyecto y requiere actualizar `testpaths`.
- C) Mismo `tests/` con prefijo de archivo → descartado: no permite `conftest.py` aislado ni prerequisite checks automáticos.

**Existing config to update**: `pyproject.toml` ya tiene `[tool.pytest.ini_options]` con `markers` y `asyncio_mode`. Solo añadir la entrada `integration` a `markers` y el `addopts`.

---

## Decisión 3: Mecanismo de verificación de cache hit (US2 / SC-003)

**Decision**: Spy sobre el método de invocación del LLM wrapper usando `monkeypatch` de pytest; contador de llamadas verificado a cero en segunda corrida.

**Rationale**:
- Los logs pueden cambiar de texto sin que cambie el comportamiento (riesgo de falso positivo/negativo en tests de log).
- `monkeypatch` es nativo de pytest — no requiere dependencias adicionales.
- El LLM wrapper en `infrastructure/` expone un método de invocación único (ej. `LLMGateway.invoke` o `ChatModel.invoke`); el spy se pone sobre ese método.
- La segunda corrida debe dejar el contador en 0 para Cap 2.1 (el cache hit evita la llamada); Cap 2.2 sí puede invocar el LLM si es una empresa nueva.

**Alternatives considered**:
- A) Inspección de logs → descartado: frágil ante cambios de mensaje de log; no es un contrato de comportamiento.
- C) Comparación de timestamps en BD → descartado: el upsert de checkpoint puede actualizar `updated_at` aunque no haya llamada LLM; no es señal confiable.

**Implementation note**: El spy se instala antes de la segunda corrida y se desmonta automáticamente tras el test. El contador se pasa como atributo del mock: `mock_invoke.call_count == 0` para los sub-módulos de Cap 2.1.

---

## Decisión 4: Test de concurrencia para Generate21Startups (US3)

**Decision**: Fake `db_factory` con tracking de instancias de sesión; no requiere BD real.

**Rationale**:
- El objetivo es verificar que cada thread crea su propia sesión (no comparte estado), no que la BD funcione.
- Una fake `db_factory` retorna mocks con ID único por invocación; el test verifica que se crearon N sesiones distintas para N threads.
- Esto mantiene el test de concurrencia como test unitario (sin marcador `integration`), lo que mejora la cobertura sin requerir infraestructura.

**Alternatives considered**:
- `db_factory` real con `SessionLocal` → válido, pero requiere BD activa y añade latencia; el comportamiento relevante (aislamiento de sesión) se puede verificar con fake sin pérdida de fidelidad.

---

## Decisión 5: Limpieza de artefactos huérfanos

**Decision**: `documentos_sectoriales/FuentesExternas/` recibe un `README.md` que documenta cada archivo; el archivo vacío `1` se elimina del repo con `git rm`.

**Findings**:
- `FuentesExternas/` contiene: `DBCamaraComercio20250410.CSV`, `CatalogoVerticalesStartIAGICS.csv`, `startia_clean.xlsx` — archivos de datos de fuentes externas (Cámara de Comercio, StartIA) usados en el proceso de ingesta `ingest_batch.py`. No están indexados directamente en pgvector; son fuente de las entidades en la tabla de entidades.
- Los archivos `.Zone.Identifier` son metadatos de Windows (descarga desde Edge/IE) — pueden ignorarse o eliminarse; no contienen datos.
- El archivo `1` en la raíz del repo está vacío (0 bytes); es un artefacto de debug.
- El `.gitignore` actual no excluye `*.Zone.Identifier` — conviene añadir la regla.

**Implementation note**: El `README.md` debe documentar origen, fecha, propósito y estado de cada archivo (si ya fue ingestado o está pendiente). No se borra ningún CSV sin confirmar que su contenido ya está en la tabla de entidades.

---

## Decisión 6: Pricing comprehensivo — Gemini + OpenRouter (DT-040)

**Decision**: Extender `_PRICING` para cubrir todos los modelos del proyecto, no solo Gemini. Reglas de lookup en cascada (sin llamadas de red):

1. **Match exacto**: buscar el model string en `_PRICING` — resultado inmediato.
2. **Sufijo `:free`**: cualquier modelo que termine en `:free` → `(0.0, 0.0)` automático, sin necesidad de entrada explícita. Elimina la necesidad de enumerar todos los modelos gratuitos.
3. **Prefijo `"gemini-"`**: modelo Gemini sin match exacto → precio de fallback `gemini-2.5-flash-lite`. Cubre variantes preview con sufijo de fecha.
4. **Desconocido**: `cost_usd = None` + log `WARNING`.

**Entradas explícitas de pago a añadir**:
- `gemini-2.5-flash-lite`: $0.075 in / $0.30 out por 1M tokens (Google AI Studio, Sep 2026)
- `gemini-2.5-flash`: $0.075 in / $0.30 out por 1M tokens
- `gemini-2.5-pro`: $1.25 in / $10.00 out por 1M tokens
- `google/gemma-3-27b-it`: ya existe ($0.10 in / $0.20 out)
- `google/gemma-3-12b-it`: ya existe ($0.05 in / $0.10 out)

**Modelos actuales que se benefician de la regla `:free`** (no requieren entrada explícita):
- `nvidia/nemotron-3-super-120b-a12b:free`
- `nvidia/nemotron-3-ultra-550b-a55b:free`
- `openai/gpt-oss-120b:free`
- `meta-llama/llama-3.3-70b-instruct:free`

**Alternatives considered**:
- Fetch dinámico de precios desde la API de OpenRouter → añade dependencia de red en el init; los precios raramente cambian; descartado.
- Enumerar explícitamente todos los modelos `:free` → mantenimiento innecesario; la regla de sufijo es más robusta.

**Implementation note**: `CostTracker.add_call` implementa las 4 reglas en orden. `CallRecord.costo_usd` cambia a `float | None`. `total_cost()` suma solo records no-None. Se añade `has_unknown_pricing() -> bool`.

---

## Decisión 7: Estructura de ui_query_services.py (DT-038)

**Decision**: Un módulo `domain/use_cases/ui_query_services.py` con 3 funciones que devuelven tipos simples (listas de dicts o dataclasses livianas definidas en `shared/`), sin acoplamiento a SQLAlchemy ni a modelos de BD.

**Rationale**:
- `app.py` solo necesita datos para renderizar (tuplas nombre/id, filas de tabla) — no necesita entidades SQLAlchemy.
- Devolver tipos simples evita que `presentation/` tenga que importar DTOs de `data/` o modelos ORM.
- El módulo abre y cierra su propia `SessionLocal` en cada función — no recibe sesiones como parámetro, evitando el anti-patrón de pasar sesiones hacia arriba.

**Alternatives considered**:
- Pasar `SessionLocal` desde `app.py` → invierte el control; `app.py` seguiría importando de `data/`.
- Clase de servicio con inyección de repositorio → sobrecarga innecesaria para 3 funciones de consulta sencillas.

**Implementation note**: Los 3 import-dentro-de-función en `app.py` (líneas 60-61, 132-133, 212-213) se reemplazan por un único import al nivel del módulo: `from ic.domain.use_cases.ui_query_services import list_empresas_conocidas, list_documentos_indexados, list_informes_recientes`. Verificar con `grep -rn "from ic.data" src/ic/presentation/` que el resultado es vacío.

---

## Decisión 8: Punto de corte para refactor de gateway.py (DT-037)

**Decision**: 4 archivos: `gateway_pricing.py` (pricing+tracker), `gateway_models.py` (Ollama+OpenRouter), `gateway_errors.py` (helpers de error + ResilientGatewayLLM), `gateway.py` (funciones de construcción + re-exports).

**Rationale**:
- Las 3 clases de modelo son la parte más voluminosa (~350L) — separarlas solas ya resuelve el problema de tamaño.
- `CostTracker` y `_PRICING` son un bloque cohesivo (datos + lógica de costo) — van juntos.
- Los helpers de error (`is_rate_limit_error`, etc.) son los prerequisitos de `ResilientGatewayLLM` — agruparlos en `gateway_errors.py` evita imports circulares.
- `gateway.py` como punto de entrada público evita que el resto de la app tenga que cambiar sus imports; re-exporta lo más usado.

**Alternatives considered**:
- 2 archivos (pricing + modelos) → `gateway.py` quedaría con ~150L incluyendo `ResilientGatewayLLM`; pasa el límite si crece.
- Un archivo por clase → demasiada fragmentación; 6 archivos para 566L es excesivo.

---

## Decisión 9: Punto de corte para refactor de generate_informe.py (DT-039)

**Decision**: 4 archivos: `_informe_context.py`, `_informe_nodes_n0.py`, `_informe_nodes_n2n3.py`, `generate_informe.py` (shell público).

**Rationale**:
- `_PipelineContext` y `_setup_infra` son inseparables (el contexto se configura en setup; nada más lo toca directamente).
- `_run_n0` es autónomo (solo lee `ctx.params` y escribe en `ctx`; no llama a N1/N2).
- `_run_n2` y `_run_n3` comparten la sesión de BD N2 y la lógica de párrafos introductorios — mantenerlos juntos evita acoplamiento de estado.
- `_run_n1` ya es una delegación de 2 líneas a `run_n1_parallel` — queda en el shell.

**Prefijo `_`**: Los 3 módulos auxiliares tienen prefijo `_` (convención Python para módulos internos); no forman parte de la API pública de `domain/`.

---

## Decisión 10: Módulos objetivo para cobertura ≥80%

**Decision**: Medir primero; atacar los módulos de más línea × más baja cobertura. Candidatos probables (basado en historia del proyecto): `generate_benchmarking.py`, `generate_n1.py`, `nurture_kb.py`, `discover_globales.py`, `checkpoint_hooks.py`.

**Rationale**:
- La cobertura global bajó desde el 69% de F19 a medida que se añadieron módulos en las specs 001-004 sin tests de dominio completos.
- Los módulos de orquestación (generate_*.py) típicamente tienen bajo cobertura porque dependen de fixtures complejas — son los que más impactan subir la cifra global.

**Implementation note**: No añadir tests que dependan de BD o LLM real para subir cobertura — usar `_FakeSession` y mocks del patrón del proyecto. El objetivo es cobertura de lógica de negocio, no de integración.
