# ADR-015 — Arquitectura HITL Post-Generación

**Fecha:** 2026-07-23
**Estado:** Aprobado
**Fase:** 21–22

---

## Contexto

Tras el análisis comparativo de los informes de Alpina (corrida de la mañana vs corrida Fase 18)
se identificó que el pipeline "one-shot" tiene dos limitaciones estructurales:

1. **Brechas de contenido rastreables pero no reparables**: el sistema distingue correctamente
   entre "dato disponible" y "dato no disponible"; pero el analista no tiene un mecanismo para
   cerrar esas brechas sin relanzar el pipeline completo manualmente.
2. **Inconsistencias cross-cap**: con el DAG de capítulos, los caps N1 se generan en paralelo
   sin conocerse entre sí; pueden producir afirmaciones que, en retrospectiva, no son coherentes
   con otras caps.

La fuente de prompts `source_prompts/13. Prompt (Opcional) - Evaluar Informe.docx` ya define un
proceso de auditoría LLM que identifica brechas por prioridad y tipo. Esta ADR formaliza cómo
integrar ese proceso al sistema como una capa HITL (Human-in-the-Loop) post-generación.

---

## Decisión

### 1. Punto de intervención: post-generación

El HITL ocurre **después** de que el pipeline ha producido un informe completo. El usuario ve el
documento final primero; luego puede optar por auditarlo.

**Motivación:** Iniciar el HITL mid-pipeline (entre tiers N1 y N2) obliga al usuario a estar
presente durante ~15–20 minutos de generación, rompe la experiencia de "lanzar y esperar" y
complica la reproducibilidad. El HITL mid-pipeline es una opción futura (Fase 23+), no la primera
capa. La post-generación tiene toda la información disponible para diagnosticar.

**Consecuencia:** Los gaps identificados pueden referirse a caps ya generados. La corrección se
aplica vía regeneración completa, no via patch selectivo (ver decisión 2).

### 2. Regeneración: full pipeline con complement-not-replace

Cuando el usuario sube un nuevo documento para cerrar un gap, el sistema:
1. Verifica que el documento no esté ya indexado (deduplicación a nivel de documento, SHA-256
   del contenido completo).
2. Si es nuevo: ingesta al índice RAG vía `PdfIngestor` (beneficia a todos los caps, no solo
   al cap donde se detectó el gap).
3. Relanza el pipeline **completo** (no selectivo por cap). Motivación: un nuevo doc de
   benchmarking puede mejorar también el Cap 5 (Convergencia) o el Cap 6 (Accionables); la
   regeneración selectiva requiere modelar estas dependencias explícitamente y añade complejidad
   mantenida para siempre.
4. La regeneración recibe el texto del informe anterior como `complement_context`. Este se inyecta
   en los prompts N1/N2/N3 con la instrucción: "El análisis previo concluyó lo siguiente. Usa los
   nuevos insumos para complementar estas conclusiones, no para contradecirlas salvo que haya
   evidencia explícita en las nuevas fuentes."

**Deduplicación doc-level:** Distinta a la deduplicación chunk-level existente (SHA-256 de texto
de cada chunk). La nueva verificación es a nivel de documento: antes de ingestar, calcular
SHA-256 del contenido completo del PDF y comparar con los hashes registrados en
`documentos_locales`. Si ya existe, notificar al usuario y no duplicar.

### 3. Terminación del loop: control del usuario

El loop HITL no tiene criterio de parada automático basado en calidad. El analista decide cuándo
el informe está suficientemente bueno pulsando "Aprobar informe" (campo `aprobado=True` en
`historial_informes`). El sistema puede proponer "sin gaps de alta prioridad" como sugerencia,
pero la aprobación siempre requiere acción humana explícita.

**Futuro (Fase 23+):** sistema de notificación cuando haya cambios pendientes de aprobación
(email o Slack webhook). No se implementa en Fase 21.

### 4. UI: tab Historial con panel por informe

El módulo HITL se integra en el tab "Historial" de la UI Streamlit existente. Por cada informe
en el historial:
- Botón "Auditar" → invoca `generate_evaluacion.py` → muestra panel lateral con gaps priorizados
  (Alta/Media/Baja), tipo de dato faltante y fuentes recomendadas.
- Uploader de documentos adicionales (puede subir varios a la vez).
- Botón "Regenerar con nuevos insumos" → verifica duplicados → ingesta → lanza pipeline completo.
- Botón "Aprobar informe" → marca `aprobado=True` en BD → muestra badge "Aprobado" en historial.

**Motivación:** Integrar en Historial (no como sección separada) mantiene el contexto del
informe visible. El analista no tiene que navegar entre pantallas. La UI "tonta" solo renderiza
el estado que devuelven los use cases (SoC invariante).

---

## Módulos implementados en dos fases

### Módulo 1: Gap Auditor (Fase 21)

Adapta `source_prompts/13. Prompt (Opcional) - Evaluar Informe.docx` a:

- `domain/chains/chain_evaluar.py` — cadena LCEL que recibe el texto completo del informe y
  devuelve un listado de `Gap(prioridad, tipo, descripcion, fuente_recomendada)`.
- `domain/use_cases/generate_evaluacion.py` — orquesta la cadena, persiste resultado en
  `informes_ic.evaluaciones_informe`.
- Deduplicación doc-level SHA-256 en `infrastructure/sources/pdf_ingestor.py`.
- `domain/use_cases/generate_informe.py`: acepta `complement_context: str | None`.
- UI: panel Auditar en `presentation/app.py`.

### Módulo 2: Consistency Checker (Fase 22)

- `domain/chains/chain_consistencia.py` — compara caps por pares, devuelve lista de
  `Inconsistencia(tipo, cap_a, cap_b, texto_a, texto_b)`.
- `domain/use_cases/generate_consistencia.py`.
- Resolución auto para inconsistencias factuales (Tavily `basic` para verificar dato correcto).
- Resolución manual para inconsistencias estratégicas (UI muestra las dos versiones).

---

## Consecuencias

**Positivas:**
- El analista puede mejorar iterativamente el informe sin perder el trabajo previo.
- Los nuevos documentos enriquecen el índice RAG para todos los informes futuros del mismo sector.
- El template de auditoría existente (`source_prompts/13`) tiene una implementación fiel.
- La política "no alucinar" se mantiene: el complement-context no autoriza al LLM a inventar;
  solo orienta qué conclusiones previas seguir respetando.

**Riesgos:**
- La regeneración full pipeline (~15–20 min) puede ser lenta si el gap es puntual. El costo
  es aceptable hasta que el corpus sea suficientemente rico para reducir los gaps.
- El complement-context puede sesgar al LLM a no incorporar evidencia contradictoria válida en
  los nuevos documentos. Mitigación: la instrucción dice "salvo que haya evidencia explícita".

**Invariantes que no cambia esta ADR:**
- La política de no-alucinación (RN-001): si el nuevo doc tampoco tiene el dato, se emite párrafo
  de ausencia.
- La citación APA (RN-002): el nuevo doc se cita igual que cualquier otra fuente.
- La regeneración es un pipeline `GenerateInforme.execute()` idéntico al original; no hay código
  especial de "regeneración" — solo se pasa `complement_context`.

---

## Alternativas descartadas

- **HITL mid-pipeline (entre N0 y N1):** Demasiado invasivo en la experiencia UX (usuario debe
  esperar ~5 min de N0 y luego decidir en tiempo real). Reservado para Fase 23+.
- **Regeneración selectiva por cap:** Requiere mapear qué caps dependen del nuevo documento,
  mantener ese mapa actualizado, y garantizar consistencia entre caps regenerados y caps previos.
  El costo de mantenimiento supera el beneficio a escala actual.
- **Aprobación automática basada en umbral de gaps:** Introduce un KPI de calidad que aún no
  está validado con datos reales. El control del usuario es más seguro como primera versión.
