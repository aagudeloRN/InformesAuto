# Data Model: QA e Integración E2E + Deuda Estructural

**Date**: 2026-08-21 | **Updated**: 2026-09-15 | **Plan**: [plan.md](plan.md)

---

## Entidades de dominio de test (no son entidades de producción)

Este spec no introduce entidades de negocio nuevas. Las entidades aquí describen las estructuras de datos que gobiernan la infraestructura de testing.

---

### IntegrationFixture

Representa el conjunto de datos de prueba sembrados en BD para los tests E2E.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `run_key` | `str` | Clave canónica con prefijo `__test__`; ej. `__test__empresa_prueba:4510` |
| `empresa_nombre` | `str` | Nombre de la empresa ficticia de prueba |
| `sector_gics_code` | `str` | Código GICS de 4 dígitos; determina qué competidores se recuperan |
| `sub_gics` | `str \| None` | Sub-sector opcional para tests de cache multi-sub |
| `competidores` | `list[str]` | Nombres de los competidores sembrados (mínimo 3 para retrieval suficiente) |
| `checkpoints_sembrados` | `list[str]` | Claves de checkpoint pre-sembradas para tests de resume/cache |

**Reglas**:
- El `run_key` DEBE comenzar con `__test__` para permitir limpieza automatizada.
- El teardown DEBE eliminar todos los checkpoints cuyo `run_key LIKE '__test__%'` y los embeddings asociados al fixture.
- El fixture tiene `scope="session"` en pytest: se siembra una vez al inicio de la sesión de integración y se elimina al final.

---

### SectorCache

Representa el conjunto de checkpoints sectoriales que el orquestador busca antes de invocar el LLM para Cap 2.1.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sector_run_key` | `str` | Clave sectorial compuesta: `{sector_gics_code}:{sub_gics}` |
| `cap2_21_globales` | `dict \| None` | Payload serializado de `Cap21Globales` (con `__type__` key) |
| `cap2_21_regionales` | `dict \| None` | Payload serializado de `Cap21Regionales` |
| `cap2_21_startups` | `dict \| None` | Payload serializado de `Cap21Startups` |
| `retrieval_suficiente` | `bool` | `True` si al menos un sub-módulo tiene `retrieval_suficiente=True` |

**Reglas**:
- El cache es válido para reutilización solo si `retrieval_suficiente=True` en al menos un sub-módulo (FR-005).
- Si todos tienen `retrieval_suficiente=False`, el sistema DEBE regenerar (no reutilizar).
- Los checkpoints usan el formato `serialize_cap()` de `checkpoint_serde.py` (con `__type__` key para round-trip fiel).

---

### LLMInvocationSpy

Estructura de datos del spy de pytest usado para verificar el cache hit (US2 / SC-003).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `target_method` | `str` | Ruta del método parcheado en el LLM wrapper (ej. `ic.infrastructure.llm_gateway.LLMGateway.invoke`) |
| `call_count_before` | `int` | Número de invocaciones antes de la segunda corrida |
| `call_count_after` | `int` | Número de invocaciones después de la segunda corrida |
| `calls_for_cap21` | `int` | Invocaciones atribuibles a Cap 2.1 (esperado: 0 en cache hit) |

**Reglas**:
- El spy se instala con `monkeypatch.setattr()` antes de la segunda corrida y se desmonta automáticamente al finalizar el test.
- Solo se cuentan las invocaciones del LLM para sub-módulos de Cap 2.1 (`cap2_21_*`); las de Cap 2.2 u otros capítulos no se cuentan.

---

### OrphanArtifact

Representa un archivo o directorio en el repositorio sin propósito documentado.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `path` | `str` | Ruta relativa desde la raíz del repositorio |
| `tipo` | `enum` | `empty_file`, `zone_identifier`, `undocumented_dir`, `stale_data` |
| `accion` | `enum` | `eliminar`, `documentar`, `ignorar_en_gitignore` |
| `verificacion_previa` | `str` | Qué verificar antes de actuar (ej. "confirmar que el CSV ya está en tabla de entidades") |

**Inventario inicial de OrphanArtifacts**:

| Path | Tipo | Acción | Verificación previa |
|------|------|--------|---------------------|
| `1` | `empty_file` | `eliminar` | Ninguna — 0 bytes, sin contenido |
| `documentos_sectoriales/FuentesExternas/*.Zone.Identifier` | `zone_identifier` | `ignorar_en_gitignore` | Añadir `*.Zone.Identifier` a `.gitignore` |
| `documentos_sectoriales/FuentesExternas/` | `undocumented_dir` | `documentar` | Confirmar que los CSVs son fuente de ingesta (no datos pgvector directos) |

---

## Entidades de deuda estructural

### PricingEntry (DT-040)

Entrada en `_PRICING` que mapea un model string a su costo por token.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `model_key` | `str` | Identificador exacto del modelo tal como llega a `add_call()` — coincide con el string en `.env` |
| `price_in` | `float` | Costo en USD por token de entrada (prompt) |
| `price_out` | `float` | Costo en USD por token de salida (completion) |

**Reglas**:
- `price_in` y `price_out` DEBEN ser >0 para modelos de pago. Los modelos `:free` tienen `(0.0, 0.0)` explícitamente.
- Si un `model_key` no tiene entrada, `add_call` DEBE retornar un `CallRecord` con `costo_usd=None` y loggear WARNING, nunca registrar `0.0`.
- Las entradas Gemini deben cubrir al menos: `gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`.

---

### UIQueryResult (DT-038)

Tipos simples que `ui_query_services.py` retorna a `presentation/app.py` — sin acoplamiento a ORM.

#### EmpresaRow
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `str` | UUID de la empresa como string |
| `nombre` | `str` | Nombre display de la empresa |

#### DocumentoRow
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `str` | UUID del documento |
| `nombre_archivo` | `str` | Nombre del archivo PDF |
| `tipo` | `str` | Tipo de documento (sectorial, empresa, etc.) |
| `sector_gics` | `str \| None` | Código GICS asociado |
| `activo` | `bool` | Si el documento está activo en el índice |
| `año` | `str` | Año de publicación (de metadatos) |
| `n_chunks` | `str` | Número de chunks (de metadatos) |

#### InformeRow
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `run_key` | `str` | Clave canónica del informe |
| `empresa` | `str` | Nombre de la empresa |
| `sector_gics` | `str` | Sector analizado |
| `estado` | `str` | Estado del informe |
| `created_at` | `str` | Timestamp ISO de creación |

**Reglas**:
- Estos tipos NO son modelos SQLAlchemy. Son dataclasses o TypedDicts simples, definidos en `domain/use_cases/ui_query_services.py`.
- `presentation/app.py` solo recibe estos tipos — nunca modelos ORM.

---

### GatewayModule (DT-037)

Mapeo de la división de `gateway.py` en módulos cohesivos.

| Módulo | Contenido | Líneas aprox. |
|--------|-----------|---------------|
| `gateway_pricing.py` | `_PRICING`, `CallRecord`, `CostTracker` | ~90 |
| `gateway_models.py` | `OllamaGatewayLLM`, `OpenRouterGatewayLLM` | ~260 |
| `gateway_errors.py` | `is_rate_limit_error`, `is_transient_network_error`, `is_empty_generation_error`, `ResilientGatewayLLM` | ~130 |
| `gateway.py` | `build_llm`, `build_api_llm`, `build_resilient_api_llm`, `_provider_base_and_key`, re-exports | ~80 |

**Regla de compatibilidad**: Todo import externo de la forma `from ic.infrastructure.llm.gateway import X` donde `X` era público antes del refactor debe seguir funcionando sin cambios.

---

### InformeModule (DT-039)

Mapeo de la división de `generate_informe.py` en módulos internos.

| Módulo | Contenido | Líneas aprox. |
|--------|-----------|---------------|
| `generate_informe.py` | `InformeParams`, `InformeResult`, shell de `GenerateInforme` (métodos delegadores) | ~120 |
| `_informe_context.py` | `_PipelineContext`, `_setup_infra`, `_sweep_stale_web`, `_promote_cited_web` | ~160 |
| `_informe_nodes_n0.py` | Lógica de `_run_n0` (extracción de empresa, GICS, RAG inicial) | ~90 |
| `_informe_nodes_n2n3.py` | Lógica de `_run_n2` (Cap 5/6) y `_run_n3` (ensamblado final) | ~260 |

**Regla de compatibilidad**: `from ic.domain.use_cases.generate_informe import GenerateInforme, InformeParams, InformeResult` sigue funcionando. Los módulos `_informe_*` son privados (prefijo `_`) — no forman parte de la API pública.
