# Feature Specification: Cap 2.2 — División de Competidores (Grupos Estratégicos)

**Feature Branch**: `spec-driven-experiment`

**Created**: 2026-08-20

**Status**: Draft

**Input**: Subcapítulo 2.2 del informe de Inteligencia Competitiva — matriz de grupos estratégicos 2×2 que clasifica exhaustivamente los competidores de 2.1 por enfoque de mercado y modelo operativo, con síntesis de presión competitiva.

## Contexto del Componente

### Estado de implementación existente (hallazgos pre-spec)

Antes de redactar este spec se auditó el repositorio. Resultado:

- **No existe implementación de Cap 2.2**: no hay `chain_cap2_22_*.py`, `generate_22_*.py`, ni tipos `Cap22*` en `shared/types.py`.
- **Patrón existente (blueprint)**: Cap 2.1 sigue el ciclo `chain → use_case → assembler → tipos` (ver `chain_cap2_21_globales.py`, `generate_21_jugadores.py`, `seccion21_assembler.py`, `Cap21Jugadores` en `shared/types.py`). Cap 2.2 debe replicar este patrón en la misma capa.
- **Datos disponibles**: la salida de Cap 2.1 ya produce un dataset estructurado de competidores por tier (globales / regionales / startups) con atributos de ficha. Esa estructura es el input primario de Cap 2.2.
- **No hay prompt doc**: no existe `prompt-02b-division-competidores.md` ni equivalente en `docs/prompts/`.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Clasificación exhaustiva en matriz 2×2 (Priority: P1)

El analista solicita un informe para una empresa. Una vez generado Cap 2.1 (lista cerrada de competidores), el sistema genera automáticamente el subcapítulo 2.2 con la matriz de grupos estratégicos que clasifica **cada** empresa de 2.1 en uno de los cuatro cuadrantes (Masivo/Tradicional, Masivo/Innovador, Nicho/Tradicional, Nicho/Innovador).

**Why this priority**: Es el entregable central del subcapítulo; sin él la sección 2.2 no existe.

**Independent Test**: Se puede probar con un JSON de Cap 2.1 de prueba (fixture) sin depender del resto del informe; la salida debe contener los cuatro cuadrantes y la suma de nombres en ellos debe ser igual al total de empresas en el fixture.

**Acceptance Scenarios**:

1. **Given** un dataset de Cap 2.1 con N empresas (N ≥ 1) y el contexto de Cap 1 disponibles, **When** se invoca la generación de Cap 2.2, **Then** el resultado contiene un párrafo introductorio, la tabla 2×2 con N nombres distribuidos entre los cuatro cuadrantes, y la sección "Síntesis de Presión Competitiva" con al menos dos párrafos analíticos.
2. **Given** un cuadrante que no recibe ninguna empresa según el LLM, **When** se genera la tabla, **Then** la celda correspondiente muestra `(ninguno)` —no se omite el cuadrante.
3. **Given** un dataset de Cap 2.1 con empresas en los tres tiers (globales, regionales, startups), **When** se clasifica, **Then** el total de menciones de empresa en la tabla es igual al total de empresas únicas en el input (cobertura exhaustiva).

---

### User Story 2 — Grounding estricto: lista cerrada de empresas (Priority: P1)

El sistema garantiza que el LLM solo puede clasificar las empresas que ya están en el dataset de Cap 2.1 y no puede añadir nuevas marcas, startups ni competidores.

**Why this priority**: Un analista que entrega el informe a su cliente confía en que la sección 2.2 no introduce actores no validados. Una alucinación aquí destruye la credibilidad de todo el informe.

**Independent Test**: Se puede probar pasando un fixture mínimo de 3 empresas; se verifica que el markdown de salida no contiene ningún nombre que no esté en el fixture.

**Acceptance Scenarios**:

1. **Given** un fixture con 5 empresas conocidas, **When** se genera Cap 2.2, **Then** el markdown de salida no contiene ningún nombre de empresa ajeno a esas 5.
2. **Given** que el LLM propone clasificar una empresa no listada en 2.1, **When** el validador post-generación revisa la salida, **Then** ese nombre se elimina o se reemplaza por `(ninguno)` y se registra un warning en el log del informe.
3. **Given** que un atributo de una empresa (ej. modelo de licenciamiento) está ausente en el dataset, **When** el LLM lo referencia en la síntesis narrativa, **Then** el texto de la síntesis incluye "Dato no disponible en fuentes consultadas" para ese atributo, la empresa sigue clasificada en su cuadrante en la tabla 2×2, y `ClasificacionCompetidor.dato_no_disponible` se marca `True`.

---

### User Story 3 — Regeneración idempotente con retroalimentación del revisor (Priority: P2)

El analista (o el asistente revisor automático) puede solicitar la regeneración del subcapítulo 2.2 con comentarios de retroalimentación sin que el contenido de Cap 1 ni de Cap 2.1 sea alterado.

**Why this priority**: La arquitectura del sistema ya incluye un flujo de revisión+regeneración para otros capítulos; Cap 2.2 debe integrarse en ese flujo.

**Independent Test**: Enviar al módulo un feedback string arbitrario + los artefactos previos de Cap 1 y 2.1 (inalterados); verificar que la salida de Cap 2.2 cambia pero los checkpoints de Cap 1 y 2.1 permanecen intactos en BD.

**Acceptance Scenarios**:

1. **Given** un Cap 2.2 ya generado y un mensaje de feedback ("Añadir más énfasis en la presión de los entrantes deeptech"), **When** se solicita regeneración, **Then** el nuevo Cap 2.2 incorpora el feedback y los artefactos de Cap 1 y 2.1 no cambian.
2. **Given** una segunda regeneración consecutiva con el mismo feedback, **When** se ejecuta, **Then** el resultado es funcionalmente equivalente a la primera (idempotencia bajo mismo contexto).
3. **Given** que la regeneración falla (error de LLM, timeout o error de red), **When** el wrapper best-effort del orquestador captura la excepción, **Then** el Cap 2.2 anterior se conserva en BD intacto, y el documento muestra el párrafo de ausencia estándar de Cap 2.2 (`retrieval_suficiente=False`) como indicación visible al usuario de que la sección no pudo generarse; no se lanza excepción que rompa la corrida del informe.

---

### User Story 4 — Ausencia de datos en Cap 2.1 (Priority: P3)

Si Cap 2.1 está vacío o no superó el umbral de calidad (retrieval insuficiente), el sistema no intenta generar Cap 2.2 con datos inventados sino que inserta un párrafo de ausencia estándar.

**Why this priority**: Previene la generación de matrices con datos inexistentes; consistente con la regla de datos ausentes (ADR-002 / Constitución III).

**Independent Test**: Pasar un dataset de Cap 2.1 vacío al módulo y verificar que devuelve el texto de ausencia, no una matriz.

**Acceptance Scenarios**:

1. **Given** un dataset de Cap 2.1 con cero competidores, **When** se solicita Cap 2.2, **Then** el sistema devuelve un párrafo de ausencia estándar y no llama al LLM.
2. **Given** un dataset de Cap 2.1 con menos de 2 empresas, **When** se genera la matriz, **Then** el sistema la genera con los datos disponibles y advierte al usuario que la matriz puede no ser representativa.

---

### Edge Cases

- ¿Qué ocurre si todas las empresas caen en un solo cuadrante? → Los otros tres muestran `(ninguno)`.
- ¿Qué ocurre si la misma empresa tiene atributos contradictorios que la sitúan en dos cuadrantes? → El LLM elige el cuadrante más representativo; la duda queda registrada en el log del informe, no en la salida al usuario.
- ¿Qué ocurre si Cap 1 no está disponible (contexto de empresa analizada faltante)? → El módulo genera la síntesis de presión competitiva sin la conexión con el sector de la empresa analizada; la sección correspondiente señala que el contexto sectorial no estaba disponible.
- ¿Qué ocurre si el LLM devuelve JSON malformado? → El parser reintenta hasta 2 veces; si falla, inserta párrafo de ausencia y registra el error.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El módulo DEBE recibir como entrada el dataset estructurado de Cap 2.1 (lista de empresas con atributos de ficha por tier) y el contexto de Cap 1 (descripción de la empresa analizada, sector GICS, capacidades).
- **FR-002**: El módulo DEBE clasificar **todas** las empresas presentes en el input de 2.1 en exactamente uno de los cuatro cuadrantes de la matriz 2×2; ninguna empresa puede quedar sin clasificar.
- **FR-003**: El módulo NO DEBE incorporar nombres de empresas no presentes en el input de 2.1; un validador post-generación DEBE detectar y eliminar cualquier nombre ajeno.
- **FR-004**: Si un cuadrante no recibe empresas, DEBE mostrarse la celda con el literal `(ninguno)`; el cuadrante no se omite.
- **FR-005**: El módulo DEBE producir la salida en el formato markdown estandarizado: (1) párrafo introductorio, (2) tabla 2×2, (3) subsección "### Síntesis de Presión Competitiva" con dos párrafos analíticos.
- **FR-006**: Cuando el LLM no puede justificar un atributo específico de una empresa en la síntesis narrativa (sección "Síntesis de Presión Competitiva"), DEBE insertar el literal "Dato no disponible en fuentes consultadas" en el texto; no debe inferir ni completar datos. La tabla 2×2 siempre muestra solo el nombre de la empresa; el flag de atributo ausente se refleja como `dato_no_disponible = True` en `ClasificacionCompetidor` (visible en logs/metadatos, no en el markdown de la tabla).
- **FR-007**: El módulo DEBE soportar regeneración recibiendo retroalimentación textual sin alterar los artefactos persistidos de Cap 1 ni de Cap 2.1 en la base de datos.
- **FR-012**: Ante errores de red o rate limit (429) del proveedor LLM, el módulo DEBE propagar la excepción al orquestador (`generate_n1.py`) sin realizar el upsert del checkpoint; el Cap 2.2 previo en BD se conserva intacto. El retry de red/API es responsabilidad del orquestador, no del use_case.
- **FR-008**: Si el dataset de Cap 2.1 está vacío, el módulo DEBE devolver un párrafo de ausencia estándar sin invocar al LLM.
- **FR-009**: El identificador del modelo LLM utilizado DEBE leerse de la configuración del sistema (variable de entorno o tabla de routing); nunca debe estar escrito en el código.
- **FR-010**: El módulo DEBE persistir la salida generada (texto markdown + metadatos de clasificación) en el checkpoint de informe en BD antes de retornar al flujo de orquestación.
- **FR-011**: El módulo DEBE integrarse en el DAG del informe como nodo N1 dependiente de Cap 2.1 (que a su vez es N1 dependiente de Cap 1), sin bloquear la ejecución paralela de otros nodos N1.
- **FR-013**: El texto de Cap 2.2 (`cap_22_division.texto`) DEBE aparecer en el documento final ensamblado (docx/PDF) entre la sección 2.1 (Jugadores Clave) y la sección 2.3 (Mercado). La modificación de `src/ic/domain/assembler.py` para insertar este bloque está en scope para este feature.

### Key Entities

- **Cap22Input**: Datos de entrada — lista de empresas de Cap 2.1 (con tier y atributos de ficha) + contexto de empresa analizada de Cap 1.
- **CuadranteKey**: Identificador interno del cuadrante (enum de dominio); valores: `masivo_tradicional`, `masivo_innovador`, `nicho_tradicional`, `nicho_innovador`. Las etiquetas legibles de UI son: Masivo/Volumen × Jugadores Tradicionales/Entrantes Innovadores.
- **ClasificacionCompetidor**: Asignación de un competidor a un cuadrante; incluye nombre de empresa, `CuadranteKey` asignado, y flag de "dato no disponible" si la clasificación fue ambigua por falta de atributos.
- **Cap22Division**: Resultado completo — texto markdown de la sección 2.2 + lista de `ClasificacionCompetidor` + metadatos (N empresas procesadas, warnings de nombres ajenos detectados, flag `retrieval_suficiente`).
- **Cap22Checkpoint**: Registro persistido en BD del Cap 22 generado para un informe específico (clave canónica `"cap_2_2"`); permite recuperación y regeneración idempotente.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las empresas del dataset de Cap 2.1 quedan clasificadas en la matriz 2×2 en cada ejecución (cobertura exhaustiva verificable en tests automáticos).
- **SC-002**: El validador de lista cerrada detecta y elimina el 100% de los nombres de empresa ajenos al dataset de 2.1 en tests con fixtures controlados.
- **SC-003**: La sección 2.2 completa (párrafo + tabla + síntesis) se genera en menos de 60 segundos para datasets de hasta 30 competidores en condiciones normales de red.
- **SC-004**: La regeneración con retroalimentación no altera los checkpoints de Cap 1 ni de Cap 2.1 en BD en el 100% de los casos (verificable por hash de contenido antes/después).
- **SC-005**: Los analistas que revisan el informe confirman que la sección 2.2 es coherente con la lista de competidores de 2.1 (sin actores nuevos ni ausentes) en el 100% de los informes piloto.
- **SC-006**: Cobertura de tests unitarios en el módulo ≥ 80%, incluyendo casos de cuadrante vacío, lista cerrada violada, y dataset de Cap 2.1 vacío.

---

## Assumptions

- Los datos de Cap 2.1 están disponibles como objeto Python (`Cap21Jugadores` o estructura equivalente) antes de invocar este módulo; Cap 2.2 no reintenta retrieval de competidores.
- El contexto de Cap 1 está disponible como texto o dict con al menos: nombre de empresa, sector GICS, y descripción de capacidades; si no está disponible, la síntesis de presión competitiva omite la conexión sectorial.
- La clasificación en cuadrantes (volumen vs. nicho; tradicional vs. innovador) la realiza el LLM usando los atributos de ficha de 2.1 como evidencia; no se usa un clasificador determinista propio.
- La búsqueda web complementaria (para enriquecer atributos faltantes de empresas ya listadas) es opcional y se activa solo si se configura explícitamente; por defecto el módulo trabaja con los datos ya presentes en el dataset.
- El formato markdown de salida es exactamente el especificado en la descripción del feature (párrafo + tabla 2×2 + subsección síntesis); no hay variantes de formato.
- La integración con el asistente revisor sigue el mismo patrón que otros capítulos revisables del sistema (feedback string → regeneración → comparación de artefactos).
- Este módulo no tiene UI propia; la presentación en Streamlit la maneja la capa `presentation/` existente que ya renderiza el markdown de cada sección.

---

## Clarifications

### Session 2026-08-21

- Q: ¿Debe el texto de Cap 2.2 incluirse en el documento final ensamblado y está esa lógica de ensamblaje en scope para este feature? → A: Opción A — sí, incluir en el documento final ensamblado (docx/PDF) entre § 2.1 y § 2.3; añadir FR-013; `assembler.py` está en scope de este feature.
- Q: Cuando la generación de Cap 2.2 falla en tiempo de ejecución, ¿qué debe recibir el usuario dado el modelo best-effort? → A: Opción B — el wrapper captura la excepción y produce un `Cap22Division` con párrafo de ausencia estándar (`retrieval_suficiente=False`); el documento muestra la sección 2.2 con la nota de ausencia; el checkpoint previo en BD se conserva intacto; US3/AC3 actualizado.

### Session 2026-08-20

- Q: ¿Cuáles son los nombres canónicos para el enum de cuadrantes y el tipo de salida? → A: Opción B — usar `CuadranteKey` (enum interno) y `Cap22Division` (tipo de salida), alineando spec con plan y data-model.
- Q: ¿Dónde aparece el literal "Dato no disponible en fuentes consultadas" en la salida? → A: Opción B — solo en la síntesis narrativa (sección "Síntesis de Presión Competitiva"); la tabla 2×2 siempre muestra el nombre de la empresa; el flag de dato ausente vive en `ClasificacionCompetidor.dato_no_disponible = True` como metadata interna (logs, no markdown).
- Q: ¿Qué hace el módulo ante error de red o rate limit (429) del LLM? → A: Opción A — propagar la excepción al orquestador; el upsert no ocurre; el Cap 2.2 previo en BD se conserva. El retry de red/API es responsabilidad del orquestador.
