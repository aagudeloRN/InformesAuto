# Quickstart: Validación de Cap 2.1 Sub-módulos

**Date**: 2026-08-20 | **Feature**: 003-cap21-activar-submodulos

## Prerequisitos

```bash
docker compose up -d          # PostgreSQL+pgvector activo
curl http://127.0.0.1:11434/api/tags  # Ollama respondiendo
```

## Validación 1 — Numeración de encabezados (unitaria, sin BD)

```bash
uv run pytest tests/test_generate_21_headings.py -v
```

**Esperado**: tres tests pasan verificando que:
- `Cap21Globales.texto` contiene `"### 2.1.1. Referentes Globales"`
- `Cap21Regionales.texto` contiene `"### 2.1.2. Referentes Regionales LatAm/Colombia"`
- `Cap21Startups.texto` contiene `"### 2.1.3. Startups y Disruptores del sector"`

## Validación 2 — Sub-módulos invocados en pipeline (unitaria, mocks)

```bash
uv run pytest tests/test_generate_n1_jugadores.py -v
```

**Esperado**: test pasa verificando que al invocar `_fn_cap2` con mocks, `jugadores_use_case.execute()` fue llamado al menos una vez.

## Validación 3 — Regresión: tests existentes

```bash
uv run pytest tests/test_generate_benchmarking_jugadores.py tests/test_generate_21_startups.py -v
```

**Esperado**: todos pasan sin modificaciones.

## Validación 4 — UI (integración manual)

1. `streamlit run src/presentation/app.py --server.port 8503`
2. Generar informe para empresa del sector Alimentos
3. En la sección **2.1 Jugadores Clave** verificar:
   - Encabezado `2.1.1. Referentes Globales` presente
   - Encabezado `2.1.2. Referentes Regionales LatAm/Colombia` presente  
   - Encabezado `2.1.3. Startups y Disruptores del sector` presente
   - Contenido separado por sub-sección, no continuo

## Validación 5 — Cache sectorial (integración con BD)

1. Generar informe para empresa A (sector X) → anotar tiempo de generación de 2.1
2. Generar informe para empresa B (mismo sector X)
3. El segundo informe debe completar la sección 2.1 en < 10 s
4. Verificar en BD: `SELECT cap_nombre, LENGTH(contenido) FROM informes_ic.checkpoints WHERE run_key LIKE 'sector_%' AND cap_nombre LIKE 'cap2_21%';`
