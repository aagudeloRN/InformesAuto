# Feature Specification: QA e Integración E2E — Módulos 001–004 + Deuda Estructural

**Feature Branch**: `spec-driven-experiment`

**Created**: 2026-08-21

**Updated**: 2026-09-15

**Status**: Draft

**Input**: Validar que los cuatro módulos ya implementados (Specs 001–004) funcionan correctamente de forma integrada en entorno real: pipeline completo N0→N1→N2, cache sectorial (T037), concurrencia de sub-módulos de Cap 2.1, y limpieza de artefactos del repositorio. Adicionalmente, saldar la deuda estructural identificada en el roadmap: SoC en presentación, pricing Gemini, refactors de módulos >300L, y cobertura de tests.

---

## Contexto del Componente

### Estado de implementación existente (hallazgos del audit 2026-08-21)

Un audit cruzado de los cuatro specs reveló que la implementación está 95% completa con 53 tests unitarios en verde. Los gaps pendientes son de integración y validación en entorno real, no de arquitectura:

- **T037 (Specs 002/003)**: El cache sectorial existe en código (`_load_sector_cache` en `generate_benchmarking.py`) pero nunca fue validado en entorno real — no hay prueba que confirme que una segunda corrida para el mismo sector reutiliza los checkpoints `cap2_21_*` sin re-invocar al LLM.
- **Spec 003 — Thread-safety**: `Generate21Startups` tiene el path `db_factory` para correr dentro de `ThreadPoolExecutor`, pero no existe test que lo ejercite concurrentemente.
- **Spec 004 — Ensamblaje final**: Cap 2.2 fue integrado en `assembler.py` (T030) pero la integración no tiene test de ensamblaje.
- **Artefactos huérfanos**: Archivo vacío `1` en raíz del repo; directorio `documentos_sectoriales/FuentesExternas/` sin documentación de propósito.

### Deuda estructural incluida en este spec

Identificada en el roadmap (auditoría 2026-08-03), agravada en sesiones posteriores:

- **DT-038**: `presentation/app.py` llama directamente a repositorios de `data/`, violando la separación de capas definida en CLAUDE.md. Bloquea el HITL futuro. (P1)
- **DT-040**: El gateway registra costo $0 para todos los modelos Gemini porque no existen entradas en la pricing table para `gemini-*`. Dato de negocio incorrecto persistido en BD. (P1)
- **DT-037**: `infrastructure/llm/gateway.py` supera las 300 líneas — límite definido como red flag en CLAUDE.md. Violación de SoC. (P2)
- **DT-039**: `domain/generate_informe.py` tiene 576 líneas — casi el doble del límite. Mezcla orquestación del DAG con lógica de nodos individuales. (P2)
- **Cobertura**: Última medición de `domain/` fue 69% (base F19). CLAUDE.md exige 80% mínimo. (P2)

Este spec no añade funcionalidad nueva — establece los criterios de aceptación de integración y salda la deuda estructural acumulada.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Pipeline E2E produce informe completo con BD y LLM reales (Priority: P1)

El analista ejecuta una generación de informe para una empresa de prueba. El sistema completa el pipeline completo (descripción → Cap 2.1 → Cap 2.2 → benchmarking → ensamblado) contra la instancia PostgreSQL real y los modelos LLM configurados, y produce un documento con todas las secciones presentes y los checkpoints persistidos en BD.

**Why this priority**: Es la validación de confianza más importante: si el pipeline E2E no funciona en entorno real, ningún módulo individual es útil para producción.

**Independent Test**: Se puede probar con una empresa ficticia de sector conocido (ej. una empresa del sector de tecnología con competidores en la BD) ejecutando `generate_informe()` directamente y verificando el objeto `InformePiloto` resultante y los registros en tabla de checkpoints.

**Acceptance Scenarios**:

1. **Given** una empresa de prueba con sector GICS configurado y al menos 3 competidores en la BD, **When** se ejecuta el pipeline completo, **Then** el `InformePiloto` resultante contiene `cap_benchmarking`, `cap_22_division` y `cap_mercado` todos con `retrieval_suficiente=True` o con párrafo de ausencia estándar (nunca `None`).
2. **Given** el pipeline completa sin error, **When** se verifica la tabla de checkpoints en BD, **Then** existen registros para `cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups` y `cap_2_2` bajo el mismo `run_key`.
3. **Given** el documento ensamblado, **When** se inspeccionan los bloques del `ReportDocument`, **Then** la sección `## 2.2. División de Competidores` aparece entre `## 2.1. Jugadores Clave` y `## 2.3. Mercado` (o `## 2.4.` si no hay mercado).
4. **Given** que el pipeline ya corrió una vez, **When** se ejecuta de nuevo para la misma empresa, **Then** la corrida completa sin excepción y los checkpoints en BD tienen `updated_at` más reciente.

---

### User Story 2 — Cache sectorial evita re-invocar LLM en segunda corrida (Priority: P1)

En una corrida de informe para una empresa, el sistema genera y persiste los sub-módulos de Cap 2.1 (globales, regionales, startups) bajo una clave sectorial. En una segunda corrida para una empresa diferente del mismo sector GICS, el sistema reutiliza esos checkpoints sin llamar al LLM.

**Why this priority**: Sin cache sectorial funcionando, cada informe del mismo sector incurre en costos y latencia de LLM innecesarios. Es el mecanismo de eficiencia central del diseño (FR-012 de Spec 002).

**Independent Test**: Ejecutar dos corridas consecutivas para dos empresas del mismo sector; interceptar o contar las invocaciones al LLM wrapper para confirmar que la segunda corrida no genera nuevas llamadas para Cap 2.1.

**Acceptance Scenarios**:

1. **Given** un sector GICS con checkpoints `cap2_21_*` ya persistidos en BD, **When** se genera un informe para una segunda empresa del mismo sector, **Then** el orquestador carga los checkpoints existentes y no invoca el LLM para Cap 2.1 en esa corrida.
2. **Given** que los checkpoints de un sector están en BD, **When** se verifica el `InformePiloto` de la segunda empresa, **Then** los textos de Cap 2.1 (globales, regionales, startups) son idénticos a los de la primera empresa (mismo contenido de sector reutilizado).
3. **Given** que los checkpoints existen pero el flag de `retrieval_suficiente` es `False` en todos, **When** se genera la segunda empresa, **Then** el sistema regenera Cap 2.1 en lugar de reutilizar datos vacíos.

---

### User Story 3 — Sub-módulos de Cap 2.1 corren concurrentemente sin errores de sesión BD (Priority: P2)

Los tres sub-módulos de Cap 2.1 (Globales, Regionales, Startups) se ejecutan en paralelo dentro de un `ThreadPoolExecutor`. Cada sub-módulo que usa `db_factory` debe abrir su propia sesión de BD independiente y cerrarla correctamente, sin que un thread interfiera con la sesión del otro.

**Why this priority**: Un error de sesión compartida en producción causaría corrupción silenciosa de datos o fallos intermitentes difíciles de diagnosticar.

**Independent Test**: Ejecutar los tres sub-módulos en un `ThreadPoolExecutor(max_workers=3)` con una `db_factory` real (o fake con tracking de instancias) y verificar que cada thread usó una sesión distinta y que todas se cerraron.

**Acceptance Scenarios**:

1. **Given** `Generate21Startups` instanciado con `db_factory` (no con `entidad_repo` directo), **When** se ejecuta `execute()` desde dentro de un thread de `ThreadPoolExecutor`, **Then** completa sin `DetachedInstanceError`, `InvalidRequestError` ni cualquier error de sesión SQLAlchemy.
2. **Given** los tres sub-módulos ejecutándose concurrentemente, **When** todos completan, **Then** cada uno produjo su propio objeto de resultado independiente (sin contaminación de datos entre threads).
3. **Given** que la `db_factory` es llamada dentro del thread, **When** se verifica el número de sesiones creadas, **Then** cada thread creó exactamente una sesión nueva (no reutilizó la sesión del thread principal).

---

### User Story 4 — Repositorio limpio de artefactos huérfanos (Priority: P3)

El directorio del proyecto no contiene archivos vacíos, temporales ni directorios sin documentar que no pertenezcan a la base de conocimiento de la aplicación.

**Why this priority**: Los artefactos huérfanos confunden a nuevos colaboradores y pueden incluir accidentalmente datos sensibles en el historial de git.

**Independent Test**: Listar los archivos no rastreados y el contenido de `documentos_sectoriales/FuentesExternas/`; verificar que todo tiene propósito documentado o ha sido eliminado/movido.

**Acceptance Scenarios**:

1. **Given** el estado actual del repositorio, **When** se corre `git status`, **Then** no aparece el archivo vacío `1` (eliminado o ignorado).
2. **Given** el directorio `documentos_sectoriales/FuentesExternas/`, **When** se revisa su contenido, **Then** existe un `README.md` que describe qué tipo de documentos viven ahí, de qué fuentes provienen, y cuál es el proceso para ingesta; o el directorio es eliminado si está vacío.
3. **Given** que `documentos_sectoriales/` contiene PDFs de fuentes externas (EMIS, informes sectoriales), **When** se revisa el `.gitignore`, **Then** los PDFs grandes (>10MB) están excluidos del tracking de git.

---

### User Story 5 — La capa de presentación no accede directamente a datos (Priority: P1) [DT-038]

El archivo `presentation/app.py` actualmente llama repositorios de `data/` sin pasar por `domain/`. Esto viola la separación de capas y bloquea la implementación futura del HITL. Toda interacción de la UI con datos debe enrutarse a través de un caso de uso o servicio en `domain/`.

**Why this priority**: La violación de SoC en la frontera presentation↔data es el bloqueante más directo para el HITL (F24/F25). Sin esta corrección, añadir validación humana en el flujo requeriría reescribir la UI desde cero.

**Independent Test**: Ejecutar `grep -rn "from data\." presentation/` — el resultado debe ser vacío tras el fix.

**Acceptance Scenarios**:

1. **Given** el código de `presentation/app.py`, **When** se buscan imports directos de `data/`, **Then** no existe ningún `from data.` ni `import data.` en el módulo de presentación.
2. **Given** cualquier funcionalidad de la UI que requiera acceso a datos (listar empresas, leer checkpoints, consultar KB), **When** se traza el flujo de llamadas, **Then** todas pasan por al menos un use case o service definido en `domain/` antes de llegar a un repositorio.
3. **Given** que se mueve lógica de `app.py` a `domain/`, **When** se ejecuta la suite de tests unitarios, **Then** todos los tests existentes siguen en verde (zero regresiones).

---

### User Story 6 — El costo de todos los modelos LLM se registra correctamente en BD (Priority: P1) [DT-040]

El gateway LLM actualmente registra `cost_usd = 0.0` para modelos sin entrada en `_PRICING` — incluyendo todos los modelos Gemini (vía Google AI Studio) y cualquier modelo OpenRouter nuevo no enumerado explícitamente. El sistema tiene 4 tiers de modelo (`free`, `free_alt`, `synth`, `paid`) y el registro de costo es incorrecto para todos los modelos de pago no catalogados.

**Why this priority**: Un dato de negocio incorrecto en BD da falsa confianza al tomar decisiones de presupuesto y selección de modelos. El problema afecta a todos los providers, no solo a Gemini.

**Independent Test**: Invocar el gateway con modelos de distintos tiers; verificar en BD que (a) los modelos `:free` registran `cost_usd = 0.0`, (b) los modelos de pago registran `cost_usd > 0.0`, (c) los modelos no reconocidos registran `cost_usd = None` con log `WARNING`.

**Acceptance Scenarios**:

1. **Given** el gateway configurado con un modelo `gemini-*` (cualquier variante: flash-lite, flash, pro), **When** se realiza una invocación LLM exitosa, **Then** el registro en BD contiene `cost_usd > 0.0`.
2. **Given** el gateway configurado con un modelo OpenRouter de pago (ej. `google/gemma-3-27b-it`), **When** se realiza una invocación exitosa, **Then** el registro en BD contiene `cost_usd > 0.0`.
3. **Given** cualquier modelo cuyo identificador termina en `:free` (ej. `nvidia/nemotron-*:free`, `meta-llama/*:free`), **When** se realiza una invocación, **Then** el registro en BD contiene `cost_usd = 0.0` sin necesidad de tener una entrada explícita en la tabla.
4. **Given** la pricing table del gateway, **When** se lista su contenido, **Then** existen entradas explícitas para los modelos de pago conocidos del proyecto (`gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`, `google/gemma-3-27b-it`, `google/gemma-3-12b-it`) más un fallback por prefijo `"gemini-"` para variantes con sufijo.
5. **Given** un modelo de pago no reconocido (sin entrada explícita y sin prefijo conocido), **When** el gateway lo invoca, **Then** registra `cost_usd = None` con log `WARNING` — nunca silenciosamente `0.0`.

---

### User Story 7 — gateway.py dividido en módulos cohesivos bajo 300L (Priority: P2) [DT-037]

`infrastructure/llm/gateway.py` supera el límite de 300 líneas definido en CLAUDE.md como señal de violación de SoC. El refactor lo divide en módulos con responsabilidades claras, manteniendo la interfaz pública intacta para que el resto del sistema no requiera cambios.

**Why this priority**: Un archivo de infraestructura central que mezcla routing, invocación, retry, circuit-breaker, logging y presupuesto es un punto único de fallos difícil de testear y de extender. El límite de 300L es una política del proyecto, no una aspiración.

**Independent Test**: `wc -l infrastructure/llm/gateway.py` — cada módulo resultante debe tener menos de 300 líneas; la interfaz pública del gateway (la clase o función principal que el resto de la app usa) debe seguir importándose desde la misma ruta.

**Acceptance Scenarios**:

1. **Given** el refactor completado, **When** se mide `wc -l` sobre cada archivo resultante en `infrastructure/llm/`, **Then** ningún archivo supera 300 líneas.
2. **Given** cualquier módulo fuera de `infrastructure/llm/` que importaba del gateway antes del refactor, **When** se ejecuta el sistema tras el refactor, **Then** no requiere cambios en sus imports ni en su lógica (la interfaz pública no cambió).
3. **Given** la suite de tests existente del gateway, **When** se ejecuta tras el refactor, **Then** todos los tests pasan sin modificación.

---

### User Story 8 — generate_informe.py dividido bajo 300L con API pública intacta (Priority: P2) [DT-039]

`domain/generate_informe.py` tiene 576 líneas y mezcla la orquestación del DAG completo con la lógica de los nodos N0, N1 y N2. El refactor separa estas responsabilidades en módulos distintos sin cambiar la firma de `generate_informe()`.

**Why this priority**: El módulo de orquestación central del dominio no debe ser un monolito. La mezcla de capas hace imposible testear nodos individuales o sustituir uno sin tocar el orquestador.

**Independent Test**: `wc -l domain/generate_informe.py` — debe ser menor de 300L tras el refactor; la función `generate_informe()` debe seguir importable desde `domain.generate_informe`.

**Acceptance Scenarios**:

1. **Given** el refactor completado, **When** se mide `wc -l` sobre cada archivo resultante en `domain/`, **Then** ninguno supera 300 líneas.
2. **Given** la función `generate_informe()`, **When** se compara su firma antes y después del refactor, **Then** es idéntica: mismos parámetros, mismo tipo de retorno.
3. **Given** los tests unitarios de `domain/` existentes, **When** se ejecutan tras el refactor, **Then** todos pasan sin modificación.
4. **Given** el pipeline E2E (US1), **When** se ejecuta tras el refactor de `generate_informe.py`, **Then** produce el mismo resultado que antes del refactor (zero regresiones funcionales).

---

### User Story 9 — Cobertura de tests en domain/ alcanza el 80% mínimo (Priority: P2)

La última medición de cobertura en `domain/` fue 69% (base F19). CLAUDE.md establece 80% como mínimo obligatorio. Los módulos más descubiertos reciben tests nuevos hasta alcanzar ese umbral.

**Why this priority**: La cobertura mínima es una política del proyecto, no una aspiración. Los módulos de dominio sin tests son una deuda que crece con cada feature y bloquea el refactor seguro de DT-037/DT-039.

**Independent Test**: `pytest --cov=domain --cov-report=term-missing tests/` — la línea `TOTAL` del reporte debe mostrar ≥80%.

**Acceptance Scenarios**:

1. **Given** la suite de tests tras agregar los tests nuevos, **When** se ejecuta `pytest --cov=domain`, **Then** el porcentaje de cobertura total de `domain/` es ≥80%.
2. **Given** los módulos de `domain/` con cobertura más baja identificados en la medición inicial, **When** se agregan los tests nuevos, **Then** cada módulo que estaba por debajo del 80% tiene al menos un test que cubre su happy path y al menos un caso de error.
3. **Given** los tests nuevos de cobertura, **When** se ejecutan junto con los tests existentes, **Then** no hay conflictos, duplicaciones ni tests que fallen por interferencia entre sí.

---

### Edge Cases

- ¿Qué ocurre si la BD está caída cuando corre la integración E2E? → El test debe fallar limpiamente con mensaje indicando el prerequisito, no con un traceback críptico.
- ¿Qué ocurre si Ollama no está corriendo en el host? → El test E2E debe detectar esto al inicio y abortar con mensaje accionable, no ejecutar parcialmente.
- ¿Qué ocurre si los checkpoints del sector están corruptos en BD? → US2/AC3 cubre esto: regenerar en lugar de usar datos inválidos.
- ¿Qué ocurre si el `ThreadPoolExecutor` tiene más workers que sub-módulos? → Los threads sobrantes no ejecutan nada; el resultado es el mismo 3 resultados.
- ¿Qué ocurre si `documentos_sectoriales/FuentesExternas/` contiene archivos de un sector que ya no se analiza? → Se documenta en el README como "archivo histórico"; no se borra sin verificar que no está indexado en pgvector.
- ¿Qué ocurre si un modelo Gemini devuelve un error de cuota durante el E2E de DT-040? → El test debe distinguir entre "no se intentó cobrar" (bug DT-040) y "se intentó pero falló por cuota" (comportamiento correcto del fallback).
- ¿Qué ocurre si `app.py` importa de `data/` a través de un módulo intermediario no documentado? → El grep de US5/AC1 debe capturarlo; el fix debe trazar la cadena completa.
- ¿Qué ocurre si el refactor de `gateway.py` cambia el comportamiento del circuit breaker o el retry? → Los tests existentes del gateway deben detectarlo; zero cambio de comportamiento es un requisito duro del refactor.

---

## Requirements *(mandatory)*

### Functional Requirements

**Integración E2E (US1–US4)**

- **FR-001**: El sistema DEBE completar el pipeline completo N0→N1→N2 para la empresa del `IntegrationFixture` (sembrada con `run_key` de prefijo `__test__`) sin lanzar excepción, produciendo un `InformePiloto` con todos los capítulos presentes (con contenido o párrafo de ausencia estándar, nunca `None`).
- **FR-002**: El pipeline DEBE persistir checkpoints para `cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups` y `cap_2_2` en la tabla de checkpoints de BD al completar cada nodo N1.
- **FR-003**: El documento final ensamblado DEBE contener la sección `## 2.2. División de Competidores` entre `## 2.1.` y la sección posterior (`## 2.3.` o `## 2.4.`), sin heading duplicado.
- **FR-004**: El orquestador DEBE detectar checkpoints sectoriales existentes (`cap2_21_*`) en BD y reutilizarlos en la segunda corrida del mismo sector, sin re-invocar el LLM para Cap 2.1.
- **FR-005**: La reutilización de cache sectorial DEBE respetar el flag `retrieval_suficiente`: si todos los checkpoints tienen `retrieval_suficiente=False`, el sistema DEBE regenerar Cap 2.1 en lugar de reutilizar.
- **FR-006**: `Generate21Startups` DEBE poder ejecutarse desde un thread de `ThreadPoolExecutor` usando `db_factory` sin producir errores de sesión BD (`DetachedInstanceError`, `InvalidRequestError` u equivalentes).
- **FR-007**: Cada thread del `ThreadPoolExecutor` DEBE crear su propia sesión de BD independiente mediante `db_factory`; nunca compartir una sesión entre threads.
- **FR-008**: El archivo vacío `1` en la raíz del repositorio DEBE ser eliminado del working tree y del historial de git.
- **FR-009**: El directorio `documentos_sectoriales/FuentesExternas/` DEBE tener un `README.md` que documente su propósito, o ser eliminado si está vacío.
- **FR-010**: Los tests de integración E2E DEBEN verificar al inicio que la BD (puerto 5434) y el LLM configurado están accesibles; si no lo están, el test DEBE saltarse con `pytest.skip` y mensaje accionable, no fallar con error críptico.
- **FR-011**: Los tests de integración DEBEN vivir en `tests/integration/` con su propio `conftest.py` que registre el marker y verifique prerequisitos (BD + LLM). El `pytest.ini` del proyecto DEBE incluir `addopts = -m "not integration"` para que `pytest tests/` sin flags adicionales nunca ejecute tests de integración.

**Deuda estructural (US5–US9)**

- **FR-012**: `presentation/app.py` NO DEBE contener imports directos de módulos bajo `data/`. Toda interacción con datos DEBE pasar por un caso de uso o servicio en `domain/`. [DT-038]
- **FR-013**: El gateway LLM DEBE registrar en BD `cost_usd > 0.0` para cada invocación exitosa a cualquier modelo de pago (Gemini o OpenRouter). [DT-040]
- **FR-014**: El mecanismo de lookup de precio DEBE funcionar con tres reglas en orden de precedencia: (1) match exacto en `_PRICING`; (2) para modelos sin match exacto cuyo identificador termina en `:free` → precio `(0.0, 0.0)` automático; (3) para modelos Gemini sin match exacto (prefijo `"gemini-"`) → precio de fallback `gemini-2.5-flash-lite`. La tabla `_PRICING` DEBE contener entradas explícitas para: `gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`, `google/gemma-3-27b-it`, `google/gemma-3-12b-it`. [DT-040]
- **FR-015**: Para modelos que no satisfacen ninguna de las tres reglas de FR-014, el gateway DEBE registrar `cost_usd = None` (tipo `float | None`) con log `WARNING`, nunca `0.0` silencioso. `CallRecord.costo_usd` cambia de `float` a `float | None`; `CostTracker.total_cost()` suma solo records donde `costo_usd is not None`; se añade `CostTracker.has_unknown_pricing() -> bool`. Los consumidores externos de `CostTracker` no requieren cambios. [DT-040]
- **FR-016**: Ningún archivo bajo `infrastructure/llm/` resultante del refactor de `gateway.py` DEBE superar 300 líneas. La interfaz pública (clase/función principal) DEBE seguir importable desde la misma ruta. [DT-037]
- **FR-017**: Ningún archivo bajo `domain/` resultante del refactor de `generate_informe.py` DEBE superar 300 líneas. La firma de `generate_informe()` NO DEBE cambiar. [DT-039]
- **FR-018**: La cobertura de tests sobre el paquete `domain/` DEBE ser ≥80% medida con `pytest --cov=domain`.

### Key Entities

- **IntegrationFixture**: Empresa de prueba con sector GICS y lista de competidores sembrados en BD por un script de seed; identificada por un `run_key` con prefijo `__test__` para distinguirla de datos de producción; eliminada en el teardown del test.
- **SectorCache**: Conjunto de checkpoints `cap2_21_*` persistidos bajo una clave sectorial (`sector_gics_code:sub_gics`); la entidad que FR-004 debe detectar y reutilizar.
- **OrphanArtifact**: Archivo o directorio en el repositorio sin propósito documentado ni referencia en specs, código o configuración.
- **PricingTable**: Estructura en el gateway LLM que mapea identificador de modelo → costo por token (input/output). Actualmente no tiene entradas para modelos `gemini-*`.
- **UseCaseLayer**: Módulos en `domain/` que exponen operaciones de negocio a `presentation/`; actualmente inexistentes para las funciones que `app.py` llama directamente a `data/`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Integración E2E**

- **SC-001**: El pipeline E2E completa para la empresa de prueba en menos de 120 segundos en condiciones normales de red y con modelos configurados (excluyendo tiempo de descarga de modelos).
- **SC-002**: El 100% de los checkpoints esperados (`cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups`, `cap_2_2`) están presentes en BD tras una corrida E2E exitosa.
- **SC-003**: La segunda corrida del mismo sector completa sin invocar el LLM para Cap 2.1 — verificable mediante un spy sobre el método de invocación del LLM wrapper que confirma que el contador de llamadas no aumenta durante la segunda corrida.
- **SC-004**: Los tres sub-módulos de Cap 2.1 corren concurrentemente sin producir ningún error de sesión BD en 10 ejecuciones consecutivas del test de concurrencia.
- **SC-005**: 0 archivos huérfanos sin propósito documentado en el repositorio tras ejecutar las tareas de limpieza.
- **SC-006**: Los tests de integración se pueden ejecutar independientemente de los tests unitarios; `pytest tests/` (sin flags adicionales) no requiere BD ni LLM activos.

**Deuda estructural**

- **SC-007**: `grep -rn "from data\." presentation/` devuelve 0 resultados tras el fix de DT-038.
- **SC-008**: El campo `cost_usd` en BD para cualquier corrida con modelo de pago (Gemini o OpenRouter paid) tiene valor >0.0 tras el fix de DT-040. Los modelos `:free` registran exactamente `0.0`. Los modelos no reconocidos registran `None` con `WARNING` en logs — verificable en la tabla de historial de invocaciones.
- **SC-009**: `wc -l` sobre cada archivo resultante del refactor de `gateway.py` (DT-037) muestra menos de 300 líneas en todos los casos.
- **SC-010**: `wc -l` sobre cada archivo resultante del refactor de `generate_informe.py` (DT-039) muestra menos de 300 líneas en todos los casos.
- **SC-011**: `pytest --cov=domain --cov-report=term` muestra cobertura total ≥80% tras agregar los tests nuevos.
- **SC-012**: La suite completa de tests (unitarios + nuevos de cobertura) pasa en verde tras todos los refactors — zero regresiones introducidas.

---

## Clarifications

### Session 2026-08-21

- Q: ¿Qué estrategia de datos deben usar los tests E2E de US1 y US2 para trabajar con la base de datos? → A: Fixture de sector dedicado — seed script inserta empresa de prueba + competidores bajo `run_key` con prefijo `__test__`; teardown los elimina; nunca se tocan datos de producción.
- Q: ¿Dónde deben vivir los tests de integración E2E dentro del repositorio? → A: Subdirectorio `tests/integration/` con `conftest.py` propio; `pytest.ini` con `addopts = -m "not integration"` para excluirlos por defecto.
- Q: ¿Cómo debe verificar el test de US2 que la segunda corrida no invocó el LLM para Cap 2.1? → A: Spy/monkeypatch sobre `OpenRouterGatewayLLM._generate` (método hoja que realiza el HTTP call real) — contador de llamadas verificado a 0 para la segunda corrida de Cap 2.1. Es el punto más preciso sin acoplarse a LangChain internals.

### Session 2026-09-15

- Q: ¿Qué tan granular debe ser el refactor de `gateway.py` (DT-037)? → A: División mínima en 3 módulos: routing/configuración, invocación/retry/circuit-breaker, logging/presupuesto. La clase o función principal que el resto de la app importa sigue en `gateway.py` (puede ser un re-export).
- Q: ¿Los use cases de DT-038 deben ser clases o funciones? → A: Funciones en módulos de `domain/` es suficiente — no se requiere patrón Command ni inyección de dependencias compleja. El criterio es que `app.py` no importe nada de `data/` directamente.
- Q: ¿Cuáles son los modelos Gemini que deben tener entrada en la pricing table (DT-040)? → A: Al menos `gemini-flash-lite`, `gemini-flash` y `gemini-pro`. El identificador exacto que usa el gateway (el string en `.env`) es el que debe aparecer en la tabla.
- Q: ¿Cómo debe implementarse el lookup de precio Gemini en `_PRICING` dado que el model string puede tener variantes con sufijo? → A: Añadir las 3 entradas canónicas (`gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`) más un fallback por prefijo `"gemini-"` que aplica el precio de `gemini-2.5-flash-lite` a cualquier model string sin match exacto.
- Q: ¿Debe `CallRecord.costo_usd` aceptar `None` para modelos sin precio conocido? → A: Sí — `float | None`. `total_cost()` suma solo records no-None; se añade `has_unknown_pricing() -> bool`. Los consumidores externos no cambian.
- Q: ¿Sobre qué método exacto se instala el spy para verificar cache hit de Cap 2.1 en SC-003? → A: `OpenRouterGatewayLLM._generate` — método hoja que hace el HTTP call; detecta ausencia de invocación real sin interferir con Cap 2.2.
- Q: ¿El fix de DT-040 debe cubrir solo Gemini o también todos los modelos OpenRouter? → A: Todos los modelos del proyecto. Reglas en cascada: (1) match exacto en `_PRICING`; (2) sufijo `:free` → `(0.0, 0.0)` automático; (3) prefijo `"gemini-"` → fallback flash-lite; (4) desconocido → `None` + WARNING.

---

## Assumptions

- La instancia PostgreSQL compartida está disponible en `localhost:5434` con el schema `informes_ic` ya migrado.
- Ollama está corriendo en el host en `http://127.0.0.1:11434` con al menos un modelo de texto configurado en `.env`.
- Los tests E2E (US1, US2) usan un fixture de sector dedicado: un script de seed inserta la empresa de prueba y al menos 3 competidores bajo un `run_key` con prefijo `__test__`; el teardown los elimina. No se usan ni modifican datos de producción.
- Los tests de integración E2E se marcan con `@pytest.mark.integration` y requieren `pytest -m integration` para correr; no corren en CI sin infraestructura.
- El archivo `1` es un artefacto de debug sin contenido útil y puede eliminarse sin pérdida de información.
- `documentos_sectoriales/FuentesExternas/` puede contener PDFs que ya están indexados en pgvector — antes de eliminar cualquier archivo, se verifica en BD.
- Los tests de concurrencia (US3) pueden usar una `db_factory` real (con `SessionLocal`) o una fake con tracking de instancias; se prefiere la fake para evitar dependencia de BD en tests unitarios.
- El refactor de `gateway.py` (DT-037) y `generate_informe.py` (DT-039) es comportamiento-neutro: zero cambios de lógica, solo reorganización de archivos. Si se detecta un bug durante el refactor, se documenta y se corrige en un commit separado.
- El fix de DT-038 no requiere crear una capa de servicios completa con inyección de dependencias — funciones simples en `domain/` que envuelvan las llamadas a `data/` son suficientes.
- Los precios de los modelos Gemini en la pricing table son aproximaciones (precio público en el momento de implementación); lo que importa es que sean >0 y documentados, no que sean exactos al centavo.
