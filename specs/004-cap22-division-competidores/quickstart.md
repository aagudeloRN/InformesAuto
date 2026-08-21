# Quickstart: Validación End-to-End — Cap 2.2

**Phase 1 output** | **Date**: 2026-08-20

---

## Prerrequisitos

```bash
# Instalar dependencias del proyecto
uv sync

# Verificar que PostgreSQL está corriendo (para tests de integración)
docker compose up -d
psql postgresql://user:pass@localhost:5434/informes_ic -c "\dt informes_ic.*"

# Verificar Ollama (solo para smoke test local, no requerido para tests unitarios)
curl http://127.0.0.1:11434/api/tags
```

---

## Escenario 1 — Clasificación correcta (test unitario)

**Qué valida**: Todas las empresas de un fixture de Cap 2.1 quedan clasificadas en la tabla 2×2.

```bash
pytest tests/test_generate_22_division.py::test_clasificacion_exhaustiva -v
```

**Fixture de entrada** (ubicado en `tests/fixtures/cap21_fixture.json`):
```json
{
  "texto": "...",
  "globales": {"candidatos": ["EmpresaA", "EmpresaB"], "n_candidatos_con_web": 2},
  "regionales": {"empresas_emis": ["EmpresaC"], "n_con_emis": 1},
  "startups": {"locales": ["StartupX"], "internacionales": ["StartupY"]},
  "retrieval_suficiente": true,
  "chunks_usados": []
}
```

**Resultado esperado**:
- `cap22.retrieval_suficiente == True`
- `len(cap22.clasificaciones) == 5` (EmpresaA, B, C, StartupX, StartupY)
- `sum(len(v) for v in cuadrantes.values()) == 5` (cobertura exhaustiva)
- `cap22.warnings_nombres_ajenos == []`

---

## Escenario 2 — Lista cerrada violada (test unitario)

**Qué valida**: El validador elimina nombres ajenos que el LLM haya introducido.

```bash
pytest tests/test_generate_22_division.py::test_lista_cerrada_nombre_ajeno -v
```

**Comportamiento del fake LLM** (stub): devuelve JSON con `"EmpresaZ"` (no está en el fixture).

**Resultado esperado**:
- `"EmpresaZ"` no aparece en `cap22.texto`
- `"EmpresaZ" in cap22.warnings_nombres_ajenos`
- `len(cap22.clasificaciones) == 5` (solo las 5 del fixture)

---

## Escenario 3 — Dataset vacío de Cap 2.1 (test unitario)

**Qué valida**: No se invoca el LLM y se devuelve párrafo de ausencia.

```bash
pytest tests/test_generate_22_division.py::test_cap21_vacio_devuelve_ausencia -v
```

**Resultado esperado**:
- `cap22.retrieval_suficiente == False`
- `cap22.texto` contiene `"## 2.2. División de Competidores"` y el párrafo de ausencia estándar
- El stub del LLM tiene 0 invocaciones

---

## Escenario 4 — Cuadrante vacío (test unitario)

**Qué valida**: Cuadrantes sin empresas muestran `(ninguno)` en el markdown.

```bash
pytest tests/test_generate_22_division.py::test_cuadrante_vacio_muestra_ninguno -v
```

**Fixture**: stub del LLM asigna todas las empresas a `masivo_tradicional`, los otros tres vacíos.

**Resultado esperado**: el `cap22.texto` contiene exactamente 3 celdas con `(ninguno)`.

---

## Escenario 5 — Idempotencia de regeneración (test unitario)

**Qué valida**: Regenerar Cap 2.2 con feedback no altera los checkpoints de Cap 1 ni Cap 2.1.

```bash
pytest tests/test_generate_22_division.py::test_regeneracion_no_altera_cap1_ni_cap21 -v
```

**Comportamiento**:
1. Llamar `generate_22(run_key="test_run", cap21=fixture, empresa=empresa_fixture)`
2. Capturar hash del checkpoint `"cap_1"` y `"cap_2_1"` en `FakeCheckpointRepo`
3. Llamar `generate_22(run_key="test_run", ..., feedback="Enfatizar más los entrantes")`
4. Verificar que los hashes de `"cap_1"` y `"cap_2_1"` no cambiaron

---

## Escenario 6 — JSON malformado del LLM (test unitario)

**Qué valida**: Tras 2 reintentos fallidos, se devuelve párrafo de ausencia.

```bash
pytest tests/test_generate_22_division.py::test_json_malformado_devuelve_ausencia -v
```

**Stub del LLM**: devuelve `"no es json"` en todas las invocaciones.

**Resultado esperado**:
- `cap22.retrieval_suficiente == False`
- Stub invocado exactamente 2 veces (retry policy)
- `cap22.texto` contiene párrafo de ausencia estándar

---

## Escenario 7 — Suite completa (cobertura ≥ 80%)

```bash
pytest tests/test_generate_22_division.py -v --cov=src/ic/domain/use_cases/generate_22_division --cov-report=term-missing
```

**Umbral mínimo**: 80% de cobertura en `generate_22_division.py` y `seccion22_assembler.py`.

---

## Smoke test manual (opcional, requiere LLM real)

```bash
# Requiere .env con OPENROUTER_API_KEY y un run_key con Cap 1 y 2.1 ya generados
python -c "
from ic.data.repositories.checkpoint_repo import CheckpointRepository
from ic.domain.use_cases.generate_22_division import Generate22Division
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import os, json

engine = create_engine(os.environ['DATABASE_URL'])
with Session(engine) as db:
    repo = CheckpointRepository(db)
    cap21_payload = repo.get_capitulo('mi_run_key', 'cap_2_1')
    cap1_payload  = repo.get_capitulo('mi_run_key', 'cap_1')
    # reconstruir objetos desde payload...
    # llamar generate_22 e imprimir resultado
    print('Texto generado:')
    print(cap22.texto[:500])
"
```

**Verificación manual**:
- El heading `## 2.2. División de Competidores` aparece.
- La tabla tiene exactamente 2 filas de datos y 3 columnas.
- Cada empresa de Cap 2.1 aparece en exactamente una celda.
- La subsección `### Síntesis de Presión Competitiva` contiene dos sub-headings `####`.
- El checkpoint `cap_2_2` existe en BD tras la ejecución.
