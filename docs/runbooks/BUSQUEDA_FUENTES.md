# Runbook — Búsqueda de Fuentes para el Corpus EMIS

> **Propósito:** Guía para el analista que enriquece el corpus RAG con PDFs sectoriales.
> Las fuentes manuales (EMIS, informes académicos, sectoriales) se ingresan al índice igual
> que las fuentes automáticas; la diferencia está en cómo se obtienen, no en cómo se usan.
>
> **Origen:** `source_prompts/0. Ecuaciones de búsqueda.docx` (ecuaciones base);
> adaptado a runbook operativo en `docs/runbooks/BUSQUEDA_FUENTES.md`.

---

## 1. Contexto

El sistema RAG (ADR-001, ADR-012) combina dos vías de fuentes:
- **Automática:** WebConnector (Tavily), OpenAlexConnector — se activan en cada generación.
- **Manual:** PDFs de EMIS / informes sectoriales — se ingestán una vez y se reutilizan.

La vía manual es la palanca principal de calidad para caps N1 (Benchmarking, Tendencias,
Ecosistema). A mayor corpus EMIS curado por sector GICS, menos "Dato no disponible" aparece
en el informe final. El índice CSV vive en `documentos_sectoriales/FuentesEMIS/indice_emis.csv`.

---

## 2. Motores de búsqueda recomendados

| Motor | Tipo | Acceso | Cobertura |
|-------|------|--------|-----------|
| **EMIS** | Base de datos sectorial | Institucional (Ruta N) | Informes de mercado, perfiles de empresa, benchmarking por sector/país |
| **Scopus / Web of Science** | Académico | Institucional | Papers sobre tendencias tecnológicas, innovación, sostenibilidad |
| **Google Scholar** | Académico | Libre (no programático) | Papers, tesis, informes grises |
| **IBISWorld / Statista** | Sectorial | Institucional | Informes de industria, estadísticas de mercado |

> **IMPORTANTE:** Google Scholar NO se usa programáticamente (ToS). Solo para localizar PDFs
> que luego se descargan manualmente y se ingestán vía `ingest_batch.py`.

---

## 3. Ecuaciones de búsqueda base

Las siguientes ecuaciones se aplican en EMIS o motores académicos para recuperar PDFs de
tendencias, panorama sectorial e informes de mercado. Se ajustan sustituyendo los términos
del sector objetivo.

### Ejemplo: Sector Alimentos (GICS 3020)

**Ecuación 1 — Tendencias globales del sector:**
```
(Food OR "Food industry" OR alimento* OR foodtech) AND
(Trend* OR landscape OR view OR panorama OR outlook OR scene OR situation OR status OR
 state OR foresight OR forecast OR challenges OR reto* OR opportunit* OR oportunidad* OR driver*)
filetype:pdf
```

**Ecuación 2 — Subsector específico (ej. galletas/snacks):**
```
(Cookie OR cake OR wafer OR biscotto OR biscuit OR crackers OR galleta OR snack*) AND
(Trend* OR landscape OR view OR panorama OR outlook OR scene OR situation OR status OR
 state OR foresight OR forecast OR challenges OR reto* OR opportunit* OR oportunidad* OR driver*)
filetype:pdf
```

**Ecuación 3 — Contexto regional (Colombia / LatAm):**
```
(Food OR "Food industry" OR alimento* OR foodtech) AND
(Trend* OR landscape OR view OR panorama OR outlook OR scene OR situation OR status OR
 state OR foresight OR forecast OR challenges OR reto* OR opportunit* OR oportunidad* OR driver*)
AND (Medellín OR Antioquia OR Colombia OR "Latin America" OR "América Latina")
filetype:pdf
```

**Ecuación 4 — Subsector + regional:**
```
(Cookie OR cake OR wafer OR biscotto OR biscuit OR crackers OR galleta OR snack*) AND
(Trend* OR landscape OR view OR panorama OR outlook OR scene OR situation OR status OR
 state OR foresight OR forecast OR challenges OR reto* OR opportunit* OR oportunidad* OR driver*)
AND (Medellín OR Antioquia OR Colombia OR "Latin America" OR "América Latina")
filetype:pdf
```

**Ecuación 5 — Subsector compuesto (para EMIS sin `filetype`):**
```
("Cookie And Cracker") AND
(Trend* OR landscape OR view OR panorama OR outlook OR scene OR situation OR status OR
 state OR foresight OR forecast OR challenges OR reto* OR opportunit* OR oportunidad* OR driver*)
```

**Ecuación 6 — Español puro:**
```
(Galletas) AND (tendencias OR Estado) AND
(Medellín OR Antioquia OR Colombia OR "Latin America" OR "América Latina")
```

### Adaptación a otros sectores GICS

Sustituir los términos de producto/sector. Ejemplos:
- **Financiero (4020):** `(Fintech OR "Financial services" OR banca OR banco*)`
- **Salud (3510):** `(Healthcare OR salud OR "Medical devices" OR farmacéutic*)`
- **Tecnología (4510):** `(Software OR SaaS OR "Cloud computing" OR tecnología OR IT)`
- **Retail (2550):** `(Retail OR "e-commerce" OR comercio OR tienda OR distribución)`

---

## 4. Criterios de selección de PDFs

Un PDF candidato entra al corpus si cumple **todos** los criterios:

| Criterio | Regla |
|----------|-------|
| **Relevancia** | El contenido es del sector GICS objetivo (o cross-sector "global") |
| **Recencia** | Publicado en los últimos 5 años (o hasta 10 si es referencia clásica) |
| **Citabilidad** | Tiene autor/institución identificable y año de publicación |
| **Idioma** | Español o inglés (el sistema procesa ambos; el LLM genera en español) |
| **Tamaño** | Preferir < 50 MB (los PDFs muy grandes toman tiempo de ingesta) |
| **Tipo** | Informes de industria, papers académicos, reportes de consultoría, estadísticas |

**No ingresar:** páginas web convertidas a PDF sin autor/fecha, presentaciones de diapositivas
sin contenido sustantivo, duplicados del mismo informe en diferente versión.

---

## 5. Proceso de ingesta

### Paso 1 — Organizar archivos

Colocar los PDFs en la carpeta del sector correspondiente:
```
documentos_sectoriales/FuentesEMIS/<CarpetaSector>/
```

Nombrar como: `Autor. (Año). Título.pdf`

Ejemplo: `Fortune Business Insights. (2026). Global Food & Beverages Market Report.pdf`

### Paso 2 — Verificar / actualizar el índice CSV

El índice vive en `documentos_sectoriales/FuentesEMIS/indice_emis.csv`. Para regenerarlo:
```bash
uv run python scripts/build_emis_index.py
```

Revisar las columnas `sectores_adicionales` si el informe cubre más de un sector GICS.
Editar el CSV a mano para documentos multi-sector antes de la ingesta.

### Paso 3 — Ingestar

```bash
# Ingestar un sector específico (subset):
uv run python scripts/ingest_batch.py --sector 3020

# Ingestar todos los sectores (lote completo, ~2–4 h):
uv run python scripts/ingest_batch.py --all

# Ingestar un PDF global (aplica a todos los sectores):
uv run python scripts/ingest_global.py \
  --pdf "ruta/al/archivo.pdf" \
  --titulo "Nombre del informe" \
  --autor "Institución" \
  --año 2026
```

### Paso 4 — Verificar

```bash
# Ver chunks por sector tras la ingesta:
uv run python scripts/eval_coverage.py --sector 3020
```

El panel Repositorio de la UI también muestra la lista de documentos ingestados.

---

## 6. Documentos ya ingestados (corpus base, julio 2026)

| Tipo | Cantidad | Fuente |
|------|----------|--------|
| PDFs sectoriales EMIS (subset E2E) | ~250 PDFs / ~1746 chunks | `FuentesEMIS/` por sector |
| Documento global cross-sector | 1 PDF / 594 chunks | `InformeConvergenciaLocal2026V3RvADAA.pdf` |

El corpus base proporciona ~38–46 chunks por sector GICS. Para alcanzar cobertura óptima
(>100 chunks/sector), se recomienda completar el lote EMIS completo (DT-034).

---

## 7. Cobertura actual por sector

| Sector GICS | Chunks sectoriales | Chunks globales |
|---|---|---|
| 3020 (Alimentos) | 44 | 594 |
| 2510 (Automoción) | 46 | 594 |
| 4020 (Finanzas) | 43 | 594 |
| 3510 (Salud) | 39 | 594 |
| 4510 (IT) | 41 | 594 |
| 5010 (Telecom) | 38 | 594 |
| … (otros sectores) | 35–43 | 594 |

> Para los sectores con < 40 chunks sectoriales, priorizar la búsqueda de informes EMIS
> adicionales antes de lanzar un informe de esa industria.
