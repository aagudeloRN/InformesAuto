# Hallazgos Técnicos — Fase 10

**Fecha:** 2026-07-21
**Commits:** pendiente (feature/fase10-fiabilidad-contenido)
**Tests fast:** 137 passed, 2 skipped

---

## Objetivos de la fase

1. **T10.1** — Extender validación CJK a todos los caps N1–N3 (cierra DT-009 lado idioma)
2. **T10.2** — Citación inline trazable: enriquecer contexto de chain_03 + validador de huérfanas
3. **T10.3/T10.4** — APA 7 fiel con dispatch por tipo de fuente + tests de contrato
4. **T10.5** — Panel de fiabilidad en HistorialInforme + UI Historial
5. **T10.6** — Desacoplar "piloto": footer/disclaimer parametrizable vía Settings

---

## H10-01 — APA 7: dispatch por tipo de fuente, no por heurística de autor

**Problema:** `format_reference()` usaba la misma plantilla para todos los chunks, independientemente
de su `fuente_tipo`. El resultado era APA incorrecto para fuentes académicas (sin cursiva en fuente)
y para PDFs sectoriales (sin marcador `[Informe]`).

**Solución:** Tres funciones privadas (`_apa_web`, `_apa_academic`, `_apa_report`) seleccionadas
por `fuente_tipo` del `ChunkResult`. La distinción persona/organización quedó como heurística dentro
de cada función (presencia de coma en el nombre del autor).

**Decisión:** Las cursivas (`*titulo*`, `*fuente*`) se emiten como marcadores Markdown en el `apa_string`.
El renderizador docx de Fase 11 los convertirá a estilo Word. No se aplican en Fase 10 para no acoplar
la capa de datos con la de presentación (PRIME DIRECTIVE §1.2).

**Archivos:** `src/ic/infrastructure/citation/apa_formatter.py`

---

## H10-02 — Citación inline: solo chain_03 pide (Autor, año); no se fuerza en cadenas narrativas

**Problema:** El roadmap pedía inyectar citas inline en "cada chain", pero chains 04, 06 y 07 tienen
explícitamente "Sin citaciones inline" en sus prompts (coherencia de estilo storytelling).

**Decisión:** Solo se enriqueció el contexto de chain_03 (Análisis Competitivo) con metadatos
autor/año, que es la única chain que ya pedía `(Autor, año)` en su SYSTEM_PROMPT. Las demás
chains conservan su política. El validador de huérfanas (`find_orphan_citations`) se ejecuta sobre
el texto completo del informe en `_run_n3()` y loguea warnings — no bloquea la generación.

**Ajuste al plan original:** En lugar de crear `tests/test_orphan_checker.py` como archivo separado,
los tests del orphan checker se consolidaron en `tests/test_apa_formatter_v2.py` (sección
`TestFindOrphanCitations`) junto a los tests del resto del formatter, por cohesión temática.

**Archivos:** `src/ic/infrastructure/citation/apa_formatter.py` (funciones nuevas:
`format_chunks_with_meta`, `find_orphan_citations`), `src/ic/domain/chains/chain_03_benchmarking.py`,
`src/ic/domain/use_cases/generate_informe.py`

---

## H10-03 — CJK: 6 use cases actualizados, deduplicación en convergencia requería chunks únicos

**Problema:** El test de convergencia fallaba porque `_DUMMY_CHUNKS` usaba el mismo `chunk_texto`
para todos los elementos. La lógica de deduplicación de `GenerateConvergencia` (que deduplicaba
por `chunk_texto[:60]` cuando no hay URL) colapsaba los 5 chunks en 1, cayendo por debajo de
`_MIN_CHUNKS=5`.

**Solución:** El helper `_make_chunks(n)` en `test_validators_idioma.py` genera chunks con texto
y URLs únicos por índice, garantizando que la deduplicación conserva todos los chunks.

**Regla derivada:** Al probar use cases con deduplicación interna, los mocks de chunks deben
tener atributos únicos (texto o URL) para sobrevivir la deduplicación.

**Archivos:** `src/ic/domain/use_cases/generate_benchmarking.py`, `generate_tendencias.py`,
`generate_ecosistema.py`, `generate_convergencia.py`, `generate_accionables.py`,
`generate_resumen_ejecutivo.py`, `tests/test_validators_idioma.py`

---

## H10-04 — Panel de fiabilidad: JSONB flexible evita migraciones futuras

**Decisión:** La columna `metricas_fiabilidad` es `JSONB` en vez de columnas individuales para
cada métrica. Esto permite añadir nuevas métricas (p. ej. latencia por cap, score de retrieval
promedio) en Fases futuras sin nuevas migraciones de esquema.

**Esquema del JSON persistido:**
```json
{
  "n_caps_ok": 5,
  "n_caps_total": 7,
  "caps_ausencia": ["Cap 3 — Tendencias"],
  "n_fuentes_total": 12,
  "n_citas_huerfanas": 0
}
```

La migración se añadió a `ensure_historial_columns()` (patrón existente, idempotente).
El modelo ORM tiene el campo `metricas_fiabilidad: Mapped[dict | None]`.

**Archivos:** `src/ic/data/models/historial_informe.py`, `src/ic/data/repositories/informe_repo.py`,
`src/ic/domain/use_cases/generate_informe.py`, `src/ic/presentation/app.py`

---

## H10-05 — Disclaimer "NOEL" eliminado; default en Settings y en assembler

**Decisión:** Se añadió `informe_disclaimer` a `Settings` con el texto genérico como default.
`PilotAssembler` recibe el disclaimer en su constructor (con el mismo default como fallback).
Los tests existentes de `test_assembler.py` no requirieron modificación porque el parámetro
es opcional con default.

**Nota:** La constante `_DEFAULT_DISCLAIMER` en `assembler.py` y el valor en `Settings` son
idénticos por diseño — el orchestrator pasa `settings.informe_disclaimer` y el assembler lo usa.
Si se pasa una cadena vacía, no se añade párrafo de disclaimer (caso "silenciar en tests").

**Archivos:** `src/ic/shared/config.py`, `src/ic/domain/assembler.py`,
`src/ic/domain/use_cases/generate_informe.py`

---

## Estado de deuda técnica al cierre de Fase 10

| ID | Descripción | Estado |
|----|-------------|--------|
| DT-004 | `generate_informe.py` ≥300 líneas | 🟡 369 L → separar en Fase 12 (T12.5) |
| DT-009 | Validación idioma global (CJK) | ✅ Cerrado — todos los caps N1–N3 protegidos |
| DT-015 | APA 7 no fiel | ✅ Cerrado — dispatch por tipo, marcadores cursiva para Fase 11 |
| DT-017 | Footer "NOEL" / disclaimer hardcodeado | ✅ Cerrado — parametrizable en Settings |
| DT-018 | Hook check-ruff.sh en settings.json | 🟡 Parcial — script listo, settings.json manual |
| DT-016 | Formato .docx pobre | ⬜ Fase 11 |

---

## Próximos pasos (Fase 11)

Ver `docs/architecture/ROADMAP_FASE9+.md` sección "FASE 11".

**Prioridades:**
1. `report_model.py` — modelo de documento intermedio (bloques semánticos)
2. `docx_renderer.py` — portada, TOC, paginación, cursivas APA (marcadores de Fase 10)
3. Cap 2 con tabla real + al menos 1 figura
4. PDF vía LibreOffice headless
