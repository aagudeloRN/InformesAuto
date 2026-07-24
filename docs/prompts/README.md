# `docs/prompts/` — Espejo versionado de los prompts operativos

Estos markdown documentan los **prompts que realmente ejecuta el pipeline** (las *chains* LCEL
de `src/ic/domain/chains/`), con la nota de divergencias respecto a los `source_prompts/*.docx`
originales (creados en NotebookLM para el informe patrón Noel).

> **Convención de numeración (fijada en Fase 20):** el número del archivo `prompt-NN` sigue el
> número de la **chain** (`chain_NN_*`), que es la fuente de verdad ejecutable — **no** el número
> del `source_prompt` ni el número del capítulo del informe. Por eso convergencia es `prompt-06`
> (chain_06) aunque es el "Capítulo 5" y era el `source_prompt 8`.

## Mapa completo: source_prompt ↔ chain ↔ docs/prompts ↔ capítulo

| `source_prompts/*.docx` | Chain operativa | `docs/prompts/*.md` | Capítulo informe | Estado |
|---|---|---|---|---|
| 0. Ecuaciones de búsqueda | — (queries de conectores) | *(→ runbook F21, T21.3)* | — (insumo corpus) | ⬜ no es chain |
| 1. Descripción Empresa | `chain_01_descripcion` | `prompt-01-descripcion-empresa.md` | Cap 1 | ✅ |
| 2. Sector GIS (GICS) | `chain_02_gics` | `prompt-02-sector-gics.md` | Cap 1 (clasif.) | ✅ |
| 3. Cap 2 Benchmarking | `chain_03_benchmarking` | `prompt-03-benchmarking.md` | Cap 2 | ✅ |
| 4. Mercado (1/2/3/Único) | — **no implementado** | *(pendiente)* | **Cap 2.3 Mercado** | 🔴 brecha (F21) |
| 5. Mercado Gestiones Anexas | — no implementado | *(pendiente)* | Cap 2.3 (anexo) | 🔴 brecha (F21) |
| 6. Cap 3 Análisis tendencial | `chain_04_tendencias` | `prompt-04-tendencias.md` | Cap 3 | ✅ |
| 7. Cap 4 Panorama Ecosistema | `chain_05_ecosistema` | `prompt-05-ecosistema.md` | Cap 4 | ⚠️ divergencia mayor (F21) |
| 8. Cap 5 Convergencia | `chain_06_convergencia` (+`06a`) | `prompt-06-convergencia.md` | Cap 5 | ✅ (deriva de áreas → F22) |
| 9. Cap 6 Accionables | `chain_07_accionables` | `prompt-07-accionables.md` | Cap 6 | ✅ (coherencia → F22) |
| 10. Párrafos Introductorios | `chain_intro` | `prompt-intro-parrafos.md` | Caps 2–6 | ✅ |
| 11. Resumen Ejecutivo | `chain_08_resumen_ejecutivo` | `prompt-08-resumen-ejecutivo.md` | Resumen (N3) | ✅ |
| 12. Referencias | — (`apa_formatter`, infra) | *(no es prompt LLM)* | Referencias | ✅ vía código |
| 13. Evaluar Informe (opcional) | — HITL, no implementado | *(pendiente)* | — (auditoría) | ⬜ F24/F25 |

**Cobertura:** 8 de 8 chains operativas documentadas (100%). Los `source_prompts` sin chain
(Mercado, Ecuaciones, Referencias, Evaluar) están explicados arriba con su fase destino.

Detalle de brechas y asignación de fases: `docs/decisions/FASE20_HALLAZGOS.md`.
Rúbrica de calidad derivada del patrón: `docs/eval/RUBRICA_CALIDAD.md`.
