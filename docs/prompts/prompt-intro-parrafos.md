# Prompt-intro (chain_intro): Párrafos Introductorios de Capítulos

> **Chain operativa:** `src/ic/domain/chains/chain_intro.py` (`build_chain_intro`).
> **Fuente original:** `source_prompts/10. Prompt - Párrafos Introductorios.docx`.
> **Rol:** Redactor de informes ejecutivos.
> **Entrada:** `{titulo}`, `{empresa}`, `{resumen_cap}`.
> **Salida:** Párrafo de 2–3 oraciones que contextualiza el capítulo.
> **Uso:** párrafos intro de Caps 2–6 (Fase 5F). Genérico, reutilizable por capítulo.

---

## Prompts (transcritos de la chain)

```
SYSTEM: Eres un redactor de informes ejecutivos. Escribe SOLO en español latino neutro.

USER:  Escribe un párrafo introductorio de 2 a 3 oraciones para el capítulo '{titulo}' del
       informe de inteligencia competitiva de {empresa}. El capítulo desarrolla el siguiente
       contenido:

       {resumen_cap}

       La introducción debe contextualizar el propósito del capítulo para un lector ejecutivo.
       Sin títulos, sin viñetas, sin meta-comentarios.
```

## Divergencias vs el `source_prompt` original (Fase 20)

Algunos capítulos (Cap 3, 4, 5) llevan además un **párrafo introductorio fijo** transcrito
literalmente dentro de su propia chain (ej. `chain_04`/`chain_05`/`chain_06`). `chain_intro`
cubre los capítulos que no tienen intro fija. Divergencia menor, coherente con el diseño N1/N2.
