# FASE 13 — Hallazgos: Repositorio Sectorial RAG

**Fecha:** 2026-07-22 · **Branch:** `feature/fase13-rag-sectorial`

---

## 1. Objetivo

Etiquetar y filtrar el retrieval por sector GICS con un corpus permanente de 25 informes
sectoriales compilados de Ruta N, gestionable por UI y script de lote, con citación APA
fiel. Decisión de diseño formalizada en **ADR-012**.

---

## 2. Issues latentes detectados y corregidos (Chesterton's Fence)

1. **`fuente_tipo="pdf_manual"`** en `pdf_ingestor`: (a) violaba el `CheckConstraint`
   `ck_embed_fuente_tipo` (solo admite `web/pdf/openalex/arxiv/crossref`) y (b) el
   `apa_formatter` enrutaba el formato "Informe" solo con `fuente_tipo == "pdf"`, por lo que
   las citas de PDFs **nunca** salían como informe. → Estandarizado a `"pdf"`.
2. **Chunks sin `documento_id`**: el `DocumentoLocal` se creaba *después* de insertar los
   chunks, dejándolos sin FK. Impedía el JOIN para el filtro `solo_activos`. → Ahora el
   `DocumentoLocal` se crea **primero** y se estampa `documento_id` en cada chunk.
3. **`indice.csv` desalineado**: listaba `Energia.pdf`… pero los archivos reales son
   `PulsoEnergia.pdf`… en `documentos_sectoriales/` del repo (no en `~/documentos_sectoriales/`).
   Mapeo Pulso→GICS verificado determinista (25/25). → CSV reconciliado.
4. **Suposición falsa del código GICS** (detectada en la verificación E2E): la decisión #3
   asumía que `grupo_gics` del LLM "siempre incluye (GICS XXXX)". **No es cierto** con el
   prompt actual (`chain_02_gics`), que pide "nombre exacto del grupo" → el clasificador
   devuelve p.ej. `"Servicios al consumidor"` sin código. Resultado: `extract_gics_code`
   daba `None`, el filtro se desactivaba y —con el corpus ya ingestado— el informe citaba
   fuentes de **8 sectores distintos** (contaminación peor que antes). → `extract_gics_code`
   ahora hace **fallback por nombre**: resuelve el grupo contra los 25 nombres canónicos
   (el más largo contenido), manteniendo prioridad del regex si el código está presente.

---

## 3. Hallazgos de RepositorioRN (T13.8)

Revisado `~/Test/RepositorioRN` (`app/backend/services/rag/`). Prácticas aprovechables:

- **MMR de diversidad por documento** (`services/rag/mmr.py`): penaliza chunks del mismo
  documento para evitar que uno grande monopolice el contexto. λ=0.7 (70% similitud / 30%
  diversidad). **Adoptado en forma mínima:** un *cap por documento* (`rag_max_chunks_per_doc`,
  default 4) en `search_similar`. El MMR completo (reordenamiento por score compuesto) queda
  como follow-up documentado si el cap resulta insuficiente.
- **Tamaños de chunk**: RepositorioRN usa `chunk_size=1000 / overlap=200` (vs. 500/50 aquí)
  y `pool candidatos 40 → 20 final`, con `threshold` subido 0.35→0.50 para reducir ruido.
  Nuestro `fetch_k` se subió a `top_k*4` para dar margen al filtro sectorial + cap. Revisar
  chunk_size 500→1000 es un candidato de mejora (no incluido en Fase 13 para acotar alcance).
- **pgvector 0.8+**: soporta `hnsw.iterative_scan` (strict/relaxed) para filtros `WHERE`;
  recomienda índices parciales para pocos valores distintos. A la escala actual (25 docs) el
  scan exacto con filtro JSONB es suficiente; no se fuerza iterative_scan.

---

## 4. Cambios entregados

| Área | Archivo | Cambio |
|------|---------|--------|
| Esquema | `data/models/documento_local.py` | `sector_gics`, `activo`, `ensure_documento_columns()` + refresco de `ck_doc_tipo` |
| Constantes | `shared/constants/__init__.py` | `TipoDocumento.PAPER_ACADEMICO` |
| GICS | `shared/constants/gics_groups.py` | `extract_gics_code()`, `gics_options()` |
| Ingesta | `infrastructure/sources/pdf_ingestor.py` | `sector_gics`/`tipo`, `documento_id`, `fuente_tipo="pdf"`, `tipo_fuente` |
| Retrieval | `data/repositories/embedding_repo.py`, `infrastructure/retrieval/pgvector_store.py` | filtros `sector_gics`/`solo_activos` + cap por doc |
| Citación | `infrastructure/citation/apa_formatter.py` | `tipo_fuente` + APA "informe compilado" |
| Orquestación | `domain/use_cases/generate_informe.py` + N1/N2 use cases | `sector_gics_code` propagado; `_run_pdf` retirado (DT-017) |
| Repo | `data/repositories/documento_repo.py` (nuevo) | `list_all`, `set_activo`, `delete_with_chunks` |
| UI | `presentation/app.py` | pestaña "Repositorio": subida, listado, toggle, borrado |
| Lote | `scripts/ingest_batch.py` (nuevo) | carga idempotente desde `indice.csv` |

| Retrieval | `infrastructure/retrieval/pgvector_store.py`, `data/repositories/embedding_repo.py` | reserva de cupos sectoriales estrictos (`sector_estricto`) con umbral relajado |

Tests: `tests/test_fase13_sectorial.py` (12 tests fast) + suite existente. Gate: ruff 0,
`pytest -m "not slow"` → **179 passed**.

---

## 5. Evaluación con 3 empresas (T13.7)

Corpus ingestado: **25 documentos, 1746 chunks**, todos con `sector_gics` y
`tipo_fuente="informe_compilado"`, 25/25 activos (`scripts/ingest_batch.py`, 0 errores).

### 5.1 Hallazgo crítico durante la evaluación (divergencia del plan)

La primera medición reveló que el filtro `sector OR NULL` **elimina la contaminación
cross-sector** (objetivo ADR-012 ✓) **pero no garantiza que la evidencia sectorial aflore**:
la BD arrastra **2024 chunks web sin sector** (de corridas previas) que puntúan 0.80–0.83,
mientras el mejor chunk sectorial 2530 puntúa 0.779 y los de Materiales (1510) ~0.68 →
quedaban desplazados o bajo el umbral 0.7. Esto incumplía el objetivo central de la fase.

**Refinamiento aplicado (ADR-012):** cuando hay match de GICS, se **reservan cupos**
(`rag_sector_reserve=3`) para el corpus sectorial **estricto** (mismo GICS,
`tipo_fuente=informe_compilado`), con **umbral relajado** (`rag_sector_reserve_threshold=0.5`,
el corpus es on-topic por construcción). Los reservados se anteponen (ya filtrados por
umbral) y el resto rellena por score, sin re-ordenar para no expulsarlos.

### 5.2 Resultados (retrieval, top-10, umbral 0.7)

Métrica: chunks del **sector correcto** vs. chunks de **sector equivocado** (cross-sector)
recuperados, con Fase 13 (filtro + reserva) vs. línea base (sin filtro; equivale al
comportamiento pre-Fase-13, donde además no existía corpus sectorial).

| Empresa | CIIU | GICS | Fase 13: sect. correcto / cross | Base: sect. correcto / cross |
|---------|------|------|---------------------------------|------------------------------|
| Comfama | 8430 | 2530 | **3 / 0** | 1 / 4 |
| Andercol S.A.S. | 2011 | 1510 | **3 / 0** | 0 / 2 |
| Guane Emerging Technologies | — | 4510 | **3 / 0** | 0 / 4 |

**Lectura:** Fase 13 garantiza ≥3 fuentes del sector correcto y **cero** contaminación
cross-sector; la línea base recuperaba 0–1 fuentes correctas y 2–4 del sector equivocado.

### 5.3 Verificación E2E (PASO 5)

Informe completo de **Comfama** (CIIU 8430) generado con el pipeline real (costo $0 con
modelos free, ~21 min). El clasificador GICS lo asigna a **Seguros (4030)** —coherente con
una caja de compensación / seguridad social—, y el informe cita **1 fuente sectorial Ruta N
(Seguros) y 0 cross-sector**, en APA "[Informe compilado de múltiples fuentes]". (APA agrupa
un documento en una sola entrada aunque se citen varios de sus chunks.)

**Antes del fix del código GICS** (issue #4): el mismo informe citaba fuentes de **8
sectores distintos** (30 referencias) por contaminación cross-sector. **Después:** 1 sector,
19 referencias. El fix `extract_gics_code` (fallback por nombre) es lo que habilita el
filtrado efectivo en producción; sin él, con el corpus ingestado la contaminación empeora.

---

## 6. Deuda técnica / follow-ups

- **DT-017 saldado**: PDF hardcodeado retirado de `generate_informe.py`.
- **Follow-up**: MMR completo si el cap por documento resulta insuficiente.
- **Follow-up**: evaluar `chunk_size` 500→1000 y `threshold` 0.7 a la luz de RepositorioRN.
- **Follow-up**: índice parcial/GIN sobre `metadatos->>'sector_gics'` si el corpus crece.
