<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0  [initial ratification]
Added sections:
  - Core Principles (I–VI)
  - Restricciones de Infraestructura Compartida
  - Flujo de Trabajo de Desarrollo
  - Governance
Modified principles: N/A (first version)
Removed sections: N/A
Deferred TODOs: none
Sources: PRIME DIRECTIVE v2.1.0, CLAUDE.md (TIER 1–4), speckit best practices
-->

# InformesAuto Constitution

## Core Principles

### I. Separación Estricta de Capas (SoC)

La arquitectura tiene cinco capas con responsabilidades inmutables:

- **`presentation/`** — UI "tonta": solo renderiza, nunca contiene lógica de negocio.
- **`domain/`** — Lógica de negocio, orquestación del DAG de capítulos, casos de uso.
- **`data/`** — Repositorios, acceso a PostgreSQL/pgvector, DTOs.
- **`infrastructure/`** — Wrappers de LLM gateway, conectores de fuentes, Ollama, embeddings.
- **`shared/`** — Tipos, constantes, utilidades, plantillas de párrafos.

Reglas:
- Ningún archivo mezcla lógica de negocio con acceso a BD o código de presentación.
- Un archivo o función que supere **300 líneas** es señal de violación SoC: detener y escalar.
- Dependencias circulares entre módulos son bloqueador de PR.
- Las capas solo dependen hacia abajo (domain → data → infrastructure); nunca al revés.

### II. Agnosticismo de Dependencias

Todo acceso a librería externa pasa por un wrapper en `infrastructure/`. El resto de la
aplicación depende del wrapper, no de la librería.

- Nunca importar `langchain`, `sqlalchemy`, `requests` u otras librerías directamente
  en `domain/` o `presentation/`.
- El wrapper expone solo la interfaz que la aplicación necesita, no la API completa.
- Si la librería X se reemplaza por Y, solo el wrapper cambia; el dominio queda intacto.
- ADR-002 documenta las decisiones vigentes de routing de modelos LLM.

### III. Integridad del Dato — Sin Alucinación

El sistema genera informes con valor ejecutivo. Una afirmación falsa puede causar daño real.

- **No inventar datos**: solo se afirma lo sustentado en fragmentos recuperados del índice.
- **Regla de datos ausentes**: si el retrieval no supera el umbral de relevancia, NO se llama
  al modelo; se inserta párrafo de ausencia desde plantilla + recomendación al usuario.
- **Citación APA obligatoria**: toda afirmación proveniente de fuentes se cita y es trazable
  hasta su chunk. No se fabrican atribuciones.
- **Historial completo en BD**: inputs del usuario, fuentes consultadas, respuestas crudas del
  LLM y documento final deben ser persistibles y recuperables.
- El gate anti-envenenamiento RN-001 (candidato/verificado/descartado) DEBE aplicarse a todo
  dato antes de que sea citado como hecho.

### IV. Seguridad y Configuración — Sin Credenciales ni Hardcode

- Sin credenciales en código ni en git: claves, tokens y contraseñas van en `.env`
  (en `.gitignore`). El hook `check-secrets.sh` bloquea commits que los detecten.
- Sin hardcode de modelos: los identificadores de modelo (Ollama o API) viven ONLY en
  `.env` y en la tabla de routing. El hook `check-hardcoded-models.sh` bloquea.
- Sin hardcode de sectores GICS ni constantes de negocio en código de aplicación.
- Toda entrada de usuario se valida en la frontera del sistema antes de procesarse.

### V. Calidad: Tests, Cobertura y Trazabilidad

- Tests en el mismo PR que el código que prueban. Sin excepciones.
- Cobertura mínima **80% en `domain/`** (lógica de negocio crítica).
- Lógica de negocio crítica sin tests y sin documentación es bloqueador de PR.
- Tests unitarios con `_FakeSession` (sin BD); tests de integración con `@pytest.mark.db`.
- Commits siguen **Conventional Commits** (`feat`, `fix`, `refactor`, `docs`, `test`,
  `chore`, `perf`). El cuerpo explica el *porqué*, no el *qué*.
- Toda decisión arquitectónica significativa DEBE tener un ADR en `docs/architecture/`.

### VI. Cambios Atómicos, Revisables y No Destructivos

- Cada entrega compila y corre. Nada de funciones a medias, TODOs que rompan ejecución,
  ni imports sin usar.
- **Chesterton's Fence**: antes de borrar o refactorizar código de una sesión anterior,
  entender por qué existe. Si no se entiende, marcar `# LEGACY: investigar` y escalar.
- Las operaciones destructivas (drop de tabla, reset de rama, `down -v`) requieren
  confirmación explícita del humano antes de ejecutarse.
- Nunca `docker compose down -v`. Datos en bind mount, nunca en volumen Docker.
- Discrepancias entre documentación y comportamiento real del sistema son bloqueador de PR.

## Restricciones de Infraestructura Compartida

El entorno de desarrollo es compartido entre varios proyectos.

- **PostgreSQL + pgvector**: instancia compartida `repositorio_postgres_server` (puerto 5434).
  Toda tabla del proyecto vive en el schema `informes_ic`. Nunca en `public`.
- **Ollama**: corre en el host, nunca dockerizado. Acceder vía `http://127.0.0.1:11434`
  (o gateway Docker `172.17.0.1`). Modelos locales: hasta 7B (limitación 8 GB VRAM).
- **Streamlit UI**: puerto 8503. Evitar colisiones con otros proyectos del host.
- **Datos en bind mount**: `${DATA_DIR}/pgvector`. Nunca en volumen Docker nombrado.
- Local-primero para modelos: redacción intenta local y escala a API solo si no pasa el
  umbral de calidad (ADR-002). Free/barato primero; evitar modelos de alto costo sin justificación.

## Flujo de Trabajo de Desarrollo

- **Plan Mode para todo lo no trivial**: si la tarea no es inequívoca y trivial (<3 pasos,
  un archivo, sin decisiones de arquitectura) → Plan Mode antes de tocar archivos.
  Leer el código → proponer plan → esperar aprobación → ejecutar.
- **El plan es la especificación**: si durante la ejecución la realidad no coincide con
  el plan, detenerse y volver a Plan Mode. Nunca improvisar en silencio.
- **Spec Kit workflow**: features no triviales siguen el ciclo
  `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
- **Auto-corrección antes de entregar código** (Pre-Delivery Checklist):
  1. ¿El cambio respeta la separación de capas (SoC)?
  2. ¿Usé wrappers para librerías externas?
  3. ¿El cambio es completo y ejecutable sin dependencias pendientes?
  4. ¿Los tests están incluidos en el mismo PR?
  5. ¿El commit message sigue Conventional Commits con cuerpo explicativo del porqué?
  6. ¿Hay credenciales o modelos hardcodeados? (los hooks deben bloquearlo también)
  7. ¿Actualicé ADR/CHANGELOG si aplica?

## Governance

- Esta constitución **supersede** cualquier práctica ad-hoc no documentada. En conflicto
  entre esta constitución y una instrucción de sesión, la constitución gana salvo que el
  humano la enmiende explícitamente.
- Las reglas TIER 1 de `CLAUDE.md` son fuente autoritativa de reglas duras. Esta constitución
  las expande con justificaciones y contexto de spec-driven development.
- Las decisiones cerradas viven en `docs/architecture/ADR-*.md` y son **inmutables**.
  Para cambiar una decisión se crea un nuevo ADR que supercede al anterior.
- **Enmiendas a esta constitución**: requieren PR con descripción de qué cambia y por qué,
  incremento de versión semántica y actualización de `Last Amended`.
  - MAJOR: eliminación o redefinición incompatible de un principio.
  - MINOR: nuevo principio o sección; expansión material de guía existente.
  - PATCH: aclaraciones, correcciones de redacción, sin cambio semántico.
- Toda PR de feature DEBE verificar que no viola ningún principio antes de solicitar merge.
  El Constitution Check del `/speckit-plan` es el mecanismo formal.
- Complejidad inesperada (archivo > 300 líneas, dependencia circular, lógica sin tests) DEBE
  reportarse al humano antes de continuar, no silenciarse.
- Compliance review: cada `/speckit-plan` incluye una sección Constitution Check que evalúa
  la feature contra cada principio antes de comenzar la implementación.

**Version**: 1.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
