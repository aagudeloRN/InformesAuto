# Quickstart — Validación Cap 2.1 Jugadores Clave Modular

**Feature**: 002-cap21-jugadores-clave | **Date**: 2026-08-19

---

## Prerrequisitos

1. `uv run pytest` corre sin errores en la rama base.
2. Docker Compose con PostgreSQL+pgvector levantado (`docker compose up -d`).
3. Variable `TAVILY_API_KEY` en `.env` (o `OPENROUTER_API_KEY` para el LLM de candidatos).
4. Al menos un sector con documentos EMIS indexados (para validar UC-2).
5. StartIA ya sembrada en `entidades` con `segmento='startup'` (para validar UC-3).

---

## Escenario 1 — Referentes Globales (UC-1)

**Objetivo**: Verificar que el sub-módulo Globales propone candidatos vía LLM, busca cada uno en web y genera perfiles en prosa.

```bash
# Correr test unitario con _FakeSession (sin DB ni web real)
uv run pytest tests/test_generate_21_globales.py -v

# Resultado esperado:
# PASSED test_candidatos_propuestos_y_filtrados
# PASSED test_candidatos_sin_web_se_omiten
# PASSED test_excluye_empresa_focal
# PASSED test_ausencia_si_cero_candidatos
# PASSED test_max_5_empresas_respetado
```

**Validación E2E (requiere Tavily + API LLM)**:

```bash
uv run python -c "
from ic.domain.use_cases.generate_21_globales import Generate21Globales
# Se instancia con LLM y store reales; verifica que:
# 1. candidatos[] tiene ≤5 elementos
# 2. texto contiene '### Referentes Globales'
# 3. chunks_usados no está vacío
# 4. No hay texto fabricado (verificar que texto.count('Dato no disponible') == 0)
print('Validar output manualmente en el log')
"
```

---

## Escenario 2 — Referentes Regionales (UC-2)

**Objetivo**: Verificar que el sub-módulo Regional usa EMIS como fuente primaria y genera ausencia si no hay chunks EMIS.

```bash
# Test unitario
uv run pytest tests/test_generate_21_regionales.py -v

# Resultado esperado:
# PASSED test_retrieval_emis_exclusivo
# PASSED test_ausencia_si_sin_chunks_emis
# PASSED test_complemento_web_no_reemplaza_emis
# PASSED test_max_3_empresas_regionales
```

**Verificar filtro `fuente_tipo_filter` en embedding_repo**:

```bash
uv run pytest tests/test_embedding_repo.py -k "fuente_tipo_filter" -v
# Nuevo test que verifica que el filtro se aplica en SQL y no rompe callers existentes
```

---

## Escenario 3 — Startups y Disruptores (UC-3)

**Objetivo**: Verificar que el sub-módulo Startups recupera locales de StartIA y busca internacionales en web.

```bash
# Test unitario
uv run pytest tests/test_generate_21_startups.py -v

# Resultado esperado:
# PASSED test_startups_locales_desde_kb
# PASSED test_internacionales_desde_web
# PASSED test_ausencia_si_sin_locales_ni_web
# PASSED test_deduplicacion_local_vs_internacional
# PASSED test_locales_aparecen_primero_en_prosa
```

---

## Escenario 4 — Orquestador y ensamblado (UC-4)

**Objetivo**: Verificar que el orquestador ejecuta los tres sub-módulos, deduplica y ensambla el texto.

```bash
uv run pytest tests/test_generate_21_jugadores.py -v

# Resultado esperado:
# PASSED test_ensambla_tres_subsecciones_en_orden
# PASSED test_deduplicacion_cross_tier
# PASSED test_resume_desde_checkpoint_parcial
# PASSED test_ausencia_total_si_todos_fallan
```

---

## Escenario 5 — Regresión: integración con `generate_benchmarking`

**Objetivo**: Verificar que el refactor de 2.1 no rompe el flujo existente de Cap 2.

```bash
uv run pytest tests/test_generate_benchmarking.py -v

# Resultado esperado: todos los tests existentes PASAN sin modificación
# El orquestador generate_21_jugadores debe ser invocable desde generate_benchmarking
# sin cambios en la interfaz pública de CapBenchmarking
```

---

## Criterios de aceptación de la validación

| Criterio | Cómo verificar |
|----------|---------------|
| SC-001: ≤3 min por sub-módulo | Log timestamp inicio/fin de cada use case |
| SC-002: ≥80% perfiles con 3 campos | Contar campos no vacíos en prosa generada en E2E |
| SC-003: 0% fabricación | Revisar que prosa no contiene "Dato no disponible" ni claims sin chunk |
| SC-004: Globales visible antes de terminar Regionales | Logs muestran checkpoint `cap2_21_globales` antes de `cap2_21_regionales` |
| SC-005: Reutilización de checkpoint | Segunda ejecución con misma empresa → `restore` devuelve valores sin re-generar |
| SC-006: ≥70% perfiles regionales desde EMIS | `chunks_usados` de `Cap21Regionales` tienen `fuente_tipo='emis'` |
| SC-007: Al menos 1 startup de StartIA | `locales` en `Cap21Startups` no vacío cuando sector tiene registros |
