# Research: Cap 2.2 — División de Competidores

**Phase 0 output** | **Date**: 2026-08-20 | **Feature**: [spec.md](spec.md)

## 1. Patrón arquitectónico existente (Cap 2.1 como blueprint)

**Decision**: Replicar el ciclo `chain → use_case → types → assembler` de Cap 2.1.

**Rationale**: Es el único patrón probado en producción para N1 analíticos del informe. Mantiene SoC (domain ≠ infrastructure) y facilita la integración en el DAG existente.

**Estructura de blueprint**:
```
chain_cap2_21_globales.py      → chain_cap2_22_division.py
generate_21_jugadores.py       → generate_22_division.py
seccion21_assembler.py         → seccion22_assembler.py   (determinista: validación + formato)
Cap21Jugadores (types.py)      → Cap22Division (types.py)
```

**Alternativas consideradas**:
- Chain inline dentro del use_case → rechazado (viola SoC).
- Assembler determinista puro sin LLM → rechazado (la clasificación en cuadrantes requiere razonamiento sobre atributos de ficha).

---

## 2. Input para Cap 2.2

**Decision**: El use_case recibe `Cap21Jugadores` (tipo ya existente) + `DescripcionEmpresa` (Cap 1, tipo ya existente).

**Rationale**: Ambos tipos están disponibles en el momento de ejecución del DAG cuando se llega a N1. No se necesita retrieval adicional; los datos de 2.1 ya incluyen los atributos de ficha (portafolio, canales/precios, factor diferencial, propuesta de valor) necesarios para la clasificación.

**Cómo se extrae la lista cerrada**:
```python
# De Cap21Jugadores se extraen todos los nombres:
names_globales   = cap21.globales.candidatos  if cap21.globales   else []
names_regionales = cap21.regionales.empresas_emis if cap21.regionales else []
names_startups   = cap21.startups.locales + cap21.startups.internacionales if cap21.startups else []
closed_list      = names_globales + names_regionales + names_startups
```

**Alternativas consideradas**:
- Re-leer de BD el JSON de 2.1 → rechazado (duplica el viaje a BD; el objeto ya está en memoria).
- Pasar solo `texto` de Cap 2.1 → rechazado (el texto es markdown procesado; la lista cerrada se deriva mejor de los campos estructurados).

---

## 3. Clasificación en cuadrantes: LLM vs. reglas deterministas

**Decision**: LLM clasifica; un validador determinista post-procesamiento aplica la lista cerrada.

**Rationale**: La dimensión "volumen vs. nicho" y "tradicional vs. innovador" requiere razonamiento sobre portafolio, canales y factor diferencial — imposible codificar como reglas estáticas sin degradar la calidad del análisis. El LLM usa los atributos de ficha de 2.1 como evidencia.

**Estrategia de grounding (lista cerrada)**:
1. El prompt enumera explícitamente las empresas que el LLM DEBE clasificar (closed list injection).
2. El validador post-gen extrae los nombres de la tabla markdown de salida y calcula la diferencia con la lista cerrada.
3. Nombres ajenos → eliminados + warning en log. Nombres faltantes → añadidos a `(ninguno)` del cuadrante más probable o marcados para revisión humana.

**Formato de salida del LLM** (prompting estructurado):
El LLM produce JSON interno con la clasificación antes de renderizar el markdown. Esto facilita el parsing y la validación determinista:
```json
{
  "cuadrantes": {
    "masivo_tradicional": ["Empresa A", "Empresa B"],
    "masivo_innovador": [],
    "nicho_tradicional": ["Empresa C"],
    "nicho_innovador": ["Empresa D", "Empresa E"]
  },
  "intro": "...",
  "sintesis_incumbente": "...",
  "sintesis_entrante": "..."
}
```
El assembler convierte este JSON a markdown final; no se depende del markdown raw del LLM.

**Retry policy**: si el JSON está malformado, reintento hasta 2 veces antes de devolver párrafo de ausencia.

**Alternativas consideradas**:
- LLM produce markdown directamente → rechazado (parsing frágil para extracción de nombres).
- Clasificación con embeddings + KNN sobre cuadrantes pre-etiquetados → rechazado (complejidad desproporcionada; no hay training data de cuadrantes).

---

## 4. Persistencia (CheckpointRepository)

**Decision**: Usar `CheckpointRepository.save_capitulo(run_key, "cap_2_2", payload)`.

**Rationale**: Es el mecanismo estándar del sistema para todos los capítulos. `cap_nombre = "cap_2_2"` es la clave canónica para este subcapítulo.

**Payload**:
```python
{
    "texto": str,             # markdown final de la sección 2.2
    "clasificaciones": [      # lista de ClasificacionCompetidor (serializada)
        {"nombre": str, "cuadrante": str, "dato_no_disponible": bool}
    ],
    "n_empresas_procesadas": int,
    "warnings_nombres_ajenos": list[str],
    "retrieval_suficiente": bool,
}
```

**Idempotencia**: `save_capitulo` hace upsert por `(run_key, cap_nombre)`. Una regeneración sobrescribe el registro existente. Los checkpoints de Cap 1 y 2.1 tienen claves distintas (`"cap_1"`, `"cap_2_1"`) → no pueden ser sobreescritos por Cap 2.2.

---

## 5. Integración con el revisor automático (self_review_hooks)

**Decision**: Usar `review_web_cap` (el mismo hook que Cap 2/3/4), con `chain_judge` + `chain_revise`.

**Rationale**: Cap 2.2 es un capítulo analítico de tipo N1 que usa fuentes (atributos de ficha de 2.1), el mismo perfil que los demás capítulos de la sección 2. El hook existente encapsula el ciclo juez → crítica → revisión.

**Diferencia clave**: el `chain_revise` de Cap 2.2 recibe adicionalmente la lista cerrada de empresas como contexto de sistema (`CLOSED_LIST_CONSTRAINT`) para que la revisión tampoco introduzca nuevos actores.

---

## 6. Modelos LLM

**Decision**: Modelo analítico vía OpenRouter, leído de `config` (nunca hardcodeado). Priorizar free tier.

**Routing**: misma tabla de routing del sistema (ADR-002). El use_case recibe el `llm` inyectado como dependencia — no instancia modelos directamente.

**Variables de entorno relevantes** (ya existen, sin cambios):
- `OPENROUTER_API_KEY` 
- `LLM_MODEL_SYNTHESIS` o la clave de routing analítico

---

## 7. Posición en el DAG del informe

**Decision**: Cap 2.2 es nodo N1, dependiente de Cap 2.1 (que depende de Cap 1, N0).

**Relaciones**:
```
N0: Cap 1 (DescripcionEmpresa + ClasificacionGICS)
N1: Cap 2.1 (Cap21Jugadores) ←── Cap 2.2 (Cap22Division)   [paralelo con Cap 3, 4, 5]
N2: Cap 6 (síntesis, barrera de sincronización)
```

Cap 2.2 no bloquea otros N1; se ejecuta en paralelo con Cap 3, 4 y 5. La barrera de sincronización de N2 (Cap 6) ya espera a todos los N1.

**Integración en `generate_n1.py`**: añadir `Generate22Division` al executor del ThreadPoolExecutor existente, con la misma firma de dependencias de los demás N1.

**`InformePiloto`** (types.py): añadir `cap_22_division: "Cap22Division | None" = None`.

---

## 8. Tests

**Decision**: Tests unitarios en `tests/test_generate_22_division.py` con `_FakeSession` y fixtures JSON de Cap 2.1.

**Escenarios obligatorios (≥ 80% cobertura en domain/)**:
1. Clasificación correcta: N empresas → N clasificaciones, suma cuadrantes = N.
2. Lista cerrada: nombre ajeno en JSON del LLM → eliminado del output.
3. Dataset Cap 2.1 vacío → párrafo de ausencia, sin llamada al LLM.
4. JSON malformado del LLM → reintento x2 → párrafo de ausencia.
5. Idempotencia de regeneración: checkpoints de Cap 1 y 2.1 inalterados.
6. Cuadrante vacío → celda muestra `(ninguno)`.
