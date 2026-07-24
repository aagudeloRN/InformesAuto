# Prompt-07 (chain_07): Capítulo 6 — Accionables Estratégicos

> **Chain operativa:** `src/ic/domain/chains/chain_07_accionables.py` (`build_chain_07`).
> **Fuente original:** `source_prompts/9. Prompt - Capítulo 6 - Accionables.docx`.
> **Rol:** Consultor estratégico senior en planificación empresarial y transformación organizacional.
> **Entrada:** `{descripcion_empresa}`, `{sector_gics}`, `{retrieval_cruzado}` (benchmarking +
> tendencias + ecosistema + convergencia territorial).
> **Salida:** 6 accionables (título en negrilla + descripción ≥150 palabras + justificación).
> **N2** en el DAG (barrera: consume outputs de N1/N2).

---

## System Prompt (constante — transcrito de la chain)

```
Eres un consultor estratégico senior con amplia experiencia en planificación empresarial
y transformación organizacional en América Latina. Tu especialidad es traducir análisis
sectoriales complejos en acciones concretas y ejecutables.

REGLAS DE CONTENIDO:
- Cada accionable sustentado en evidencia de las fuentes proporcionadas.
- Sin evidencia: "Dato no disponible en fuentes consultadas."
- No inventar datos, cifras ni tendencias.
- IDIOMA OBLIGATORIO: español latino neutro.

REGLAS DE ESTILO:
- Tono ejecutivo y directo. Prohibido: "podría", "quizás", "en resumen", "por lo tanto",
  "cabe destacar".
- Sin adjetivos vacíos salvo evidencia cuantificable.
- Storytelling: texto corrido, sin viñetas. Sin mini-checklists ni citaciones inline.
```

## Estructura (user prompt)

- Exactamente **6 accionables** que crucen hallazgos de capítulos anteriores.
- Cada uno: **título en negrilla** (verbo en infinitivo) + descripción ≥150 palabras (storytelling)
  + justificación de prioridad basada en hallazgos.
- 6 dimensiones distintas: competitividad, transformación digital, sostenibilidad, talento,
  ecosistema, desarrollo de mercado.

---

## Divergencias vs el `source_prompt` original (Fase 20)

| Aspecto | Original | Chain operativa | Veredicto |
|---|---|---|---|
| 6 accionables cruzando 4 capítulos | Sí (Benchmarking/Tendencias/Ecosistema/Convergencia) | Sí (`{retrieval_cruzado}`) | ✅ fiel |
| Formato Título/Descripción/Justificación | Sí (+ ejemplo "Accionable 1: …") | Sí, sin el prefijo "Accionable N:" | ✅ fiel (prefijo quitado, como el paso de mejora del original) |
| 6 dimensiones explícitas | No fijadas | Añadidas (evita repetición) | ✅ mejora |
| **Coherencia real con caps previos** | Consume las 4 fuentes completas | Recibe **retrieval**, no los textos completos de Cap 2/3/4/5 | 🟠 → F22 (Q1/T22.1: pasar contexto de caps previos) |
