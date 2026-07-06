# ADR-007: Gestión de memoria en entorno WSL2 — Tests, OpenBLAS y Ollama

**Status:** Accepted
**Date:** 2026-07-06
**Supersedes:** —
**See also:** ADR-002 (routing local-primero), ADR-006 (presupuesto modelos)

---

## Contexto

El entorno de desarrollo es WSL2 con **8 GB de RAM total** asignada al subsistema Linux.
Durante la Fase 5E se produjeron dos crasheos de proceso distintos al ejecutar la suite de
tests, ambos por agotamiento de memoria:

### Crash 1 — OpenBLAS multithreading durante `pytest`

**Síntoma:** `pytest` muere con `IOT instruction` (SIGABRT / OOM-killer) a mitad de la suite.
Mensaje previo: `memory allocation of 262144 bytes failed`.

**Causa raíz:** `numpy`/`scikit-learn` (dependencias transitivas de `langchain-community`)
usan OpenBLAS, que por defecto lanza tantos hilos como CPUs lógicas reporta el host.
En WSL2 el número de CPUs lógicas suele ser 8–16 (los del host Windows), pero la RAM es
limitada. Con múltiples workers de pytest y OpenBLAS multiplicando hilos, la memoria se
agota antes de completar la suite.

**Variable culpable:** `OPENBLAS_NUM_THREADS` (sin fijar = # CPUs lógicas).
Variable hermana igualmente peligrosa: `OMP_NUM_THREADS` (OpenMP, misma dinámica).

### Crash 2 — Build de Rust (hatchling) durante `uv add`

**Síntoma:** `memory allocation of 262144 bytes failed` + `RUST_BACKTRACE=1` hint durante
`uv add --dev pytest-env` mientras Ollama tenía un modelo cargado en RAM.

**Causa raíz:** Ollama mantiene el modelo en VRAM/RAM entre requests (comportamiento default).
Con el modelo cargado (~4 GB para `qwen3:8b`) + el compilador de Rust lanzado por hatchling,
la RAM disponible fue insuficiente.

**Mitigación ya cubierta:** `keep_alive: 0` en embedder y gateway (ADR-002, Fase 5C)
descarga el modelo tras cada request. El crash de `uv add` fue aislado y no recurrente.

---

## Decisión

### D1 — Fijar `OPENBLAS_NUM_THREADS=1` y `OMP_NUM_THREADS=1` para toda la suite de tests

Las variables se declaran en `pyproject.toml` bajo `[tool.pytest.ini_options]`, gestionadas
por el plugin `pytest-env` (instalado como dependencia de desarrollo):

```toml
[tool.pytest.ini_options]
env = [
    "OPENBLAS_NUM_THREADS=1",
    "OMP_NUM_THREADS=1",
]
```

**Por qué `pytest-env` y no otro mecanismo:**
- Un `conftest.py` con `os.environ` funciona igual pero requiere que el conftest se cargue
  antes de cualquier import de numpy (frágil, depende del orden de imports).
- Un `.env` de shell (`export`) no se propaga a subprocesos spawneados por pytest-xdist.
- `pytest-env` es el mecanismo oficial y robusto para fijar variables de entorno antes de
  que pytest cargue cualquier módulo del proyecto.

**Impacto en rendimiento:** El rendimiento de los tests no se degrada — los tests son
operaciones de IO/mock, no de cómputo matricial. La limitación a 1 hilo aplica solo al
pool de OpenBLAS, no a asyncio ni a ThreadPoolExecutor del código bajo test.

### D2 — Marcar `@pytest.mark.slow` todos los tests que invocan Ollama o red real

Regla: cualquier test que llame a `Embedder.embed()`, `OllamaGatewayLLM._call()` o cualquier
conector de red externo (web, OpenRouter, OpenAlex) **debe** llevar `@pytest.mark.slow`.

```python
@pytest.mark.slow
@requires_ollama
@requires_network
def test_pilot_end_to_end_noel(tmp_path):
    ...
```

**Por qué es importante:** Sin este marker, `pytest -m "not slow"` no puede excluir esos
tests. Si Ollama está bajo presión de memoria (modelo cargado de otra sesión) y un test
llama al embedder, el fallo es un 500 del servidor, no un skip limpio. Mezclar tests de
integración con Ollama en la suite rápida hace la CI frágil.

**Convención de runner:**

```bash
# Suite rápida (CI, desarrollo normal) — sin Ollama, sin red
uv run pytest -m "not slow"

# Suite completa (validación pre-release) — requiere Ollama + BD + red
uv run pytest
```

### D3 — Nunca ejecutar `uv add` / operaciones de compilación con Ollama cargado

Antes de cualquier `uv add`, `pip install` o acción que lance el compilador de Rust:

```bash
# Verificar RAM disponible
free -m | awk '/^Mem/ {print $7 " MB disponibles"}'

# Si < 3000 MB libres, reiniciar Ollama para vaciar el modelo
sudo systemctl restart ollama   # o matar el proceso con kill
```

Esto no es automatizable sin riesgo de perder contexto de sesión, por lo que queda como
procedimiento operativo documentado aquí.

---

## Consecuencias

### Positivas
- La suite rápida (`-m "not slow"`) pasa en ~1 s y no crashea por memoria.
- El marker `slow` documenta explícitamente el coste de cada test de integración.
- `pytest-env` es la fuente canónica de configuración de entorno para tests; no hay magia
  de shell ni conftest frágil.
- La regla D3 previene el crash de compilación más común en el entorno.

### Negativas / Trade-offs
- `pytest-env` añade una dependencia de desarrollo. Es mínima (sin deps propias) y estable.
- Fijar `OPENBLAS_NUM_THREADS=1` deja rendimiento de cómputo matricial sobre la mesa en
  pruebas de benchmark numérico. No aplica a este proyecto (no hay tests de performance ML).
- D3 requiere disciplina manual; no hay hook que lo fuerce.

---

## Alternativas consideradas

| Alternativa | Razón de rechazo |
|-------------|-----------------|
| `conftest.py` con `os.environ` | Frágil ante orden de imports; no garantizado antes de numpy |
| Fijar en `.env` del shell | No propaga a workers de pytest-xdist; opaco para nuevos colaboradores |
| `pytest-xdist` con `--forked` | Overhead innecesario; el problema es RAM, no isolación por test |
| Limitar RAM de WSL2 a 6 GB | Agrava el problema; la solución es reducir consumo, no la disponibilidad |
| Aumentar RAM de WSL2 a 16 GB | No disponible en el equipo corporativo (sin admin en Windows) |
