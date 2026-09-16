# Fase 31 ? Spec 005: QA, Integraci?n E2E y Saldado de Deuda Estructural

> Estado: **Completado e Integrado**. Gate: ruff 0 errores, 710 unit tests passing, 3 integration tests passing, cobertura domain/ 93%, 0 violaciones SoC, todos los archivos <300L.

## Contexto y Objetivos

La especificaci?n `specs/005-qa-integracion-e2e` abord? el cierre de la deuda t?cnica estructural acumulada desde las Fases 19-30 y la creaci?n de la suite formal de integraci?n y concurrencia para el pipeline completo de generaci?n de informes.

## Deudas Estructurales Saldadas

| ID | Deuda / Requisito | Soluci?n Implementada | Estado |
|----|-------------------|-----------------------|:------:|
| **DT-037** | `gateway.py` >300L | Modularizado en 4 archivos: `gateway.py` (149L), `gateway_errors.py` (154L), `gateway_models.py` (260L), `gateway_pricing.py` (101L). Re-exports preservados para retrocompatibilidad. | **CERRADA** |
| **DT-038** | `presentation/app.py` acoplado a `data/` | Creado `src/ic/domain/use_cases/ui_query_services.py` con `list_empresas_conocidas`, `list_documentos_indexados`, `list_informes_recientes`. `app.py` desacoplado al 100% (`grep -rn "from ic.data" src/ic/presentation/` = 0). | **CERRADA** |
| **DT-039** | `generate_informe.py` 576L | Modularizado en 5 archivos: `generate_informe.py` (77L), `_informe_context.py` (193L), `_informe_nodes_n0.py` (101L), `_informe_nodes_n2.py` (132L), `_informe_nodes_n3.py` (212L). Firma p?blica inalterada. | **CERRADA** |
| **DT-040** | `_PRICING` y tracking de Gemini | Actualizada tabla `_PRICING` con modelos Gemini 2.5 (`gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`). Lookup en cascada (exacto ? `:free` ? prefijo `gemini-` ? `None` + warning log). Tipo `CallRecord.costo_usd: float | None`. | **CERRADA** |
| **DT-041** | Cobertura `domain/` < 80% | Cobertura total de `src/ic/domain` elevada al **93%** (supera el 80% exigido por la Constituci?n). | **CERRADA** |

## Suites de Integraci?n y Concurrencia Creadas

Se estructur? el directorio `tests/integration/` con aislamiento respecto a la suite unitaria est?ndar (`pytest -m "not integration"` por defecto en `pyproject.toml`):

1. **`test_pipeline_e2e.py` (US1)**:
   - Ejecuta el flujo end-to-end N0?N1?N2 con LLM mockeado y persistencia en PostgreSQL (`informes_ic`).
   - Valida presencia de todos los checkpoints requeridos (`cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups`, `cap_2_2`) y que una segunda corrida corre limpia sin excepciones.
2. **`test_sector_cache.py` (US2)**:
   - Valida mediante spy en `OpenRouterGatewayLLM._generate` que una segunda empresa del mismo sector reutiliza el cach? sectorial y no re-invoca al LLM para Cap 2.1 (`call_count == 0`).
   - Valida identidad de textos y re-generaci?n correcta en caso de retrieval insuficiente.
3. **`test_concurrencia.py` (US3)**:
   - Valida concurrencia de `Generate21Startups` en `ThreadPoolExecutor(max_workers=3)` con `db_factory` independiente.
   - Ejecuta 10 iteraciones continuas garantizando 0 errores de sesi?n SQLAlchemy (`DetachedInstanceError`, `InvalidRequestError`).
4. **`conftest.py` y `seed/sector_fixture.py`**:
   - Manejo de seeds con prefijo `__test__` y teardown autom?tico al finalizar.

## Limpieza de Repositorio (US4)

- Eliminado archivo espurio de depuraci?n `1` (`git rm 1`).
- Agregada regla `*.Zone.Identifier` en `.gitignore` para metadatos WSL/Windows.
- Creado `documentos_sectoriales/FuentesExternas/README.md` documentando origen, prop?sito y ciclo de ingesta de los archivos CSV/xlsx.

## M?tricas de Calidad Finales

- **Ruff linting**: 0 errores en todo el proyecto.
- **L?mites de archivo**: Todos los m?dulos de `domain/` e `infrastructure/llm/` permanecen estrictamente por debajo de 300 l?neas.
- **Suite de Pruebas**:
  - Unitarias (`not integration`): 710 pasadas.
  - Integraci?n (`integration`): 3 pasadas.
- **Cobertura Domain**: 93%.
