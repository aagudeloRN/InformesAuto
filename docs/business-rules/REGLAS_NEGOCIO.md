# Reglas de Negocio del Sistema

> Reglas invariantes que definen el comportamiento del sistema de informes.
> Cada regla tiene un código `RN-NNN` para referencia desde el código y los ADRs.

---

## RN-001 — Datos ausentes: condición de recuperación, no de generación

**Regla:** Si el retrieval RAG retorna menos de `MIN_CHUNKS` fragmentos con score ≥ `RAG_SIMILARITY_THRESHOLD`,
el sistema **no invoca el LLM**. Inserta un párrafo de ausencia estándar generado desde plantilla.

**Implementación:** `domain/absent_data.py` → `check_retrieval_sufficient()` + `build_absent_paragraph()`

**Umbral por defecto:** `MIN_CHUNKS = 3`, configurable por capítulo.

**Razón:** Evitar que el LLM fabrique contenido cuando no hay evidencia suficiente. El párrafo de
ausencia le indica al analista humano qué buscar para enriquecer el informe.

**Formato del párrafo de ausencia:**
```
No se encontró información suficiente para generar [Cap N — Nombre].
Recomendación: ingestar PDFs sectoriales relevantes con `scripts/ingest_pdf.py`
o verificar conectividad con Tavily/DDG para búsquedas web.
```

---

## RN-002 — Citación APA 7 obligatoria y trazable

**Regla:** Toda afirmación en el informe que provenga de fuentes externas debe ser trazable hasta
su `ChunkResult` de origen. Las referencias se generan en APA 7 a partir de los metadatos del chunk.

**Implementación:** `infrastructure/citation/apa_formatter.py` → `build_references_section()`

**Campos requeridos en metadatos del chunk:**
- `titulo` — título del documento o página
- `autor` — autor (puede ser `None` → "Autor desconocido")
- `año` — año de publicación (puede ser `None` → "s.f.")
- `fuente_nombre` — nombre de la fuente (OpenAlex, web, PDF manual)
- URL del chunk (campo `fuente_url` en `ChunkResult`)

**Regla de deduplicación:** Solo se incluye una referencia por URL única. Los chunks del mismo
documento comparten referencia.

---

## RN-003 — Política de modelos: local-primero, API solo si supera umbral

**Regla:** El LLM local (Ollama) tiene prioridad. La API externa (OpenRouter) se usa para caps
analíticos y de síntesis que requieren mayor capacidad de razonamiento.

**Tiers (ver ADR-006):**
- N0 (Cap 1, GICS): local Ollama con fallback API free
- N1 (Caps 2-5): API free OpenRouter
- N2 (Cap 6 Accionables): API free o synth
- N3 (Resumen Ejecutivo): API synth

**Prohibición absoluta:** Modelos top-tier (Claude-3, GPT-4o, Gemini Ultra, o1/o3). Presupuesto
máximo: $1.00 USD por informe completo.

**Nombres de modelo:** Solo en `.env`. Nunca en código de aplicación.

---

## RN-004 — Ingesta de fuentes: doble vía hacia un único índice

**Regla:** Toda fuente —automática (web, OpenAlex) o manual (PDF)— se indexa en el mismo store
pgvector. Las búsquedas RAG no distinguen el origen de la fuente.

**Fuentes automáticas:** `WebConnector` (Tavily/DDG) + `OpenAlexConnector`
**Fuentes manuales:** PDFs via `scripts/ingest_pdf.py` (con anti-duplicados SHA-256)
**Fuentes prohibidas:** Google Scholar programático (ToS).

**Namespace de fuentes:** el campo `fuente_tipo` en el chunk puede ser `"web"`, `"openalex"`, `"pdf"`.

---

## RN-005 — Estructura del informe: DAG de capítulos con barreras de sincronización

**Regla:** Los capítulos siguen un grafo acíclico dirigido. Las barreras de sincronización
garantizan que los inputs de cada nivel estén completos antes de avanzar.

```
N0 (fundacionales): Cap 1 Descripción + GICS
  ↓ barrera: N0 completo antes de N1
N1 (analíticos): Cap 2 Benchmarking ‖ Cap 3 Tendencial ‖ Cap 4 Ecosistema ‖ Cap 5 Convergencia
  ↓ barrera: N1 completo antes de N2
N2 (síntesis): Cap 6 Accionables (cruza Cap 2+3+4+5)
  ↓ barrera: N2 completo antes de N3
N3 (meta): Resumen Ejecutivo + Párrafos Introductorios + Referencias APA
  ↓
Ensamblado .docx con plantilla membrete
```

**Estado actual de implementación:** N0 + N1 parcial (Caps 1, GICS, 2, 3, 4) implementados.
N2, N3 y el orquestador DAG están pendientes.

---

## RN-006 — Historial completo en BD: trazabilidad total del informe

**Regla:** Cada informe generado persiste en la BD: inputs del usuario, fuentes consultadas
(chunks usados), texto generado por cap, documento final, costos LLM, tiempos de ejecución.

**Implementación:** `data/repositories/informe_repo.py` → `InformeRepository`
**Tabla:** `informes_ic.historial_informes` con JSON de chunks y costs.

**Razón:** Auditoría, reproducibilidad y mejora del sistema. Un analista debe poder reconstruir
exactamente por qué el sistema generó un texto determinado.

---

## RN-007 — Idioma: español latino neutro en toda la salida

**Regla:** Todo el contenido generado debe estar en español latino neutro. Si el LLM genera texto
en otro idioma (CJK principalmente en `qwen3:8b`), se activa la política de ausencia.

**Implementación:** `shared/text_utils.py` → `has_cjk_characters()` (umbral ≥5 chars CJK)

**Alcance:** Solo se aplica post-generación en Cap 1 actualmente. En fase futura se aplicará a
todos los caps como capa de validación.

---

## RN-008 — Presupuesto máximo por informe: $1.00 USD

**Regla:** El `CostTracker` en el LLM gateway lleva la cuenta acumulada de tokens y costo en USD
por sesión. Si se supera `LLM_BUDGET_LIMIT_USD`, el circuit breaker activa el nivel `paid`
como último recurso y emite alerta.

**Implementación:** `infrastructure/llm/gateway.py` → `CostTracker`

**Nota:** Los modelos `free` tienen costo $0. El presupuesto aplica principalmente al tier `paid`
(< $0.20/MTok). Un informe completo con 6 caps debería costar entre $0 y $0.30.
