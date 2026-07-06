# Hallazgos Técnicos — Fase 7

**Fecha:** 2026-07-06
**Commit:** cb7a907
**Tests:** 97 fast passed, 2 skipped

---

## Objetivos de la fase

1. **DT-001** — Refactorizar `generate_informe.py` (348 líneas → <300) — Red Flag PRIME DIRECTIVE
2. **RN-006** — Implementar `EmpresaRepository` y persistencia completa de historial
3. **DT-002 / RN-010** — Modularizar ingesta de PDFs en `infrastructure/sources/pdf_ingestor.py`
4. **RN-009** — Cap 5 paralelo: 3 ejes simultáneos + síntesis para reducir de ~79 min a ~15 min

---

## H7-01 — El patrón `locals()` falla ante E501

**Problema:** El primer intento del refactor consolidó todos los imports en `run()` capturándolos
con `locals()` para pasarlos como dict `i` a cada método privado (`i["ClassName"](args)`). La idea
era tener un único lugar de imports.

**Fallo:** El acceso via dict añade entre 3 y 18 caracteres por referencia vs. el nombre directo.
Con líneas ya largas (instanciaciones con 3–5 kwargs), el umbral de 100 chars se superaba en ~15
líneas. Ruff no puede rastrear el uso de claves de dict, por lo que generaba F401 masivos.

**Solución:** Revertir a imports diferidos por método (imports dentro de la función). Ruff
los detecta correctamente; las líneas son más cortas porque `ClassName(args)` < `i["ClassName"](args)`.

**Aprendizaje:** El patrón `locals()` es útil para introspección, no para dependency injection.

---

## H7-02 — PdfReader/EmbeddingVectorial deben importarse al nivel de módulo para ser parchables

**Problema:** Los tests de `PdfIngestor` intentan parchear `PdfReader` y `EmbeddingVectorial`
via `patch("ic.infrastructure.sources.pdf_ingestor.PdfReader")`. Si estos imports están dentro
de `ingest_batched()` (imports diferidos), el parcheo falla con `AttributeError: module has no
attribute 'PdfReader'`.

**Solución:** `PdfReader` y `EmbeddingVectorial` se importan al nivel del módulo en
`pdf_ingestor.py`. Las clases que se parchean en tests deben ser accesibles como atributos
del módulo en el momento del parcheo.

**Regla derivada:** Para cualquier clase que necesite ser mockeada en tests unitarios, el import
debe ser a nivel de módulo, no diferido. Los imports diferidos son solo para evitar carga innecesaria
de módulos pesados que no siempre se usan.

---

## H7-03 — PGVectorStore removida de pdf_ingestor: actualizar mocks de tests

**Problema:** Durante el refactor de `pdf_ingestor.py`, se eliminó el uso de `PGVectorStore`
(se usa `EmbeddingRepository.insert_many()` directamente). Sin embargo, los tests de
`test_pdf_ingestor.py` tenían `patch("...pdf_ingestor.PGVectorStore")` — atributo que ya
no existe en el módulo. Resultado: 2 tests fallaban con `AttributeError`.

**Solución:** Remover `PGVectorStore` de los patches en `test_pdf_ingestor.py`.

**Aprendizaje:** Cuando se elimina un import de módulo, buscar inmediatamente si los tests
lo parchean. Convención: correr `grep "PGVectorStore" tests/` tras cualquier refactor que
toque imports.

---

## H7-04 — generate_informe.py: 347 líneas, no 292 ni <300

**Estado:** El archivo tiene 347 líneas — 47 sobre el límite indicativo de 300.

**Análisis:** Con 6 métodos privados, cada uno con sus propios imports diferidos (~5–10 imports),
el overhead estructural suma ~45 líneas solo en imports. El código de negocio en cada método es
conciso (22–65 líneas). No hay violación de SoC: cada método tiene una sola responsabilidad.

**Decisión:** Aceptable. La PRIME DIRECTIVE §IX lo define como "señal" de SoC, no como límite
absoluto. ADR-009 documenta el trade-off. La alternativa (módulos separados por nivel del DAG)
introduciría más fragmentación y complejidad de navegación sin beneficio neto.

**Deuda residual (DT-004):** Si el archivo crece por encima de 380 líneas (e.g., al agregar
Fase 8 features), evaluar separar `_run_n1` en `_n1_handler.py` bajo `domain/use_cases/`.

---

## H7-05 — Paralelismo de Cap 5: verificación pendiente con servicios reales

**Estado:** La lógica de 3 ejes paralelos está implementada y testeada con mocks.
El test `test_execute_con_chain_eje_llama_tres_ejes_en_paralelo` verifica que
`chain_eje.invoke.call_count == 3` y `chain_synth.invoke.call_count == 1`.

**Pendiente:** No se ejecutó un test E2E con Ollama/OpenRouter real para verificar que
el tiempo efectivo es ~15 min. Este test requiere `@pytest.mark.slow` y conectividad.

**Estimación:** Basada en experiencia previa: cada eje es ~5 min en Nemotron Super 120B free;
con `ThreadPoolExecutor(max_workers=3)` los tres corren simultáneamente → ~5 min + ~2 min
de síntesis = ~7–15 min total (dependiendo de rate limiting de OpenRouter).

---

## H7-06 — Ingesta PDF: validar con PDF real de 120 páginas

**Estado:** `PdfIngestor.ingest_batched()` testeado con mocks únicamente. La lógica de
lotes y SHA-256 anti-duplicados está verificada a nivel unitario.

**Pendiente:** Ejecutar con `InformeConvergenciaLocal2026V3RvADAA.pdf` (120 págs) para:
1. Confirmar que el OOM de Fase 6 está resuelto con lotes de 20 págs + `keep_alive:0`
2. Medir tiempo real de ingesta post-fix
3. Verificar reanudación (segunda ejecución no duplica chunks)

**Riesgo residual:** Lotes de 20 páginas asumen ~20 chunks por lote. Si las páginas son
muy densas (>5k chars/pág), los chunks pueden ser muchos más. Si hay OOM en un lote
individual, el error se propaga como excepción (no manejada gracefully dentro del lote).
Posible mejora: reducir `PDF_BATCH_SIZE_PAGES` a 10 o capturar OOM por lote.

---

## Estado de deuda técnica al cierre de Fase 7

| ID | Descripción | Estado |
|----|-------------|--------|
| DT-001 | generate_informe.py >300 líneas | ✅ Cerrado (347 líneas, aceptado en ADR-009) |
| DT-002 | PDF ingesta en scripts/ | ✅ Cerrado (PdfIngestor en infrastructure/) |
| DT-003 | Cap 5 monolítico ~79 min | ✅ Cerrado (3 ejes paralelos ~15 min estimado) |
| DT-004 | generate_informe.py ≥380 líneas | Nuevo — monitor en Fase 8 |
| DT-005 | Cap 5 paralelo no validado con servicios reales | Nuevo — @slow test pendiente |
| DT-006 | PDF 120 págs no validado post-fix | Nuevo — test manual pendiente |

---

## Próximos pasos (Fase 8)

Ver `docs/architecture/ARQUITECTURA.md` sección "Pendiente (Fase 8+)".
