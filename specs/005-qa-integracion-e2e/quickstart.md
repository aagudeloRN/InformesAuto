# Quickstart: QA e Integración E2E + Deuda Estructural

**Date**: 2026-08-21 | **Updated**: 2026-09-15 | **Contracts**: [integration-test-contract.md](contracts/integration-test-contract.md)

Guía para correr los tests de integración una vez implementados.

---

## Prerequisitos

1. **BD activa**: `docker compose up -d` (PostgreSQL en `localhost:5434` con schema `informes_ic`).
2. **LLM configurado**: Ollama corriendo en host (`curl http://127.0.0.1:11434/api/tags` debe responder) o API key válida en `.env`.
3. **Dependencias instaladas**: `uv sync` desde la raíz del repo.
4. **`.env` configurado**: Variables de BD y modelo LLM presentes (ver `.env.example`).

---

## Correr los tests de integración

```bash
# Solo tests de integración
uv run pytest -m integration -v

# Con output de logs (útil para debug del spy LLM)
uv run pytest -m integration -v -s

# Un test específico
uv run pytest tests/integration/test_pipeline_e2e.py -m integration -v

# Tests de concurrencia (no requieren BD — corren sin flags también)
uv run pytest tests/integration/test_concurrencia.py -v
```

## Correr tests unitarios (sin integración)

```bash
# Modo normal — nunca ejecuta tests de integración
uv run pytest

# Confirmar que los 53 tests unitarios siguen en verde
uv run pytest tests/ -m "not integration" -q
```

---

## Escenario de validación: Pipeline E2E

**Setup**: BD activa + Ollama corriendo

```bash
uv run pytest tests/integration/test_pipeline_e2e.py -m integration -v -s
```

**Salida esperada**:
```
tests/integration/test_pipeline_e2e.py::test_informe_piloto_todos_capitulos PASSED
tests/integration/test_pipeline_e2e.py::test_checkpoints_persistidos PASSED
tests/integration/test_pipeline_e2e.py::test_cap22_en_posicion_correcta PASSED
tests/integration/test_pipeline_e2e.py::test_segunda_corrida_sin_error PASSED
```

**Si falla con SKIP**:
```
SKIPPED [1] tests/integration/conftest.py:XX: BD no disponible en localhost:5434 — arrancar PostgreSQL
```
→ Verificar que `docker compose up -d` está corriendo.

---

## Escenario de validación: Cache sectorial

**Prerequisito**: TC-001 a TC-004 pasaron (checkpoints en BD).

```bash
uv run pytest tests/integration/test_sector_cache.py -m integration -v -s
```

**Verificación manual adicional** (opcional):
```bash
# Ver los checkpoints sembrados en BD
uv run python -c "
from ic.data.database import SessionLocal
from ic.data.repositories.checkpoint_repo import CheckpointRepository
with SessionLocal() as db:
    repo = CheckpointRepository(db)
    keys = ['cap2_21_globales', 'cap2_21_regionales', 'cap2_21_startups', 'cap_2_2']
    for k in keys:
        r = repo.get_capitulo('__test__empresa_prueba:4510', k)
        print(k, '✓' if r else '✗')
"
```

---

## Escenario de validación: Concurrencia

```bash
# No requiere BD ni LLM
uv run pytest tests/integration/test_concurrencia.py -v
```

**Salida esperada**:
```
tests/integration/test_concurrencia.py::test_db_factory_sesiones_independientes PASSED
tests/integration/test_concurrencia.py::test_10_ejecuciones_sin_fallo PASSED
```

---

## Limpieza manual de datos de test

Si el teardown falló y quedan datos `__test__` en BD:

```bash
uv run python -c "
from ic.data.database import SessionLocal, engine
from ic.data.models.checkpoint import ensure_checkpoint_table
from sqlalchemy import text
ensure_checkpoint_table(engine)
with SessionLocal() as db:
    n = db.execute(text(\"DELETE FROM informes_ic.checkpoints WHERE run_key LIKE '__test__%'\")).rowcount
    db.commit()
    print(f'Eliminados {n} checkpoints de test')
"
```

---

---

## Escenario de validación: DT-040 — Gemini pricing

```bash
# Verificar que _PRICING tiene entradas Gemini
uv run python -c "
from ic.infrastructure.llm.gateway_pricing import _PRICING
gemini_keys = [k for k in _PRICING if 'gemini' in k]
print('Entradas Gemini:', gemini_keys)
for k in gemini_keys:
    pin, pout = _PRICING[k]
    assert pin > 0 and pout > 0, f'{k}: precios deben ser >0'
    print(f'  {k}: in={pin}, out={pout} ✓')
"
```

**Verificación en BD** (requiere corrida con modelo Gemini configurado en .env):
```bash
uv run python -c "
from ic.data.database import SessionLocal
from sqlalchemy import text
with SessionLocal() as db:
    rows = db.execute(text(\"SELECT modelo, costo_usd FROM informes_ic.llm_calls WHERE modelo LIKE 'gemini%' LIMIT 5\")).fetchall()
    for r in rows:
        print(r.modelo, r.costo_usd)
        assert r.costo_usd is not None and r.costo_usd > 0, 'BUG: costo_usd debe ser >0'
"
```

---

## Escenario de validación: DT-038 — SoC presentation→domain

```bash
# Verificar que app.py no importa de data/ directamente
grep -rn "from ic.data\." src/ic/presentation/
# Salida esperada: ninguna línea
```

---

## Escenario de validación: DT-037 y DT-039 — tamaño de módulos

```bash
# Verificar límite de 300 líneas en todos los módulos refactorizados
wc -l src/ic/infrastructure/llm/gateway*.py src/ic/domain/use_cases/generate_informe.py src/ic/domain/use_cases/_informe_*.py
# Ningún archivo debe superar 300 líneas
```

---

## Escenario de validación: cobertura domain/ ≥80%

```bash
uv run pytest --cov=ic.domain --cov-report=term-missing tests/ -m "not integration" -q
# La línea TOTAL debe mostrar ≥80%
```

---

## Checklist de validación completa

- [ ] `uv run pytest` pasa sin flags (sin integración, ruff 0)
- [ ] `uv run pytest -m integration` pasa (TC-001 a TC-009)
- [ ] `grep -rn "from ic.data" src/ic/presentation/` → vacío
- [ ] `wc -l src/ic/infrastructure/llm/gateway*.py` → todos <300
- [ ] `wc -l src/ic/domain/use_cases/generate_informe.py src/ic/domain/use_cases/_informe_*.py` → todos <300
- [ ] `pytest --cov=ic.domain` → TOTAL ≥80%
- [ ] `git status` no muestra el archivo `1`
- [ ] `documentos_sectoriales/FuentesExternas/README.md` existe y describe cada archivo
- [ ] `pyproject.toml` tiene el marker `integration` y `addopts = "-m 'not integration'"`
- [ ] Corrida con Gemini: `cost_usd > 0` en BD (no `0.0` ni `None`)
