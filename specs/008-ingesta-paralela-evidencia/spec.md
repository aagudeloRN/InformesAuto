# Feature Specification: 008 — Ingesta Masiva Paralela de PDFs e Infraestructura de Evidencia

**Feature Branch**: `008-ingesta-paralela-evidencia`

**Created**: 2026-09-17

**Status**: Draft

**Priority**: P1 (Infraestructura y Capacidad de Carga)

**Sequence**: Spec 008 (Opción B) — inmediatamente después de Spec 007 (Opción A: HITL + Reconciliación).

---

## 1. Contexto y Justificación de Negocio

El sistema genera informes de Inteligencia Competitiva a partir de un corpus documental indexado en pgvector. Existen dos cuellos de botella que limitan la calidad y escalabilidad del sistema:

1. **Ingesta secuencial lenta**: `scripts/ingest_batch.py` procesa los PDFs uno por uno. Con ~250 archivos por lote, el proceso tarda ~10 minutos en condiciones normales. Al necesitar re-ingestar corpus completos (ej. nuevos informes EMIS), el tiempo se vuelve operativamente costoso.

2. **Baja densidad documental en sectores secundarios**: Sectores con menos de ~10 documentos en el corpus producen informes con solo ~9 referencias citadas, lo que degrada la credibilidad del análisis. El sistema ya detecta ausencias de evidencia (regla de datos ausentes), pero aún no intenta enriquecerse automáticamente antes de declarar ausencia.

---

## Clarifications

### Session 2026-09-17

- Q: ¿Qué campo(s) definen la unicidad de un chunk para evitar duplicados en re-ingesta? → A: Constraint único `(documento_id, chunk_index)` — FK del documento + posición ordinal dentro del PDF.
- Q: ¿El paralelismo entre PDFs debe usar hilos (`ThreadPoolExecutor`) o procesos (`ProcessPoolExecutor`)? → A: `ThreadPoolExecutor` — las llamadas a Ollama son I/O HTTP; el GIL se libera durante la espera, los threads son suficientes y más livianos.
- Q: ¿El umbral que activa el enriquecimiento automático es el mismo del retrieval normal o uno independiente? → A: Mismo umbral del sistema existente (`RETRIEVAL_MIN_SCORE` en `.env`); sin nueva variable de configuración.
- Q: ¿El acceso a OpenAlex requiere API key o opera de forma anónima con polite pool? → A: Anónimo con polite pool — incluir `OPENALEX_EMAIL` en `.env` para el header `User-Agent`; sin API key adicional.
- Q: ¿El log de errores de ingesta debe persistirse en BD o basta con stdout estructurado? → A: Stdout estructurado (JSON lines) — cada resultado impreso como JSON por línea; redirigible a archivo con `> ingesta.log`; sin tabla adicional en BD.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ingesta Paralela Entre PDFs (Priority: P1)

El operador del sistema desea ingestar un lote grande de PDFs (ej. 250 archivos EMIS de un sector) sin esperar a que cada archivo termine antes de empezar el siguiente. Lanza el script con un flag de paralelismo y observa el progreso en tiempo real; al finalizar, el índice vectorial refleja todos los documentos nuevos correctamente.

**Why this priority**: Desbloquea re-ingesta periódica de corpus sin ventanas de mantenimiento largas. Es prerequisito para que el enriquecimiento automático (US2) sea viable a escala.

**Independent Test**: Ejecutar `scripts/ingest_batch.py --workers 4` sobre un directorio de 10 PDFs de prueba y verificar que (a) todos se ingestaron en el índice, (b) no hay duplicados de chunks, (c) el tiempo total es menor que la suma de tiempos individuales.

**Acceptance Scenarios**:

1. **Given** un directorio con N PDFs no indexados, **When** se lanza `ingest_batch.py --workers W`, **Then** todos los PDFs se procesan y sus chunks aparecen en la tabla de embeddings dentro del tiempo ≤ (tiempo_secuencial / W) × 1.5.
2. **Given** un PDF ya indexado en la BD, **When** se re-ejecuta la ingesta sobre el mismo directorio, **Then** no se crean chunks duplicados (idempotencia).
3. **Given** un PDF corrupto o ilegible en el lote, **When** se procesa el lote, **Then** el archivo fallido se registra en un log de errores y los demás archivos se procesan con normalidad (fallo aislado).
4. **Given** el sistema de embeddings (Ollama `nomic-embed-text`) no responde durante la ingesta, **When** un worker intenta embeddings, **Then** el worker reintenta hasta 3 veces con backoff antes de registrar el fallo y continuar con el siguiente PDF.

---

### User Story 2 — Enriquecimiento Automático de Sectores con Baja Evidencia (Priority: P2)

El sistema detecta, durante la generación de un informe, que el retrieval de un sector específico no supera el umbral de relevancia mínima. En lugar de insertar inmediatamente el párrafo de ausencia, activa un proceso de enriquecimiento: consulta fuentes secundarias (OpenAlex, arXiv, búsqueda web), descarga y persiste los fragmentos relevantes en el índice vectorial compartido, y luego reintenta el retrieval. Si tras el enriquecimiento hay evidencia suficiente, el informe la utiliza con citación APA; si no, aplica la regla de datos ausentes.

**Why this priority**: Reduce la tasa de párrafos de ausencia en sectores secundarios sin requerir intervención manual del analista. Mejora directamente la completitud percibida del informe.

**Independent Test**: Configurar un sector de prueba sin documentos en el índice, lanzar una generación de informe con ese sector y verificar que (a) el sistema activa el enriquecimiento, (b) al menos una fuente secundaria se persiste en pgvector, (c) el retrieval reintentado devuelve al menos 1 fragmento con score > umbral.

**Acceptance Scenarios**:

1. **Given** un sector con retrieval score < umbral mínimo, **When** el pipeline de generación alcanza ese sector, **Then** el sistema activa el enriquecimiento automático antes de invocar al modelo.
2. **Given** el enriquecimiento encuentra artículos relevantes en OpenAlex o web, **When** los fragmentos se persisten en pgvector, **Then** quedan indistinguibles de fuentes manuales para el pipeline RAG (mismo esquema de chunk, misma tabla).
3. **Given** el enriquecimiento no encuentra evidencia adicional, **When** el retrieval reintentado sigue por debajo del umbral, **Then** se inserta el párrafo de ausencia estándar (regla de datos ausentes, sin invocar al modelo).
4. **Given** el enriquecimiento automático falla por error de red o API externa, **When** el timeout se alcanza, **Then** el pipeline continúa sin enriquecimiento (degradación elegante) y registra el evento en el historial del informe.

---

### Edge Cases

- ¿Qué ocurre si dos workers intentan ingestar el mismo PDF simultáneamente? → El constraint único `(documento_id, chunk_index)` garantiza que el segundo worker recibe `ON CONFLICT DO NOTHING` sin error; los datos quedan consistentes.
- ¿Qué ocurre si el pool de conexiones SQLAlchemy se agota durante ingesta paralela masiva? → Cada worker crea su propia `SessionLocal()` independiente; no se comparten sesiones entre hilos.
- ¿Qué ocurre si el enriquecimiento web devuelve contenido en inglés para un informe en español? → Los fragmentos se persisten con metadato `idioma: "en"`; el pipeline RAG los incluye si superan el umbral de relevancia semántica.
- ¿Qué ocurre si el directorio de PDFs está vacío? → El script finaliza inmediatamente con mensaje informativo y código de salida 0.
- ¿El enriquecimiento automático puede entrar en bucle infinito? → No: se ejecuta como máximo una vez por sector por generación de informe (flag en contexto de generación).

---

## Requirements *(mandatory)*

### Functional Requirements

**Bloque A — Ingesta Paralela:**

- **FR-001**: El script `ingest_batch.py` DEBE aceptar un parámetro `--workers N` (entero ≥ 1, default 1) que controla el número de hilos concurrentes implementados con `ThreadPoolExecutor`; cada hilo maneja un PDF completo de forma independiente.
- **FR-002**: Cada worker DEBE usar su propia sesión de base de datos independiente; está prohibido compartir sesiones SQLAlchemy entre hilos.
- **FR-003**: La ingesta paralela DEBE ser idempotente: la tabla de embeddings tiene un constraint único `(documento_id, chunk_index)`; re-ejecutar sobre un directorio ya procesado activa `ON CONFLICT DO NOTHING` y no crea duplicados.
- **FR-004**: Los fallos de un PDF individual DEBEN emitirse por stdout como JSON lines (`{"archivo": ..., "estado": "error", "error": ...}`) sin interrumpir el procesamiento de los demás archivos; el operador puede redirigir stdout a archivo (`> ingesta.log`).
- **FR-005**: El script DEBE emitir líneas de progreso por stdout (JSON lines con `{"procesados": N, "total": M, "archivo": ..., "estado": ...}`) a medida que cada worker completa un PDF.
- **FR-006**: El módulo de ingesta paralela DEBE estar encapsulado en un wrapper bajo `infrastructure/` siguiendo el principio de agnosticismo de dependencias (Constitución II).

**Bloque B — Enriquecimiento Automático:**

- **FR-007**: El pipeline de generación DEBE detectar automáticamente cuando el retrieval de un sector no supera `RETRIEVAL_MIN_SCORE` (variable existente en `.env`); ese mismo umbral activa el enriquecimiento automático — no se introduce una variable de configuración adicional.
- **FR-008**: Al detectar baja evidencia, el sistema DEBE activar el módulo de enriquecimiento automático (`infrastructure/sources/`) consultando OpenAlex vía polite pool (header `User-Agent` con `OPENALEX_EMAIL` de `.env`, sin API key) como primera opción, y búsqueda web como fallback.
- **FR-009**: Los fragmentos obtenidos del enriquecimiento DEBEN persistirse en la misma tabla de embeddings que los PDFs manuales, con metadatos de procedencia (`fuente: "openalex"`, `fuente: "web_enrichment"`, etc.).
- **FR-010**: El enriquecimiento DEBE ejecutarse como máximo una vez por sector por ejecución de informe (sin bucles de retry indefinidos).
- **FR-011**: Si el enriquecimiento falla o no obtiene evidencia suficiente, el sistema DEBE aplicar la regla de datos ausentes sin invocar al modelo (comportamiento existente, preservado).
- **FR-012**: Los fragmentos enriquecidos DEBEN ser citables con APA; cada fragmento persistido DEBE tener `titulo`, `autores`, `año` y `url` como metadatos mínimos.

### Key Entities

- **LotePDF**: Conjunto de archivos PDF a procesar; atributos clave: ruta de directorio, lista de archivos, número de workers, estado de progreso.
- **ResultadoIngesta**: Resultado por archivo: `documento_id`, `n_chunks_creados`, `estado` (exitoso / fallido), `error_msg`.
- **FragmentoEnriquecido**: Chunk de texto obtenido de fuente secundaria; mismo esquema que chunks de PDFs manuales, con metadato `fuente` y `procedencia_url`.
- **EventoEnriquecimiento**: Registro de cada activación del enriquecimiento: sector, umbral detectado, fuentes consultadas, fragmentos obtenidos, resultado (enriquecido / sin evidencia / fallido).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un lote de 50 PDFs con `--workers 4` completa en tiempo ≤ 40% del tiempo que tardaría de forma secuencial (factor de aceleración ≥ 2.5×).
- **SC-002**: La re-ingesta del mismo lote produce exactamente 0 chunks duplicados en la tabla de embeddings.
- **SC-003**: Un fallo en un PDF individual no interrumpe el lote; el resto de archivos se procesan y quedan indexados correctamente.
- **SC-004**: El enriquecimiento automático reduce la tasa de párrafos de ausencia en sectores secundarios (< 10 docs en corpus) en al menos un 30% respecto al baseline actual.
- **SC-005**: Los fragmentos enriquecidos son recuperados por el pipeline RAG en las mismas condiciones que los chunks de PDFs manuales (mismo threshold, mismo re-ranker).
- **SC-006**: Ningún archivo nuevo creado en `src/` supera las 300 líneas (Constitución I).
- **SC-007**: Cobertura de tests ≥ 80% en los módulos de `domain/` nuevos o modificados; 0 errores de `ruff`.

---

## Assumptions

- El embedding local (`nomic-embed-text` vía Ollama en el host) tiene capacidad para manejar requests concurrentes desde múltiples workers; se asume que Ollama gestiona la cola internamente.
- La BD PostgreSQL compartida soporta el número de conexiones simultáneas requerido (N workers × 1 sesión cada uno); el `pool_size` del engine se configurará en `.env`.
- OpenAlex se accede vía polite pool anónimo con `OPENALEX_EMAIL` en el header `User-Agent`; sin API key. El volumen esperado (~10 queries/sector/informe) está dentro del límite del polite pool (~10 req/s).
- El enriquecimiento automático no reemplaza la ingesta manual de PDFs EMIS; es un complemento para sectores con corpus insuficiente.
- Los PDFs del lote están en el sistema de archivos local (no en S3 ni almacenamiento remoto).
- El formato de salida del script (`--workers`) es compatible con la invocación actual desde Makefile o scripts de CI sin cambios en la interfaz principal.
