# Feature Specification: Cap 2.1 — Activar Sub-módulos Modulares y Numeración de Secciones

**Feature Branch**: `003-cap21-activar-submodulos`

**Created**: 2026-08-20

**Status**: Draft

**Input**: El informe generado muestra la información de competidores de forma continua, sin dividirla en las tres sub-secciones numeradas (2.1.1 Referentes Globales, 2.1.2 Referentes Regionales, 2.1.3 Startups y Disruptores). Adicionalmente, los sub-módulos modulares implementados (Globales, Regionales, Startups como piezas independientes) nunca se invocan en el flujo real de generación porque el pipeline principal no los conecta. La información de competidores tampoco se almacena para reutilización entre empresas del mismo sector.

---

## Contexto del Negocio

El Capítulo 2.1 del informe de inteligencia competitiva fue modularizado en tres sub-módulos independientes (Referentes Globales, Referentes Regionales, Startups y Disruptores), cada uno con su propia fuente de datos, lógica de recuperación y resultado persistible. Sin embargo, en el flujo real de generación de informes el pipeline principal sigue utilizando el generador monolítico anterior: los tres sub-módulos nunca se activan.

Consecuencias observadas en la UI:
1. La sección 2.1 muestra empresas sin sub-encabezados numerados, haciéndola difícil de navegar.
2. La información curada de competidores (búsquedas web por candidato, perfiles EMIS) se descarta al terminar la corrida — no se almacena para reutilización.
3. El analista no puede distinguir visualmente entre referentes globales, regionales y startups.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Sub-secciones numeradas en el informe (Priority: P1)

El analista genera un informe para una empresa del sector Alimentos. Al revisar el Capítulo 2.1, ve tres sub-secciones claramente demarcadas: **2.1.1. Referentes Globales**, **2.1.2. Referentes Regionales LatAm/Colombia** y **2.1.3. Startups y Disruptores del sector**, cada una con su propio encabezado numerado y el contenido de las empresas correspondientes debajo.

**Acceptance Scenarios**:

1. **Given** un informe generado exitosamente, **When** el analista lee la sección 2.1, **Then** encuentra exactamente tres sub-encabezados numerados en orden: `2.1.1. Referentes Globales`, `2.1.2. Referentes Regionales LatAm/Colombia` y `2.1.3. Startups y Disruptores del sector`.
2. **Given** alguno de los sub-módulos retorna ausencia (sin datos suficientes), **When** se ensambla el capítulo, **Then** ese sub-encabezado numerado no aparece en el texto (se omite junto con su contenido vacío), sin dejar brechas numeradas visibles.
3. **Given** los tres sub-módulos devuelven ausencia, **When** se ensambla el capítulo, **Then** aparece un único párrafo de ausencia bajo `## 2.1. Jugadores Clave` sin ningún sub-encabezado numerado.

---

### User Story 2 — Sub-módulos modulares activos en el pipeline (Priority: P1)

El analista genera un informe. El pipeline de generación invoca los tres sub-módulos independientes (Globales vía LLM+web, Regionales vía EMIS, Startups vía StartIA+web), cada uno ejecutándose con su propia lógica y fuente de datos. El resultado visible en el informe proviene de estos sub-módulos, no del generador monolítico anterior.

**Acceptance Scenarios**:

1. **Given** el pipeline de generación se ejecuta con los sub-módulos disponibles, **When** se genera la sección 2.1, **Then** el log de la corrida muestra que `Generate21Globales`, `Generate21Regionales` y `Generate21Startups` fueron invocados como partes independientes.
2. **Given** el sub-módulo Regionales no tiene documentos EMIS indexados para el sector, **When** se genera la sección 2.1, **Then** el sub-módulo Regionales genera un párrafo de ausencia y los otros dos sub-módulos continúan normalmente.
3. **Given** el pipeline ya generó la sección 2.1 para un sector, **When** se genera un nuevo informe para una empresa del mismo sector, **Then** los sub-módulos 2.1 se recuperan desde el cache sectorial sin repetir búsquedas web ni llamadas LLM (si el cache está disponible).

---

### User Story 3 — Almacenamiento de información de competidores para reutilización (Priority: P2)

El analista genera informes para dos empresas del mismo sector GICS. La segunda corrida reutiliza los perfiles de competidores globales y regionales ya recopilados en la primera, sin volver a lanzar búsquedas web ni llamadas LLM para los mismos candidatos.

**Acceptance Scenarios**:

1. **Given** se generó el sub-módulo Globales para el sector X, **When** se inicia una nueva corrida para otra empresa del mismo sector X, **Then** el sistema detecta el checkpoint `cap2_21_globales` existente y lo reutiliza sin re-ejecutar el sub-módulo.
2. **Given** el cache sectorial contiene los tres sub-módulos completos, **When** se genera la sección 2.1 para una empresa del mismo sector, **Then** el tiempo de generación de 2.1 es inferior a 5 segundos (solo lectura de cache, sin LLM ni web).
3. **Given** el pipeline inyecta correctamente el motor de base de datos y la clave de corrida, **When** finaliza la generación de cada sub-módulo, **Then** el resultado queda persistido bajo la clave sectorial `f"sector_{sector_gics_code}_{sub_gics or 'any'}"`.

---

### Edge Cases

- Si el motor de base de datos no está disponible en la corrida, los sub-módulos se ejecutan sin persistir checkpoint (modo degradado silencioso).
- Si el cache sectorial contiene datos de un sub-módulo pero no de los otros, los sub-módulos sin cache se ejecutan normalmente y sus resultados se suman al cache.
- Si el sub-módulo anterior (pre-modular) generó texto de 2.1 y el nuevo sistema no está activo, el informe debe seguir siendo válido (invariante de compatibilidad hacia atrás).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El pipeline principal de generación (`generate_n1.py`) DEBE instanciar y conectar los tres sub-módulos (`Generate21Globales`, `Generate21Regionales`, `Generate21Startups`) como el orquestador `Generate21Jugadores`, e inyectar este orquestador en `GenerateBenchmarking` antes de ejecutar la corrida.
- **FR-002**: Los sub-encabezados de cada sub-módulo DEBEN incluir numeración jerárquica: `### 2.1.1. Referentes Globales`, `### 2.1.2. Referentes Regionales LatAm/Colombia`, `### 2.1.3. Startups y Disruptores del sector`.
- **FR-003**: El pipeline DEBE inyectar el motor de base de datos (`engine`) y la clave de corrida (`run_key`) en `GenerateBenchmarking` para habilitar la persistencia del cache sectorial.
- **FR-004**: Los resultados de los tres sub-módulos DEBEN persistirse bajo la clave sectorial compuesta `f"sector_{sector_gics_code}_{sub_gics or 'any'}"` al finalizar cada sub-módulo, antes de que termine la corrida completa.
- **FR-005**: Si el cache sectorial contiene resultados previos para el sector de la empresa, DEBEN reutilizarse sin re-ejecutar los sub-módulos correspondientes.
- **FR-006**: Si algún sub-módulo retorna ausencia (sin datos suficientes), su sub-encabezado numerado NO DEBE aparecer en el texto ensamblado final.
- **FR-007**: La activación de los sub-módulos modulares NO DEBE cambiar la firma pública de `GenerateBenchmarking.execute()` ni romper los tests existentes del pipeline.

### Key Entities

- **Pipeline context (`ctx`)**: contiene `engine`, `run_key`, `llm`, `api_llm`, `empresa_id`, necesarios para construir e inyectar el orquestador.
- **Sector run key**: clave compuesta `f"sector_{sector_gics_code}_{sub_gics or 'any'}"` bajo la cual se almacenan los tres sub-módulos de 2.1 para reutilización.
- **Orquestador Generate21Jugadores**: pieza de conexión entre los tres sub-módulos y `GenerateBenchmarking`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El texto del Capítulo 2.1 en el informe generado contiene los tres sub-encabezados numerados en el orden correcto cuando los tres sub-módulos tienen datos disponibles.
- **SC-002**: El log de la corrida muestra que los tres sub-módulos (`Generate21Globales`, `Generate21Regionales`, `Generate21Startups`) fueron invocados cuando el pipeline principal corre con un sector que tiene datos disponibles.
- **SC-003**: Una segunda corrida para una empresa del mismo sector con cache disponible completa la sección 2.1 en menos de 10 segundos (lectura de cache, sin llamadas LLM ni web).
- **SC-004**: Los tests unitarios existentes de `generate_benchmarking` siguen pasando sin modificaciones tras la activación del pipeline.
- **SC-005**: Los tres sub-módulos están correctamente persistidos como checkpoints sectoriales al finalizar una corrida exitosa con base de datos disponible.

---

## Assumptions

- El `generate_n1.py` tiene acceso a `ctx.engine` (motor de BD) y `ctx.run_key` para inyectarlos en `GenerateBenchmarking`.
- Los componentes `Generate21Globales`, `Generate21Regionales`, `Generate21Startups` ya están implementados y sus dependencias (store, web_connector, entidad_repo) están disponibles en el contexto del pipeline.
- El cambio de numeración en los encabezados (`### Referentes Globales` → `### 2.1.1. Referentes Globales`) es retrocompatible: el DocxRenderer y el ensamblador de informe tratan encabezados Markdown de nivel `###` uniformemente.
- La activación de los sub-módulos modulares desplaza al generador LLM monolítico de 2.1 como ruta principal, pero el flujo de fallback (LLM monolítico) debe permanecer disponible para sectores sin datos EMIS ni StartIA.

---

## Clarifications

### Session 2026-08-20

- Q: ¿La activación de los sub-módulos modulares en `generate_n1.py` debe reemplazar completamente el flujo LLM monolítico de 2.1, o coexistir como ruta alternativa? → A: Coexistir como alternativa — si los sub-módulos modulares están disponibles se usan primero; si fallan o no tienen datos, el flujo LLM monolítico actúa como fallback (ya implementado en `generate_benchmarking.py` línea ~429). El flag `jugadores_use_case is not None` controla cuál ruta se activa.
- Q: ¿La verificación de almacenamiento de checkpoints es parte del scope de esta feature, o es solo diagnóstico? → A: Parte del scope — FR-003/FR-004/FR-005 exigen que el pipeline inyecte el engine y que los checkpoints sectoriales se persistan y reutilicen. La feature incluye el wiring completo, no solo el diagnóstico.
