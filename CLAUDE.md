# CLAUDE.md — Sistema de Informes de Inteligencia Competitiva

> Reglas operativas para agentes (Claude Code). Las reglas más importantes van primero.
> La norma arquitectónica completa vive en `docs/architecture/PRIME_DIRECTIVE.md`.
> Las decisiones cerradas viven en `docs/architecture/ADR-*.md` y son inmutables.

## TIER 1 — REGLAS DURAS (verificar antes de cada acción)

No negociables. Violar cualquiera es un fallo de flujo.

1. **No hardcodear nombres de modelo.** Los modelos (Ollama o API) viven SOLO en
   `.env` y en la tabla de routing. Nunca escribir `"qwen2.5"`, `"claude-..."`,
   `"gemini-..."` ni similares en código de aplicación. (ADR-002)
2. **No credenciales en código ni en git.** Claves, tokens y contraseñas van en `.env`
   (que está en `.gitignore`). Nunca commitear secretos.
3. **No tocar la base de datos compartida sin esquema propio.** Toda tabla del
   proyecto vive en su esquema dedicado dentro de la instancia PostgreSQL compartida.
   Nunca `docker compose down -v`. Datos en bind mount, nunca en volumen Docker.
4. **Ollama corre en el host, nunca dockerizado.** Acceder vía
   `http://127.0.0.1:11434` (o gateway Docker `172.17.0.1`). No levantar instancias
   propias de BD, embeddings o modelos: usar los servicios compartidos.
5. **Todo acceso a librería externa pasa por un wrapper en `infrastructure/`.**
   El resto de la app depende del wrapper, no de la librería. (Dependency Agnosticism)

## TIER 2 — FLUJO DE TRABAJO

- **Plan Mode para todo lo no trivial.** Si la tarea NO es (a) inequívoca Y (b)
  trivial (<3 pasos, un archivo, sin decisiones de arquitectura) → entrar en Plan Mode
  antes de tocar archivos. Leer el código relevante → proponer plan → esperar
  aprobación → ejecutar.
- **El plan es la especificación.** Si durante la ejecución la realidad no coincide
  con el plan, DETENERSE y volver a Plan Mode. Nunca improvisar en silencio.
- **Cambios atómicos.** Cada entrega compila y corre. Nada de funciones a medias,
  TODOs que rompan ejecución, ni imports sin usar.
- **Chesterton's Fence.** Antes de borrar o refactorizar código que no escribiste en
  esta sesión: entender por qué existe y documentarlo. Si no se entiende, marcar
  `# LEGACY: investigar` y escalar al humano.

## TIER 3 — ARQUITECTURA DEL PROYECTO

Separación estricta de capas (SoC). Nunca mezclar lógica, datos y presentación:

```
presentation/   → Streamlit (UI "tonta": solo renderiza)
domain/         → lógica de negocio, orquestación del DAG de capítulos, casos de uso
data/           → repositorios, acceso a PostgreSQL/pgvector, DTOs
infrastructure/ → wrappers: LLM gateway, conectores de fuentes, Ollama, embeddings
shared/         → tipos, constantes, utilidades, plantillas de párrafos
```

### Decisiones vigentes (ver ADRs para el detalle)
- **Retrieval:** RAG propio (pgvector + `nomic-embed-text` local). NotebookLM NO se
  usa en producción. (ADR-001)
- **Modelos:** local-primero; la redacción intenta local y escala a API solo si no
  pasa el umbral de calidad. Un único wrapper de LLM controla presupuesto, fallback,
  caps de tokens, circuit breaker y logging de costo a BD. (ADR-002)
- **Datos ausentes:** condición de RECUPERACIÓN, no de generación. Si el retrieval no
  supera el umbral de relevancia, NO se llama al modelo: se inserta párrafo de ausencia
  desde plantilla + recomendación al usuario de cómo conseguir la info. (ADR-002)
- **Fuentes:** doble vía hacia un solo índice. Automática (OpenAlex + arXiv + Crossref
  + web) y manual (PDFs sin API: EMIS, informes sectoriales). Se citan igual. Google
  Scholar NO programático. (ADR-003)
- **Estructura del informe:** DAG de capítulos. N0 fundacionales → N1 analíticos
  (paralelizables) → N2 síntesis (Cap 6 cruza Cap 2/3/4/5) → N3 meta (consume informe
  completo) → ensamblado en plantilla membrete. Cap 6 y N3 son barreras de
  sincronización: persistir estado antes de cruzarlas.

## TIER 4 — CALIDAD Y TRAZABILIDAD

- **Citación APA obligatoria.** Toda afirmación proveniente de fuentes se cita y es
  trazable hasta su fragmento (chunk). No inventar atribuciones.
- **No alucinar.** Solo afirmar lo sustentado en fragmentos recuperados. Si no hay
  evidencia, aplicar la regla de datos ausentes; nunca rellenar.
- **Historial completo en BD.** Persistir inputs del usuario, fuentes consultadas,
  respuestas crudas del LLM y documento final. Todo informe debe ser recuperable.
- **Commits:** Conventional Commits (`feat`, `fix`, `refactor`, `docs`, `test`,
  `chore`, `perf`). El cuerpo explica el *porqué*, no el *qué*.
- **Tests** en el mismo PR que el código que prueban. Cobertura mínima 80% en
  `domain/`.

## HOOKS ACTIVOS (cierran la brecha del 70%)

Definidos en `.claude/settings.json`. No dependen de que el agente "recuerde" la regla.

- **`check-secrets.sh`** (pre-commit, BLOQUEA): rechaza el commit si detecta claves,
  tokens o contraseñas en el diff.
- **`check-hardcoded-models.sh`** (pre-commit, BLOQUEA): rechaza si detecta nombres de
  modelo escritos en código de aplicación (deben ir en config).
- **`format-python.sh`** (post-edit, NO bloquea): corre `ruff` + `black` tras editar
  un `.py` y devuelve el resultado.

## RED FLAGS — DETENERSE Y ESCALAR

- Archivo o función que supera 300 líneas (señal de violación de SoC).
- Lógica de negocio crítica sin tests ni documentación.
- Dependencias circulares entre módulos.
- Discrepancia entre la documentación y el comportamiento real del sistema.

## COMANDOS ÚTILES

```bash
docker compose up -d            # levanta PostgreSQL+pgvector (bind mount)
curl http://127.0.0.1:11434/api/tags   # verifica que Ollama responde
ruff check . && black --check . # linting manual
pytest                          # corre tests
```
