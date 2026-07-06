# Guía de Contribución — Informes de Inteligencia Competitiva

> Para agentes IA (Claude Code) y colaboradores humanos.
> Lee `CLAUDE.md` para reglas operativas de agentes; este documento es el contrato de calidad.

---

## Prerrequisitos para contribuir

1. Leer `CLAUDE.md` completo (reglas Tier 1 son no negociables).
2. Leer el ADR relevante antes de tocar módulos que los implementan.
3. Entender la separación de capas (`presentation/domain/data/infrastructure/shared`).

---

## Flujo de trabajo

### Para cambios no triviales (regla de oro)

1. **Plan Mode obligatorio** antes de tocar archivos.
2. Explorar código relevante → proponer plan → obtener aprobación → ejecutar.
3. Si durante la ejecución la realidad no coincide con el plan, volver a Plan Mode.

### Para cambios triviales (< 3 pasos, 1 archivo, sin decisiones de arquitectura)

Se puede ejecutar directamente, pero el commit debe ser igualmente atómico y con Conventional Commits.

---

## Convención de commits (Conventional Commits)

```
feat(scope): descripción en imperativo presente
fix(scope): descripción
refactor(scope): descripción
docs(scope): descripción
test(scope): descripción
chore(scope): descripción
perf(scope): descripción
```

El **cuerpo** del commit explica el **por qué**, no el qué (el diff ya muestra el qué).

**Scopes válidos:** `gateway`, `embedder`, `retrieval`, `chains`, `use-cases`, `assembler`,
`pipeline`, `tests`, `docs`, `config`, `types`, `ci`.

---

## Estructura de archivos nuevos

### Nueva cadena LCEL (chain N)

Archivo: `src/ic/domain/chains/chain_0N_nombre.py`

- `SYSTEM_PROMPT_NN` — string multilínea
- `USER_PROMPT_NN` — con variables `{var}` explícitas
- `build_chain_NN(llm) -> Runnable`
- Helpers de formateo (si son reutilizables, re-exportar desde chain anterior, no duplicar)

### Nuevo use case (N1 analítico)

Archivo: `src/ic/domain/use_cases/generate_nombre.py`

- Clase `GenerateNombre` con `__init__(chain, store, web_connector, ...)`
- Método `execute(nombre_empresa, descripcion_empresa, sector_gics) -> CapNombre`
- `_MIN_CHUNKS = 3` (ajustar si la naturaleza del capítulo lo justifica)
- Política de datos ausentes obligatoria
- Sin dependencias directas de librerías externas (solo wrappers de `infrastructure/`)

### Nuevo DTO

Archivo: `src/ic/shared/types.py` — añadir `@dataclass` con los campos estándar:
```python
@dataclass
class CapNombre:
    texto: str
    n_chunks_usados: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)
```

### Nuevos tests

Archivo: `tests/test_nombre.py`

- Todo mockeado (sin Ollama, sin BD, sin red)
- Tests mínimos obligatorios:
  1. Tipo correcto del output
  2. Inputs correctos al chain (`mock_chain.invoke.call_args`)
  3. Retrieval insuficiente → párrafo de ausencia
  4. Web sin resultados → no falla
  5. Ingest llamado al menos una vez
- Si el test requiere Ollama real: `@pytest.mark.slow` + `@requires_ollama`

---

## Política de modelos (ADR-006)

| Tier | Uso | Variable de entorno |
|------|-----|---------------------|
| `free` | Caps analíticos N1 (benchmarking, tendencias, ecosistema, convergencia) | `LLM_API_FREE_MODEL` |
| `free_alt` | Fallback N1 | `LLM_API_FREE_ALT_MODEL` |
| `synth` | Caps síntesis N2+N3 (accionables, resumen ejecutivo) | `LLM_API_SYNTH_MODEL` |
| `paid` | Último recurso (<$0.20/MTok) | `LLM_API_PAID_MODEL` |

**Nunca** hardcodear nombres de modelo. **Nunca** usar top-tier (Claude-3, GPT-4o, Gemini Ultra).

---

## Política de datos ausentes (ADR-002)

Si `check_retrieval_sufficient(chunks, min_chunks=3)` retorna `False`, el capítulo **no invoca el LLM**.
Se retorna un DTO con `retrieval_suficiente=False` y `texto=build_absent_paragraph("Cap N — Nombre")`.

Nunca rellenar con conocimiento general del LLM cuando el retrieval falla.

---

## Checklist pre-PR

```
[ ] Separación de capas respetada (domain no importa httpx, sqlalchemy, langchain directamente)
[ ] No hay nombres de modelo en código (solo en .env)
[ ] No hay credenciales en código
[ ] Tests nuevos en el mismo PR (cobertura mínima: flujo exitoso + datos ausentes)
[ ] @pytest.mark.slow en tests que usan Ollama real
[ ] CHANGELOG.md actualizado con entrada semántica
[ ] ADR creado si hay decisión arquitectónica nueva
[ ] README.md actualizado si cambia el estado del proyecto
[ ] Commit con Conventional Commits
[ ] ruff check pasa sin errores no-E501
```

---

## Red flags — detener y escalar

- Archivo o función > 300 líneas.
- Lógica de negocio sin tests.
- Dependencias circulares entre módulos.
- Diferencia entre docs y comportamiento real del sistema.
- `TODO` que bloquea ejecución.
