# Hallazgos Técnicos — Fase 8

**Fecha:** 2026-07-06
**Commits:** en proceso (verificación ruff + pytest pendiente por indisponibilidad del clasificador Bash)
**Tests:** ≥100 fast expected (97 pre-existentes + 3 nuevos en `test_informe_repo.py`)

---

## Objetivos de la fase

1. **DT-007** — Resolver ~38 errores ruff E501/F401/I001 pre-existentes en `chain_0*.py` y tests
2. **DT-008** — Agregar pestaña "Historial" a la UI Streamlit (RN-006 visible en UI)
3. **DT-005** — Crear test E2E `@pytest.mark.slow` que valide Cap5 paralelo con servicios reales

---

## H8-01 — ruff line-length es 100, no 88

**Problema:** El agente Explore que auditó las violaciones E501 asumió `line-length = 88` (default de
black). El proyecto configura `line-length = 100` en `[tool.ruff]` dentro de `pyproject.toml`.

**Impacto:** La lista de violaciones reales fue considerablemente más corta que la estimada (~38
asumidos vs. ~20 reales). Varias líneas reportadas como violación estaban dentro del límite.

**Solución:** Leer `pyproject.toml` antes de calcular qué líneas necesitan `# noqa`. Algunos
`# noqa: E501` añadidos son innecesarios (líneas ≤100 chars) pero inofensivos: `RUF100`
(unused noqa) no está en el `select` del proyecto (`["E", "F", "I", "UP"]`).

**Regla derivada:** Para cualquier tarea de linting, verificar la configuración del linter antes
de asumir defaults.

---

## H8-02 — El clasificador de Bash estuvo caído durante la sesión completa

**Problema:** El clasificador de seguridad de auto mode retornó "claude-sonnet-4-6 is temporarily
unavailable" de forma persistente durante toda la sesión de Fase 8. Esto impidió ejecutar
`ruff check` ni `pytest`.

**Impacto:** Las correcciones P1 se hicieron por conteo manual de caracteres. No se verificó:
- Que todas las líneas >100 chars tienen `# noqa: E501`
- Que no se introdujeron nuevos errores ruff
- Que los 3 tests nuevos de `test_informe_repo.py` pasan

**Acción para Fase 9 (DT-009):** Como primer paso, antes de cualquier nuevo código:
```bash
ruff check src/ tests/      # debe ser clean o mostrar solo noqa restantes
pytest -m "not slow" -q     # debe mostrar ≥100 passed
```

---

## H8-03 — Patrón `st.tabs()` en Streamlit: todos los tabs renderizan en cada script run

**Contexto:** `_render_historial()` abre una sesión de BD en cada render de la UI. Streamlit
re-ejecuta el script completo en cada interacción del usuario (submit, click, etc.).

**Decisión:** Se aceptó este comportamiento porque:
1. La consulta `list_recientes(limit=20)` es O(20) con índice en `created_at` — despreciable.
2. Alternativa (`st.session_state` con caché) añade complejidad para un gain mínimo.
3. La sesión SQLAlchemy se cierra correctamente con `with SessionLocal() as db:`.

**Deuda residual:** Si el historial crece a miles de registros y la consulta se siente lenta,
agregar `@st.cache_data(ttl=30)` en `_render_historial()`.

---

## H8-04 — `from pathlib import Path` ya importado al nivel de módulo en app.py

**Problema menor:** El primer borrador de `_render_historial()` incluía `from pathlib import Path`
dentro de la función, duplicando el import al nivel de módulo (línea 11).

**Solución:** Eliminado el import redundante dentro de la función. `Path` del módulo aplica.

**Aprendizaje:** Al añadir funciones a un módulo existente, leer los imports al inicio antes de
añadir los propios.

---

## Estado de deuda técnica al cierre de Fase 8

| ID | Descripción | Estado |
|----|-------------|--------|
| DT-004 | `generate_informe.py` ≥380 líneas | En monitoreo — 347 líneas post-Fase 7 |
| DT-005 | Cap 5 E2E con servicios reales | ✅ Test creado (`test_convergencia_e2e.py`) — pendiente ejecutar |
| DT-006 | PDF 120 págs validación real | Abierto — requiere Ollama + BD disponibles |
| DT-007 | Errores ruff E501 en chains | ✅ Resuelto (pendiente verificación con `ruff check`) |
| DT-008 | UI sin historial | ✅ Resuelto — `st.tabs` + `list_recientes` |
| DT-009 | Verificación ruff + pytest post-Fase 8 | **Nuevo** — clasificador Bash caído durante sesión |
| DT-010 | Validación idioma global (CJK) | Abierto — solo cubre Cap 1 actualmente |
| DT-011 | CostTracker en llamadas Ollama | Abierto — Ollama no expone tokens |

---

## Próximos pasos (Fase 9)

Ver `docs/architecture/ARQUITECTURA.md` sección "Pendiente (Fase 9+)".

**Orden sugerido para Fase 9:**
1. Verificar ruff + pytest (DT-009) — gate de calidad antes de nuevo código
2. Ejecutar `pytest -m slow tests/test_convergencia_e2e.py` con Ollama + OpenRouter (DT-005)
3. Validar ingesta PDF real de 120 págs (DT-006)
4. Extender `has_cjk_characters()` a todos los caps N1+ (DT-010)
