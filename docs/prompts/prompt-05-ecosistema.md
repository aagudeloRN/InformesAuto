# Prompt-05 (chain_05): Capítulo 4 — Ecosistema Empresarial

> **Chain operativa:** `src/ic/domain/chains/chain_05_ecosistema.py` (`build_chain_05`).
> **Fuente original:** `source_prompts/7. Prompt - Capítulo 4 - Panorama Ecosistema.docx`.
> **Rol:** Analista senior en mapeo de ecosistemas empresariales y cadenas de valor.
> **Entrada:** `{descripcion_empresa}`, `{sector_gics}`, `{retrieval_sector}`, `{fuentes_web}`.
> **Salida:** Markdown con párrafo intro fijo + 4.1 + 4.2 + 4.3.
> **N1** en el DAG (paralelizable con Cap 2/3).

---

## ⚠️ Divergencia MAYOR vs el patrón Noel (Fase 20 — brecha 🔴)

La cadena **reescribió por completo** la estructura del capítulo respecto al `source_prompt` y al
patrón `InformeSectoryCompetitivoNoel.docx`:

| | Patrón Noel / `source_prompt 7` | Chain operativa actual |
|---|---|---|
| 4.1 | **Inversiones** en startups/empresas locales | Ecosistema Local (Medellín/Colombia) |
| 4.2 | **Integraciones verticales** y acuerdos proveedores | Ecosistema Global |
| 4.3 | **Fusiones y adquisiciones (M&A)** | Actores Disruptores |
| 4.4 | **Joint ventures** | — (no existe) |
| 4.5 | **Alianzas de compra y abastecimiento** | — (no existe) |
| Unidad de análisis | **Evento** (3 por subcap): Título + ejecución + *capacidad estratégica adquirida* + *vulnerabilidad mitigada* | Ficha de actor (nombre/rol/relevancia) |
| Foco geográfico | Local **obligatorio** (Medellín/Antioquia/Colombia) | Local + Global |

**Consecuencia:** el capítulo actual mapea actores del ecosistema (proveedores, gremios,
reguladores, disruptores) en lugar de analizar los **movimientos del ecosistema** (inversiones,
M&A, JV, alianzas) que pide el patrón. Es la mayor divergencia de contenido detectada en Fase 20.

**Decisión:** rediseño agendado en **F21** (nueva tarea T21.5, ver `FASE20_HALLAZGOS.md`).
La chain **no se toca en Fase 20**.

---

## System Prompt (constante — transcrito de la chain)

```
Eres un analista estratégico senior especializado en mapeo de ecosistemas empresariales
y análisis de cadenas de valor, con experiencia en los sectores industriales de América Latina.

REGLAS DE CONTENIDO:
- Sustenta cada afirmación clave con datos de las fuentes proporcionadas.
- Si un dato no está disponible: "Dato no disponible en fuentes consultadas."
- No inventar actores, alianzas ni relaciones bajo ninguna circunstancia.
- No menciones escasez de fuentes; solo reporta el estado del dato.
- IDIOMA OBLIGATORIO: español latino neutro.

REGLAS DE ESTILO:
- Tono ejecutivo y directo. Prohibido: "podría", "quizás", "en resumen", "por lo tanto",
  "cabe destacar", "es importante mencionar".
- Sin adjetivos vacíos salvo evidencia cuantificable.
- Cada actor/categoría: ficha con nombre, rol y relevancia estratégica.
- Sin mini-checklists ni meta-comentarios. Sin citaciones inline.
```

## Estructura del capítulo (user prompt actual)

- **Párrafo introductorio fijo.**
- **4.1 Ecosistema Local (Medellín/Colombia):** fichas de proveedores, clientes, gremios, reguladores.
- **4.2 Ecosistema Global:** partners internacionales, organismos, mercados de exportación.
- **4.3 Actores Disruptores:** ≥4 startups/tecnologías emergentes con horizonte de impacto.

> Nota: la chain emite `## 4.1/4.2/4.3`. `renumber_subheadings()` (DT-032) corrige cualquier
> prefijo mal numerado en el ensamblado. Los outputs de `output/` con `5.x` bajo Cap 4 son
> **previos** a ese fix (verificado en Fase 20).
