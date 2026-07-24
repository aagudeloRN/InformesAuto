# Prompt-03b (chain_03b): Sección 2.3 — Mercado

> **Chain operativa:** `src/ic/domain/chains/chain_03b_mercado.py` (`build_chain_03b`).
> **Fuente original:** `source_prompts/4. Prompt - Mercado ...docx` + `5. Prompt - Mercado Gestiones Anexas.docx`.
> **Rol:** Analista senior de inteligencia de mercado.
> **Entrada:** `{descripcion_empresa}`, `{sector_gics}`, `{retrieval_mercado}`.
> **Salida:** Markdown de la sección `## 2.3. Mercado` (narrativa + tabla de mercado por región).
> **N1** en el DAG (paralelizable con Cap 2/3/4). Use case: `GenerateMercado`.

---

## Origen (Fase 21 — cierra brecha 🔴 DT-044)

Hasta Fase 20 el patrón Noel tenía una sección **2.3 Mercado** (tamaño de mercado, segmentos y
una tabla de mercado por región — T10 del patrón) que el sistema **no implementaba**. F21 (T21.6)
la implementa como chain propia y la **intercala en el ensamblado entre 2.2 y 2.4** dentro del
Capítulo 2 (`assembler._insert_before_subheading`, ancla `prefix="2.4"`).

## Estructura de la sección (user prompt)

1. **Tamaño y crecimiento del mercado** — valor total, TAM/SAM si consta, tasa de crecimiento,
   con año de referencia. Texto corrido.
2. **Segmentos de mercado** — segmentos principales y su peso relativo. Texto corrido.
3. **Drivers y barreras** — factores que impulsan o frenan el mercado. Texto corrido.
4. **Tabla de mercado por región** — tabla markdown `| Región | Tamaño de mercado | Crecimiento (%) | Año |`.

## Reglas clave

- **RN-001 (datos ausentes):** sin datos suficientes en retrieval → el use case devuelve
  "Dato no disponible en fuentes consultadas." y el assembler **omite** la sección. A nivel de
  celda, si falta un dato, se escribe la misma frase. Nunca se rellena con conocimiento del modelo.
- **Des-sesgado:** el rol se parametriza por `{sector_gics}` (coherente con T21.5). Sin nombres
  de modelo (ADR-002): el LLM lo inyecta el gateway.
- **Retrieval sectorial:** `GenerateMercado` lanza queries de mercado con `search_depth="advanced"`
  y recupera del índice filtrando por `sector_gics_code` + `empresa_id` (ADR-012/013).

## Divergencia deliberada vs source_prompt

Los `source_prompts 4` originales ofrecían variantes (Mercado1/2/3/Único) con un flujo iterativo
multi-llamada. La chain **colapsa** ese flujo en una sola llamada que ya pide el resultado final
(narrativa + tabla), igual que el resto de chains (ver nota en `FASE20_HALLAZGOS.md §4`).
