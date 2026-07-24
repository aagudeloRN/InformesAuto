# Prompt-05 (chain_05): Capítulo 4 — Panorama del Ecosistema

> **Chain operativa:** `src/ic/domain/chains/chain_05_ecosistema.py` (`build_chain_05`).
> **Fuente original:** `source_prompts/7. Prompt - Capítulo 4 - Panorama Ecosistema.docx`.
> **Rol:** Analista senior en movimientos corporativos y dinámica de ecosistemas.
> **Entrada:** `{descripcion_empresa}`, `{sector_gics}`, `{retrieval_sector}`, `{fuentes_web}`.
> **Salida:** Markdown con párrafo intro fijo + 4.1 + 4.2 + 4.3 + 4.4 + 4.5.
> **N1** en el DAG (paralelizable con Cap 2/3).

---

## ✅ Divergencia MAYOR vs el patrón Noel — CERRADA en Fase 21 (T21.8, DT-046)

Hasta Fase 20 la chain mapeaba **actores** del ecosistema (Local/Global/Disruptores) en lugar de
analizar los **movimientos** que pide el patrón. En Fase 21 se reescribió al patrón Noel:

| | Patrón Noel / `source_prompt 7` | Chain operativa (F21) |
|---|---|---|
| 4.1 | **Inversiones** | ✅ Inversiones |
| 4.2 | **Integraciones verticales** | ✅ Integraciones Verticales |
| 4.3 | **Fusiones y adquisiciones (M&A)** | ✅ Fusiones y Adquisiciones (M&A) |
| 4.4 | **Joint ventures** | ✅ Joint Ventures |
| 4.5 | **Alianzas de compra y abastecimiento** | ✅ Alianzas de Compra y Abastecimiento |
| Unidad de análisis | **Evento** (3 por subcap): Título + ejecución + *capacidad estratégica adquirida* + *vulnerabilidad mitigada* | ✅ mismo formato de evento |
| Foco geográfico | Colombia / América Latina cuando la evidencia lo permita | ✅ |

El rol se des-sesga por `{sector_gics}` (coherente con T21.5) y RN-001 se preserva: si no hay 3
eventos con evidencia, se emiten los que existan y el resto reporta "Dato no disponible en
fuentes consultadas".

---

## Estructura del capítulo (user prompt vigente)

- **Párrafo introductorio fijo** (enfoque de movimientos corporativos).
- **4.1 Inversiones** — 3 eventos (formato Título + ejecución + capacidad + vulnerabilidad).
- **4.2 Integraciones Verticales** — 3 eventos.
- **4.3 Fusiones y Adquisiciones (M&A)** — 3 eventos.
- **4.4 Joint Ventures** — 3 eventos.
- **4.5 Alianzas de Compra y Abastecimiento** — 3 eventos.

> Nota: la chain emite `## 4.1–4.5`. `renumber_subheadings()` (DT-032) corrige cualquier prefijo
> mal numerado en el ensamblado.
