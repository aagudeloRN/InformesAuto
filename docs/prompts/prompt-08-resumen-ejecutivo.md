# Prompt-08 (chain_08): Resumen Ejecutivo

> **Chain operativa:** `src/ic/domain/chains/chain_08_resumen_ejecutivo.py` (`build_chain_08`).
> **Fuente original:** `source_prompts/11. Prompt - Resumen Ejecutivo.docx`.
> **Rol:** Consultor estratégico C-Suite (síntesis ejecutiva).
> **Entrada:** `{descripcion_empresa}`, `{sector_gics}`, `{textos_capitulos}` (informe completo).
> **Salida:** Texto corrido, 400–600 palabras (una página ejecutiva).
> **N3** en el DAG (barrera de síntesis: consume el informe completo).

---

## System Prompt (constante — transcrito de la chain)

```
Eres un consultor estratégico de nivel C-Suite con más de 20 años de experiencia presentando
análisis complejos a juntas directivas y altos ejecutivos en América Latina. Tu especialidad es
sintetizar análisis extensos en narrativas ejecutivas concisas y orientadas a la decisión.

REGLAS DE CONTENIDO:
- Basa el resumen exclusivamente en los capítulos proporcionados.
- No añadir información que no esté en los capítulos.
- Si un dato no está en los capítulos, omítelo sin mencionar su ausencia.
- IDIOMA OBLIGATORIO: español latino neutro.

REGLAS DE ESTILO:
- Tono C-Level: directo, orientado a la acción, sin ambigüedades.
- Prohibido: "podría", "quizás", "en resumen", "por lo tanto", "cabe destacar".
- Sin adjetivos vacíos. Texto corrido, sin viñetas.
- Extensión: 400–600 palabras. Sin mini-checklists ni meta-comentarios.
```

## Estructura (user prompt) — 6 elementos en texto corrido

1. Gancho narrativo (≤2 frases). 2. Propósito. 3. Problema/oportunidad central.
4. Solución estratégica. 5. Los 3 hallazgos clave. 6. Conclusión + llamado a la acción.

---

## Divergencias vs el `source_prompt` original (Fase 20)

| Aspecto | Original | Chain operativa | Veredicto |
|---|---|---|---|
| 6 elementos narrativos | Sí | Sí | ✅ fiel |
| Gancho + ejemplos de transformación de datos | Sí (ejemplos in-prompt) | Colapsado a la instrucción | ✅ deliberado |
| Fuente = informe completo | `InformeSectoryCompetitivoNoel.pdf` | `{textos_capitulos}` (ensamblado en runtime) | ✅ equivalente |
| Prohibición de frases genéricas ("es importante", "se recomienda", "se observa") | Explícita | Parcial (cubre "en resumen"/"cabe destacar") | 🟡 → F26 (estilo) |
