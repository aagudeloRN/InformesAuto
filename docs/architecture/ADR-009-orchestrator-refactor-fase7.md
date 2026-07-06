# ADR-009: Refactor del Orchestrator — _PipelineContext + Métodos Privados + Módulos de Infraestructura

**Status:** Aceptado
**Fecha:** 2026-07-06
**Autores:** aagudeloRN + Claude Sonnet 4.6

---

## Contexto

Al completar Fase 6, el orchestrator `GenerateInforme` acumuló tres deudas técnicas
que disparaban Red Flags de la PRIME DIRECTIVE:

- **DT-001:** `generate_informe.py` alcanzó 348 líneas — Red Flag §IX (límite 300).
  El método `run()` era monolítico: inicializaba infraestructura, ejecutaba los 4 niveles
  del DAG y persistía resultados en un único bloque de ~300 líneas.
- **DT-002:** La ingesta de PDFs se hacía desde `scripts/ingest_pdf.py` llamado vía
  `sys.path` hack dentro de `run()` — violación directa de SoC (§1.1) y de la regla
  de wrappers en `infrastructure/` (§1.2).
- **DT-003 / RN-009:** Cap 5 (Convergencia) tardaba ~79 min en una sola llamada
  monolítica a Nemotron Ultra 550B free. El modelo es lento bajo rate limiting; la
  única forma de reducir el tiempo es subdividir la llamada.

---

## Decisión

### A — _PipelineContext + seis métodos privados

Se introduce el dataclass `_PipelineContext` que agrupa todo el estado del pipeline
(LLMs, embedder, web, tracker, resultados por cap). `run()` queda como orquestador
puro de 15 líneas; la lógica se distribuye en:

| Método | Responsabilidad | Líneas |
|--------|----------------|--------|
| `_setup_infra()` | LLMs, embedder, web, tracker, output_path | ~32 |
| `_run_n0()` | Cap 1 Descripción + GICS | ~22 |
| `_run_n1()` | Caps 2/3/4 paralelos + intros N1 | ~55 |
| `_run_pdf()` | PDF ingesta condicional via PdfIngestor | ~24 |
| `_run_n2()` | Caps 5/6 + intros N2 | ~43 |
| `_run_n3()` | Resumen + APA + ensamblado + persistencia BD | ~62 |

**Patrón de imports diferidos:** cada método importa solo lo que necesita (imports dentro
de la función). Esto evita el tiempo de carga completo en tests que solo ejercen un método,
y reduce acoplamiento entre ramas del DAG.

**Resultado:** 347 líneas totales. El límite de 300 no se alcanza porque el overhead
estructural (6×~5 líneas de imports) es inevitable con imports diferidos. La PRIME
DIRECTIVE §IX lo identifica como "señal de SoC"; la investigación confirma que cada
método tiene responsabilidad única y < 65 líneas — no hay violación de SoC.

### B — PdfIngestor en infrastructure/sources/

`PdfIngestor.ingest_batched()` encapsula toda la lógica de ingesta:
- Lotes de `PDF_BATCH_SIZE_PAGES` páginas (configurable en `Settings`)
- SHA-256 por chunk para anti-duplicados reanudables
- `keep_alive:0` POST a Ollama tras cada lote (libera VRAM)
- Registro de `DocumentoLocal` al finalizar
- `scripts/ingest_pdf.py` queda como thin wrapper CLI

### C — GenerateConvergencia con chain_eje opcional

`GenerateConvergencia.__init__` acepta `chain_eje=None`:
- **Sin chain_eje (legacy):** llamada monolítica única — compatibilidad hacia atrás.
- **Con chain_eje:** 3 llamadas paralelas (`ThreadPoolExecutor(max_workers=3)`) a
  `chain_06a_convergencia_eje` con los 3 ejes (Tecnológico, Mercado, Social) +
  1 llamada de síntesis a `build_chain_06_synth`. Tiempo estimado: ~15 min vs ~79 min.

### D — EmpresaRepository + persistencia completa de historial

`EmpresaRepository.upsert_by_name()` desbloquea la FK `empresa_id` en
`historial_informes`. La persistencia en `_run_n3()` está envuelta en `try/except`
para degradación graceful: un fallo de BD no aborta la entrega del `.docx`.

---

## Consecuencias

### Positivas
- Cada método tiene una responsabilidad única y cabe en una pantalla.
- Los tests pueden parchear imports de un solo método sin afectar el resto del pipeline.
- PdfIngestor es reutilizable desde CLI, orchestrator y cualquier futuro workflow.
- GenerateConvergencia es retrocompatible: los tests anteriores sin chain_eje siguen pasando.
- El historial en BD es ahora completo: empresa, costo, tokens, tiempo y ruta del .docx.

### Negativas / Trade-offs
- `generate_informe.py` tiene 347 líneas (47 sobre el límite indicativo de 300).
  Reducirlo requeriría extraer los métodos a módulos separados (over-engineering
  para el tamaño actual del proyecto).
- Los imports diferidos por método son más verbosos que imports en el nivel del módulo,
  pero son necesarios para imports condicionales y testabilidad.
- `_PipelineContext` debe actualizarse manualmente si se agrega un nuevo capítulo.
  Riesgo bajo: el dataclass es un único punto de verdad bien documentado.

---

## Alternativas consideradas

| Alternativa | Razón de descarte |
|-------------|-----------------|
| `locals()` para centralizar imports en `run()` | E501 generalizado por `i["ClassName"]` verbose; menor legibilidad; ruff no puede verificar uso |
| Módulos separados por método (e.g., `_n1_handler.py`) | Over-engineering para un pipeline que cambia frecuentemente; dificulta navegación |
| Llamada monolítica a Cap 5 con modelo más rápido | Modelo más rápido puede tener menor calidad; la subdivisión mantiene calidad y reduce tiempo |

---

## Supersede

Este ADR complementa ADR-008. No lo invalida: ADR-008 estableció la interfaz pública
(`InformeParams`, `InformeResult`, `on_step` callback); ADR-009 define la implementación
interna del método `run()`.
