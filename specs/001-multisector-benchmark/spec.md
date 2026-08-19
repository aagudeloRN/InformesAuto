# Feature Specification: Multi-sector en Benchmarking — Tier Global y Fichas (DT-UI04f)

**Feature Branch**: `spec-driven-experiment`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Multi-sector en tier Global y Fichas del benchmarking (DT-UI04f)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Benchmarking multi-sector sin duplicados (Priority: P1)

Un analista genera el informe de benchmarking para una empresa que opera en
varios sectores GICS (ej. alimentos y confitería). El sistema consulta
competidores de **todos** los sectores declarados y entrega una lista unificada,
sin repetir empresas que estén clasificadas en más de uno de esos sectores,
ordenada de mayor a menor relevancia.

**Why this priority**: Es el corazón de la funcionalidad. Sin esto, empresas
multi-sector pierden competidores relevantes y el análisis queda incompleto.

**Independent Test**: Invocar el caso de uso de benchmarking con una empresa
de dos sectores distintos y verificar que el resultado contiene competidores
de ambos sectores, sin entradas duplicadas, y en orden de relevancia descendente.

**Acceptance Scenarios**:

1. **Given** una empresa con sectores `["1040", "1050"]`, **When** se solicita la
   lista de competidores globales con límite 6, **Then** el sistema retorna hasta
   6 competidores de ambos sectores combinados, sin duplicados, ordenados por
   relevancia descendente.
2. **Given** un competidor presente en los dos sectores, **When** se ejecuta la
   búsqueda, **Then** ese competidor aparece exactamente una vez en el resultado.
3. **Given** sectores donde ningún competidor existe, **When** se ejecuta la
   búsqueda, **Then** el sistema retorna lista vacía sin error.

---

### User Story 2 - Exclusión de empresa focal por aliases (Priority: P2)

El analista busca competidores de "NOEL SAS", pero en el directorio la empresa
está registrada como "Compañía de Galletas NOEL". El sistema reconoce que ambas
referencias corresponden a la misma entidad (vía aliases) y excluye
correctamente la empresa focal de los resultados.

**Why this priority**: Sin exclusión correcta por aliases, la empresa analizada
puede aparecer como su propio competidor, invalidando el análisis.

**Independent Test**: Ejecutar búsqueda de competidores indicando la empresa
focal por un nombre que coincide con uno de sus aliases, y confirmar que
la empresa no aparece en los resultados bajo ninguna de sus denominaciones.

**Acceptance Scenarios**:

1. **Given** la empresa focal "NOEL SAS" con alias "Compañía de Galletas NOEL"
   en el directorio, **When** se buscan competidores en su sector, **Then**
   "Compañía de Galletas NOEL" no aparece en los resultados.
2. **Given** una empresa sin aliases registrados, **When** se buscan
   competidores, **Then** la exclusión funciona por nombre exacto igual que antes.

---

### User Story 3 - Compatibilidad con empresa de un solo sector (Priority: P3)

Un analista genera el informe para una empresa clasificada en un único sector
GICS. El flujo existente funciona sin cambios: la interfaz puede seguir
enviando un único código de sector y los resultados son idénticos a los
anteriores.

**Why this priority**: Garantiza que el cambio no rompe los flujos ya
productivos para empresas mono-sector.

**Independent Test**: Ejecutar el benchmarking con un único sector y comparar
los resultados contra el comportamiento documentado antes del cambio; deben
ser idénticos.

**Acceptance Scenarios**:

1. **Given** una empresa con un único sector `["1040"]`, **When** se solicita
   el listado de competidores, **Then** el resultado es equivalente al
   comportamiento previo (mismos competidores, mismo orden).
2. **Given** los tests de regresión existentes de `entidad_repo`, **When**
   se ejecutan sin modificación, **Then** todos pasan en verde.

---

### Edge Cases

- ¿Qué ocurre si dos sectores distintos retornan el mismo competidor con
  scores de relevancia diferentes? → Se conserva la entrada de mayor
  relevancia; la otra se descarta en la deduplicación.
- ¿Qué ocurre si la lista de sectores está vacía? → El sistema retorna lista
  vacía sin error (comportamiento defensivo).
- ¿Qué ocurre si `aliases` es `null` o el campo no está presente en la
  entidad? → La exclusión recae únicamente en el nombre canónico; no se
  lanza excepción.
- ¿Qué ocurre si `entidad_repo.py` supera 300 líneas tras el cambio? → Los
  query builders se extraen a un módulo separado antes de cerrar la tarea.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE aceptar una lista de uno o más códigos de sector
  GICS al consultar competidores (tier global, locales y atributos de fichas).
- **FR-002**: Las consultas de competidores DEBEN cubrir todos los sectores de
  la empresa focal en una sola operación, sin requerir múltiples llamadas
  secuenciales (una por sector).
- **FR-003**: Los resultados DEBEN estar deduplicados por identificador único de
  entidad; si la misma empresa aparece en varios sectores, solo se incluye una vez.
- **FR-004**: Los resultados deduplicados DEBEN estar ordenados por relevancia
  descendente, conservando la entrada de mayor score cuando hay colisión.
- **FR-005**: La empresa focal DEBE ser excluida de los resultados considerando
  tanto su nombre canónico como todos sus aliases registrados.
- **FR-006**: El comportamiento cuando se pasa una lista de un único sector DEBE
  ser idéntico al comportamiento anterior (compatibilidad hacia atrás).
- **FR-007**: Todas las consultas DEBEN operar bajo el schema `informes_ic`;
  ninguna tabla puede referenciarse sin prefijo de schema.
- **FR-008**: Si el archivo principal del repositorio supera el límite de 300 líneas
  tras el cambio, los constructores de queries DEBEN extraerse a un módulo auxiliar
  dentro de la misma capa de datos.
- **FR-009**: Los casos de uso que invocan los métodos afectados DEBEN actualizar
  sus llamadas para pasar la lista completa de sectores GICS de la empresa focal.

### Key Entities

- **Entidad**: Empresa registrada en el directorio. Atributos relevantes:
  `entidad_id` (identificador único), `nombre` (nombre canónico), `sector`
  (código GICS), `aliases` (lista de denominaciones alternativas, JSONB).
- **Competidor**: Entidad identificada como par competitivo de la empresa focal
  en uno o más de sus sectores GICS. Tiene un score de relevancia asociado.
- **Empresa focal**: La empresa analizada en el informe; debe ser excluida de
  su propio listado de competidores.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una búsqueda para empresa con N sectores retorna resultados en
  un tiempo similar a una búsqueda mono-sector (sin degradación apreciable).
- **SC-002**: El 100 % de competidores relevantes en cualquiera de los sectores
  declarados aparece en el resultado combinado, sin entradas duplicadas.
- **SC-003**: La empresa focal no aparece en los resultados bajo ninguna de sus
  denominaciones registradas (nombre canónico ni aliases).
- **SC-004**: El 100 % de los tests de regresión existentes de `entidad_repo`
  pasa sin modificación de los tests.
- **SC-005**: Las herramientas de calidad de código (linting y suite rápida de
  tests) reportan cero errores tras el cambio.

## Assumptions

- El campo `aliases` ya existe en la tabla `entidad` como tipo JSONB; si no
  existe, se requiere una migración previa que está fuera del scope de esta
  funcionalidad.
- La ordenación por relevancia utiliza el mismo criterio ya implementado
  (campo de score o ranking existente); no se introduce un nuevo algoritmo
  de ranking.
- Solo se modifican los métodos correspondientes a tier global, competidores
  locales y atributos de fichas; el tier regional queda fuera de scope.
- La clasificación GICS de la empresa focal (fuente de la lista de sectores)
  ya retorna una lista; esta funcionalidad solo consume esa lista sin modificarla.
- No se modifican las firmas de `classify_gics.py` ni de `chain_02_gics.py`.
- La deduplicación ocurre en la capa de repositorio o en la capa de dominio;
  la presentación recibe siempre datos ya deduplicados.
