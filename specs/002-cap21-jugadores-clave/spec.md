# Feature Specification: Cap 2.1 — Jugadores Clave Modular

**Feature Branch**: `002-cap21-jugadores-clave`

**Created**: 2026-08-19

**Status**: Draft

**Input**: Cap 2.1 — Jugadores Clave modular: tres sub-secciones independientes (Referentes Globales, Referentes Regionales, Startups/Disruptores), cada una con su propia fuente primaria y resultado consultable por separado.

---

## Contexto del Negocio

El Capítulo 2.1 del informe de inteligencia competitiva describe los actores clave del sector de la empresa analizada, agrupados en tres categorías:

1. **Referentes Globales**: líderes mundiales del sector cuya estrategia y modelo de negocio marcan el estándar de la industria.
2. **Referentes Regionales**: empresas establecidas en LatAm/Colombia representativas del sector por tamaño o ventas.
3. **Startups y Disruptores**: entrantes recientes (locales e internacionales) con modelos de negocio innovadores que están ganando tracción.

Hoy las tres categorías se generan en un único llamado LLM, sin control granular, sin visibilidad parcial y sin aprovechamiento estructurado de las fuentes de datos curadas disponibles (EMIS, StartIA). Esta feature modulariza cada categoría como un sub-módulo independiente con su propia fuente primaria, sus propias búsquedas y su propio resultado consultable.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Referentes Globales web-first (Priority: P1)

El analista solicita el informe de una empresa del sector Alimentos (GICS 3020). El sistema identifica automáticamente hasta 5 referentes globales del sector (propuestos por LLM), realiza una búsqueda web independiente para cada uno y redacta su perfil en texto corrido, enfocándose en modelo de negocio, posición de mercado y diferenciales clave según el sector. El resultado está disponible como sección independiente antes de que terminen los otros sub-módulos.

**Por qué P1**: Es la sección más visible del Cap 2.1 y la que el analista usa para calibrar el nivel de referencia del sector. Proporciona valor inmediato y es la más rápida de obtener (no depende de EMIS ni StartIA).

**Independent Test**: Se puede ejecutar solo con la clasificación GICS de la empresa (disponible al final de N0). Entrega una sección 2.1.1 con perfiles en prosa de ≤5 empresas globales.

**Acceptance Scenarios**:

1. **Given** una empresa clasificada en sector GICS válido, **When** se ejecuta el sub-módulo Globales, **Then** el LLM propone ≤5 candidatos globales del sector, se lanza una búsqueda web por cada candidato, y el resultado es texto corrido en español con modelo de negocio + mercado + diferenciales para cada uno que tuvo resultados web.
2. **Given** el LLM propone un candidato pero la búsqueda web no retorna resultados relevantes, **When** se ensambla la sección, **Then** ese candidato se omite o aparece con información mínima (nombre y sector), nunca con datos fabricados.
3. **Given** el sub-módulo Globales ya terminó, **When** el sub-módulo Regionales aún está en ejecución, **Then** el resultado de Globales es visible e independientemente accesible para el analista.
4. **Given** la búsqueda web retorna más información de la necesaria para un candidato, **When** se redacta el perfil, **Then** se selecciona la información más relevante al sector analizado y se cita la fuente.

---

### User Story 2 — Referentes Regionales desde EMIS (Priority: P2)

El analista solicita el informe de una empresa de alimentos colombiana. El sistema consulta la base de datos EMIS indexada para el sector, selecciona hasta 3 empresas representativas por tamaño o ventas, y redacta sus perfiles en texto corrido usando EMIS como fuente primaria, complementando con web solo donde EMIS no es suficiente. El resultado es una sección 2.1.2 independiente.

**Por qué P2**: Requiere que EMIS esté indexado para el sector (dependencia de ingesta previa). Agrega valor diferencial alto porque provee datos financieros y operativos curados de empresas regionales, lo que el RAG web no puede igualar.

**Independent Test**: Se puede ejecutar con el código GICS y verificar que los perfiles provienen de documentos EMIS (metadatos de chunk `fuente_tipo = "emis"`). Entrega una sección 2.1.2 con ≤3 perfiles en prosa.

**Acceptance Scenarios**:

1. **Given** hay documentos EMIS indexados para el sector, **When** se ejecuta el sub-módulo Regionales, **Then** el sistema recupera chunks de fuente EMIS, selecciona las ≤3 empresas más representativas por tamaño/ventas, y redacta sus perfiles en prosa citando la fuente EMIS.
2. **Given** EMIS tiene información parcial de una empresa regional, **When** se redacta el perfil, **Then** el sistema complementa con búsqueda web y cita cada dato según su fuente (EMIS o web), sin mezclar atribuciones.
3. **Given** no hay documentos EMIS indexados para el sector, **When** se ejecuta el sub-módulo, **Then** se genera un párrafo de ausencia (Constitution III) recomendando ingestar documentos EMIS del sector; no se fabrican datos.
4. **Given** el sub-módulo Regionales finaliza, **When** se integra en el Cap 2.1, **Then** sus perfiles aparecen bajo el encabezado `### Referentes Regionales LatAm/Colombia` con trazabilidad de fuente.

---

### User Story 3 — Startups y Disruptores desde StartIA + web (Priority: P3)

El analista solicita el informe de una empresa de logística. El sistema consulta la base de datos StartIA para identificar hasta 3 startups locales/colombianas que están activamente ingresando al sector (las más grandes o con mayor tracción), y busca hasta 2 disruptores internacionales en la web. Redacta los perfiles con énfasis en modelos de negocio disruptivos. Resultado: sección 2.1.3 independiente.

**Por qué P3**: Depende de StartIA (fuente de datos curada, no siempre disponible para todos los sectores) y de web search para los internacionales. Agrega contexto de innovación pero su ausencia no invalida el informe.

**Independent Test**: Se puede ejecutar con el código GICS y verificar que los perfiles locales provienen de la DB StartIA y los internacionales tienen URL de fuente web. Entrega sección 2.1.3 con ≤5 perfiles (≤3 locales + ≤2 internacionales).

**Acceptance Scenarios**:

1. **Given** hay registros en StartIA para el sector, **When** se ejecuta el sub-módulo, **Then** se seleccionan las ≤3 startups locales más grandes o con mayor tracción del sector, y se redactan sus perfiles en prosa con énfasis en modelo de negocio disruptivo.
2. **Given** cualquier resultado del sub-módulo (con o sin startups locales), **When** se complementa con internacionales, **Then** siempre se lanza búsqueda web para identificar ≤2 disruptores internacionales del sector no presentes en StartIA, y se redactan sus perfiles con fuente citada.
3. **Given** StartIA no tiene registros para el sector, **When** se ejecuta el sub-módulo, **Then** se buscan hasta 2 disruptores internacionales en web y se genera la sección con ellos; si tampoco hay web, se genera párrafo de ausencia.
4. **Given** una startup aparece tanto en StartIA como en la búsqueda web de internacionales, **When** se ensambla la sección, **Then** aparece una sola vez (deduplicación por nombre normalizado), usando StartIA como fuente primaria.

---

### Edge Cases

- ¿Qué ocurre si el LLM propone un referente global que ya es la empresa analizada? → Se excluye automáticamente (exclusión por nombre focal, como en el KB actual).
- ¿Qué ocurre si los tres sub-módulos devuelven datos para la misma empresa (overlap entre tiers)? → La empresa se asigna al tier de mayor prioridad (Global > Regional > Startup) y no se duplica en 2.1.
- ¿Qué ocurre si la búsqueda web de un referente global retorna contenido en un idioma distinto al español? → Se usa el contenido para el perfil y se redacta en español; la fuente se cita igualmente.
- ¿Qué ocurre si el límite de búsquedas web se agota antes de cubrir todos los candidatos? → Se procesan los que alcanzaron cobertura; se documenta en el log qué candidatos quedaron sin datos web.
- ¿Qué ocurre si StartIA retorna 10 startups del sector? → Se seleccionan las 3 con mayor `ventas_2025_cop` (JOIN `entidad_atributos`), usando `n_menciones` como desempate si el campo no está disponible. El criterio de ranking es lógica interna del sistema y no se menciona en el texto del perfil; se registra solo en el log de la corrida.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ejecutar los tres sub-módulos (Globales, Regionales, Startups) de forma independiente, con su propio inicio, estado y resultado, sin que la falla o lentitud de uno bloquee a los demás.
- **FR-002**: El sub-módulo Globales DEBE usar el LLM para proponer una lista de candidatos globales del sector (hasta 5), luego lanzar una búsqueda web independiente por cada candidato antes de redactar sus perfiles.
- **FR-003**: El sub-módulo Globales DEBE limitar su output a ≤5 empresas; si el LLM propone más, se priorizan las de mayor relevancia al sector.
- **FR-004**: El sub-módulo Regionales DEBE usar documentos EMIS indexados (chunks con `fuente_tipo = "emis"`) como fuente primaria para identificar y describir las empresas regionales representativas del sector.
- **FR-005**: El sub-módulo Regionales DEBE seleccionar hasta 3 empresas del sector priorizando las de mayor tamaño o ventas según los datos EMIS disponibles.
- **FR-006**: El sub-módulo Regionales PUEDE complementar la información EMIS con búsqueda web para campos no cubiertos, citando cada dato según su fuente real.
- **FR-007**: El sub-módulo Startups DEBE usar la base de datos StartIA como fuente primaria para identificar startups locales activamente ingresando al sector.
- **FR-008**: El sub-módulo Startups DEBE seleccionar hasta 3 startups locales de StartIA, priorizando las de mayor tamaño según `ventas_2025_cop` (atributo de StartIA en `entidad_atributos`); si el campo no está disponible para una startup, se usa `n_menciones` como criterio de desempate.
- **FR-009**: El sub-módulo Startups DEBE complementar siempre con hasta 2 disruptores internacionales identificados mediante búsqueda web, que no estén ya en la lista StartIA. Esta búsqueda ocurre independientemente de cuántas startups locales se hayan encontrado: los internacionales son una capa adicional, no un fallback.
- **FR-010**: Todos los sub-módulos DEBEN presentar sus resultados en texto corrido en español (prosa), sin tablas, sin viñetas, sin listas.
- **FR-011**: Ningún sub-módulo DEBE fabricar información: cada afirmación debe ser trazable a un chunk recuperado de EMIS, StartIA, o web. Si no hay evidencia, se omite el campo.
- **FR-012**: Cada sub-módulo DEBE tener su propio resultado persistible y consultable de forma independiente (checkpoint propio: `cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups`). La clave de lookup es `(sector_gics_code, sub_gics)`: empresas del mismo sector GICS y sub-sector comparten cache; sub-sectores distintos dentro del mismo sector amplio generan entradas separadas. La clave se implementa como `run_key` compuesto: `f"sector_{sector_gics_code}_{sub_gics or 'any'}"`, construido por el llamador y usado en `CheckpointRepository` sin migración de esquema. El orquestador acepta `engine` y `run_key` como parámetros opcionales de `execute()`; si son `None`, la persistencia se omite silenciosamente (compatible con ejecución sin BD, p.ej. tests unitarios). El llamador (`generate_benchmarking`) inyecta ambos cuando están disponibles.
- **FR-013**: Si un sub-módulo no supera el umbral mínimo de retrieval, DEBE generar un párrafo de ausencia desde plantilla (Constitution III) en lugar de llamar al LLM con evidencia insuficiente.
- **FR-014**: El enfoque de cada perfil DEBE estar orientado al sector GICS analizado: modelo de negocio, posición de mercado y diferenciales clave relevantes al sector.
- **FR-015**: Los tres sub-módulos DEBEN ser ensamblables en orden (2.1.1 → 2.1.2 → 2.1.3) para componer la sección 2.1 completa del informe. Si los tres sub-módulos devuelven ausencia, el orquestador DEBE generar un único párrafo de ausencia consolidado directamente bajo el encabezado `## 2.1. Jugadores Clave` (sin los tres sub-encabezados `###`), indicando qué fuentes faltan y cómo obtenerlas.
- **FR-016**: La empresa focal analizada (y sus aliases) DEBE ser excluida de todos los perfiles generados. La exclusión se implementa mediante filtro por código (`_clave_exclusion`) aplicado sobre la lista de candidatos/empresas extraída en cada sub-módulo, antes de pasarla al LLM — no se confía únicamente en instrucciones del prompt.

### Key Entities

- **CandidatoGlobal**: nombre propuesto por el LLM, chunks web recuperados, perfil redactado, fuentes citadas.
- **EmpresaRegional**: nombre, datos EMIS (ventas, tamaño, descripción), chunks web complementarios, perfil redactado, fuentes citadas.
- **StartupDisruptor**: nombre, tier (local/internacional), fuente primaria (StartIA o web), modelo de negocio disruptivo, perfil redactado.
- **Sub21Result**: resultado de un sub-módulo — lista de perfiles en prosa, `retrieval_suficiente: bool`, chunks usados para citación, checkpoint key.
- **Jugadores21**: resultado ensamblado de los tres sub-módulos — texto markdown con encabezados `### Referentes Globales / ### Referentes Regionales / ### Startups y Disruptores`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cada sub-módulo produce un resultado visible al analista en menos de 3 minutos desde su inicio, independientemente de los otros dos.
- **SC-002**: Al menos el 80% de los perfiles generados (cuando hay datos disponibles) contienen los tres campos clave: modelo de negocio, posición de mercado y diferencial clave.
- **SC-003**: El 100% de las afirmaciones en los perfiles es trazable a una fuente recuperada (web, EMIS o StartIA); cero datos fabricados verificables.
- **SC-004**: El checkpoint `cap2_21_globales` está persistido antes de que el sub-módulo Regionales finalice, lo que permite consultarlo en la siguiente ejecución o via restore. No se requiere visibilidad en tiempo real en la UI de Streamlit (fuera de scope de este feature).
- **SC-005**: Un segundo informe de una empresa del mismo `(sector_gics_code, sub_gics)` reutiliza los resultados cacheados de los tres sub-módulos sin repetir búsquedas web ni llamadas LLM (hit de checkpoint). Empresas del mismo sector pero distinto `sub_gics` NO comparten cache y generan búsquedas nuevas. Prerequisito: `sub_gics` de la empresa focal debe haberse resuelto en N0 (desde productos/descripción); si es `None`, la clave de cache degrada a `sector_gics_code` solo.
- **SC-006**: El sub-módulo Regionales usa datos EMIS como fuente primaria en ≥70% de los perfiles cuando hay documentos EMIS indexados para el sector.
- **SC-007**: El sub-módulo Startups incluye al menos una empresa de StartIA cuando el sector tiene registros en esa base de datos.

---

## Clarifications

### Session 2026-08-19

- Q: ¿SC-004 implica UI en tiempo real o basta con checkpoint persistido? → A: Checkpoint backend — SC-004 se cumple con `cap2_21_globales` persistido antes de que Regionales finalice; visibilidad UI en tiempo real está fuera del scope de este feature.
- Q: ¿Qué criterio concreto define "mayor tamaño o tracción documentada" para FR-008? → A: `ventas_2025_cop` (atributo StartIA, JOIN con `entidad_atributos`) como criterio primario; `n_menciones` como desempate cuando `ventas_2025_cop` no está disponible.
- Q: ¿Qué aparece en 2.1 cuando los tres sub-módulos devuelven ausencia? → A: Un único párrafo de ausencia consolidado bajo `## 2.1. Jugadores Clave` (sin los tres `###`), indicando fuentes faltantes y cómo obtenerlas.

### Session 2026-08-20 (convergence phase 9)

- Q: ¿FR-012 debe reflejar constructor injection o execute() params para engine/run_key? → A: Actualizar el spec — el orquestador acepta `engine` y `run_key` como parámetros opcionales de `execute()`; T040 cierra editando FR-012 (no refactorizar la implementación).
- Q: ¿Cómo obtiene T037 el `sub_gics` de la empresa analizada para construir la clave de cache sectorial? → A: Resolución proactiva en N0 — añadir un instrumento de clasificación de sub-sector GICS (desde productos/descripción de la empresa focal) que produzca `sub_gics` en el pipeline context de N0; `GenerateBenchmarking` recibe `sub_gics` como atributo de constructor (`sub_gics: str | None = None`) y lo usa internamente en T037 para construir la clave `(sector_gics_code, sub_gics)` sin cambiar la firma pública de `execute()`.
- Q: ¿Cómo almacena e indexa T037 los checkpoints sectoriales de 2.1 — nueva columna en BD, tabla separada, o `run_key` compuesto? → A: `run_key` compuesto — el llamador construye `sector_run_key = f"sector_{sector_gics_code}_{sub_gics or 'any'}"` y los sub-módulos 2.1 se guardan bajo ese `run_key`; la siguiente corrida busca ese `run_key` antes de ejecutar. Sin migración de esquema, reutiliza `CheckpointRepository` existente.

### Session 2026-08-19 (convergence)

- Q: ¿Qué combinación de parámetros define la clave de cache para SC-005 (reutilización entre corridas del mismo sector)? → A: Doble llave `(sector_gics_code, sub_gics)` — el sector amplio más el sub-sector específico de la empresa analizada. Empresas del mismo sector GICS y mismo sub_gics comparten cache de sub-módulos 2.1; sub-sectores distintos dentro del mismo sector amplio generan caches separados.
- Q: ¿Cómo recibe `Generate21Jugadores` el engine de BD y la run_key para persistir checkpoints? → A: Constructor injection — `Generate21Jugadores(…, engine=None, run_key=None)`; si `engine` es `None` la persistencia se omite silenciosamente (modo test/sin-BD). El llamador (`generate_benchmarking`) inyecta ambos cuando están disponibles.
- Q: ¿Los disruptores internacionales se buscan siempre o solo cuando `locales < max_locales`? → A: Siempre — los ≤2 internacionales son una capa adicional independiente del conteo de locales; FR-009 "DEBE complementar" no tiene condición sobre el cupo local.
- Q: ¿La exclusión de la empresa focal en Regionales debe ser filtro por código o solo instrucción en el prompt? → A: Filtro por código — aplicar `_clave_exclusion(nombre_empresa)` sobre la lista de `empresas_emis` antes de pasarla al LLM; consistente con cómo lo hace `generate_21_globales` y garantiza FR-016 de forma determinista.
- Q: ¿El criterio de selección de startups (`ventas_2025_cop` / `n_menciones`) debe aparecer en el perfil redactado o es solo lógica interna? → A: Solo interno — el perfil redacta el negocio de la startup sin mencionar el criterio de ranking; el criterio se registra en el log del sistema para auditoría pero no en el texto del informe.

---

## Assumptions

- Los documentos EMIS relevantes para el sector ya fueron ingestados en el índice pgvector antes de que se ejecute el sub-módulo Regionales. Si no están indexados, aplica la regla de ausencia.
- La base de datos StartIA está disponible y puede filtrarse por sector GICS (el mapeo GICS↔sector StartIA ya existe desde DT-050/DT-UI04f).
- El WebConnector y el API LLM están configurados y disponibles en el entorno de ejecución.
- El código GICS del sector de la empresa fue resuelto en la fase N0 antes de ejecutar cualquier sub-módulo de 2.1. El sub-sector GICS (`sub_gics`) de la empresa focal también se resuelve en N0 mediante un clasificador de sub-sector (desde productos/descripción); si no puede resolverse, se usa `None` y la clave de cache de SC-005 degrada a `sector_gics_code` solo.
- Los tres sub-módulos son piezas del mismo paso N1 del pipeline y se ejecutan después de N0 (Cap 1 + GICS).
- El resultado de los tres sub-módulos se ensambla secuencialmente (Globales → Regionales → Startups) para formar la sección 2.1 completa que sirve de entrada al Cap 2.2.
- La deduplicación cross-tier (una empresa en Globales y Regionales) asigna la empresa al tier de mayor prioridad y no la repite.
- El límite de búsquedas web por ejecución es el que impone la configuración actual de `WebConnector` (sin cambios en este feature).
