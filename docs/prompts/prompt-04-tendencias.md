# Prompt-04 (chain_04): Capítulo 3 — Análisis Sectorial Tendencial

> **Chain operativa:** `src/ic/domain/chains/chain_04_tendencias.py` (`build_chain_04`).
> **Fuente original:** `source_prompts/6. Prompt - Capítulo 3 - Análisis tendencial.docx`.
> **Rol:** Analista estratégico senior en inteligencia de mercado y análisis sectorial.
> **Entrada:** `{descripcion_empresa}`, `{sector_gics}`, `{retrieval_sector}`, `{fuentes_academicas}` (OpenAlex).
> **Salida:** Markdown con párrafo intro fijo + 3.1 (6 tendencias) + 3.2 (4 MECE) + 3.3 (casos).
> **Tier LLM:** `synth`. **N1** en el DAG (paralelizable con Cap 2/4).

---

## System Prompt (constante — transcrito de la chain)

```
Eres un analista estratégico senior especializado en inteligencia de mercado y análisis
sectorial, con más de 10 años asesorando grandes corporaciones del sector {sector_gics} en
América Latina.

REGLAS DE CONTENIDO:
- Sustenta cada afirmación clave con datos de las fuentes proporcionadas.
- Indica el nivel de confianza (Alto/Medio/Bajo) de las afirmaciones clave y justifícalo.
- Si un dato no está disponible, escribe exactamente: "Dato no disponible en fuentes consultadas."
- No inventar información bajo ninguna circunstancia.
- No menciones escasez de fuentes; solo reporta el estado del dato.
- IDIOMA OBLIGATORIO: español latino neutro. Prohibido chino/inglés u otro idioma.

REGLAS DE ESTILO:
- Tono ejecutivo y directo. Prohibido: "podría", "quizás", "en resumen", "por lo tanto",
  "cabe destacar", "es importante mencionar".
- Sin adjetivos vacíos salvo evidencia cuantificable.
- Texto corrido (storytelling), sin viñetas ni listas.
- Varía el ritmo: frases cortas (≤12 palabras) con frases más largas.
- Sin mini-checklists ni meta-comentarios. Sin citaciones inline en secciones narrativas.
```

## Estructura del capítulo (user prompt)

- **Párrafo introductorio fijo** (transcrito literalmente).
- **3.1 Tendencias Tecnológicas, Económicas y Sociales:** 6 tendencias (2 T, 2 E, 2 S) en
  orden T1,T2,E1,E2,S1,S2; título en negrilla + 2 párrafos respirables.
- **3.2 MECE:** exactamente 4 tendencias asignadas (Crecimiento / Optimización / Innovación /
  Mitigación de riesgos); datos post-2026 + horizonte temporal + implicaciones imperativas.
- **3.3 Casos de éxito:** globales (1 por MECE, ≥150 palabras) + locales (1 por tendencia
  tecnológica, ≥150 palabras). Los casos locales llevan **restricción sectorial** (F21, T21.2):
  deben pertenecer al sector `{sector_gics}`; si no hay, "Dato no disponible en fuentes
  consultadas." — no se usan casos de otros sectores aunque sean de Medellín/Colombia.

---

## Divergencias vs el `source_prompt` original (Fase 20)

| Aspecto | Original (NotebookLM) | Chain operativa | Veredicto |
|---|---|---|---|
| Estructura 3.1/3.2/3.3 | Idéntica | Idéntica | ✅ fiel |
| Refinamientos "editor humano" + mini-checklist + partir párrafos | Presentes (iterativo) | Colapsados al system prompt (una sola llamada) | ✅ deliberado |
| "quita prefijos Tecnológica 1/2…" | Paso posterior | Se pide directamente el título en negrilla | ✅ deliberado |
| **Sesgo sectorial** | "corporaciones agroindustriales" (era Noel) | **Des-sesgado** por `{sector_gics}` (F21, T21.5) | ✅ resuelto |
| Casos locales del mismo sector | "reflejar la realidad, no tendencias globales" | **Constraint sectorial** añadido (F21, T21.2) | ✅ resuelto |
| Fuentes académicas (OpenAlex) | No existía | Añadido (`{fuentes_academicas}`) | ✅ mejora |

> **Actualizado en Fase 21:** el sesgo sectorial (DT-043) y el constraint de casos locales
> (DT-036) quedaron resueltos. `generate_tendencias` añade además una query web dedicada a
> casos locales del sector.
