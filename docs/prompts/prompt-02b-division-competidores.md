# Prompt: Cap 2.2 — División de Competidores (Grupos Estratégicos)

**Módulo**: `chain_cap2_22_division.py`
**Cadena**: `build_chain_cap2_22_division(llm) -> Runnable`
**Input variables**: `closed_list_str`, `fichas_context`, `empresa_sector`, `feedback`

---

## System Prompt

```text
Eres un analista de inteligencia competitiva experto en estrategia sectorial.
Tu tarea es clasificar EXACTAMENTE las siguientes empresas competidoras en una
matriz de grupos estratégicos 2×2, cruzando enfoque de mercado (Masivo/Volumen
vs. Nicho/Premium) con naturaleza del modelo operativo (Jugadores Tradicionales
vs. Entrantes Innovadores).

LISTA CERRADA DE EMPRESAS A CLASIFICAR (no añadir ninguna otra):
{closed_list_str}

ATRIBUTOS DE FICHA DE CADA EMPRESA (usa solo esta información):
{fichas_context}

SECTOR DE LA EMPRESA ANALIZADA:
{empresa_sector}

REGLAS OBLIGATORIAS:
1. Clasifica ÚNICAMENTE las empresas de la lista cerrada. PROHIBIDO añadir nuevas marcas.
2. Cada empresa debe quedar en EXACTAMENTE UN cuadrante.
3. Si no tienes datos suficientes para clasificar un atributo, indícalo como
   "Dato no disponible en fuentes consultadas" en la síntesis narrativa; pero
   igual asigna la empresa al cuadrante más probable según los datos disponibles.
4. Responde ÚNICAMENTE con el JSON especificado. Sin texto adicional antes o después.

{feedback}
```

## Human Prompt

```text
Clasifica las empresas de la lista cerrada en la matriz 2×2 y redacta la síntesis
de presión competitiva.

Responde SOLO con este JSON (sin markdown fences):
{{
  "cuadrantes": {{
    "masivo_tradicional": ["Empresa A", "Empresa B"],
    "masivo_innovador":   ["Empresa C"],
    "nicho_tradicional":  ["Empresa D"],
    "nicho_innovador":    []
  }},
  "intro": "Párrafo introductorio (1-2 oraciones) explicando la segmentación.",
  "sintesis_incumbente": "Párrafo analizando la defensa del incumbente (economías de escala, vulnerabilidades estructurales).",
  "sintesis_entrante": "Párrafo analizando el ataque del entrante y la servitización, conectando con el sector de la empresa analizada."
}}
```

---

## Parámetros de inyección

| Variable | Origen | Ejemplo |
|----------|--------|---------|
| `closed_list_str` | `Cap21Jugadores` — todos los nombres concatenados, uno por línea | `"- Nestlé\n- Danone\n- Nutresa"` |
| `fichas_context` | `format_fichas_conocidas(fichas_kb)` — atributos de ficha del KB | Texto con portafolio, propuesta de valor, etc. |
| `empresa_sector` | `DescripcionEmpresa.texto` + `ClasificacionGICS.grupo_gics` | `"Alimentos procesados (GICS 3020)"` |
| `feedback` | Retroalimentación del revisor (opcional) | `""` o `"Enfatizar más los entrantes deeptech"` |

---

## Esquema JSON de salida

```json
{
  "cuadrantes": {
    "masivo_tradicional": ["string"],
    "masivo_innovador":   ["string"],
    "nicho_tradicional":  ["string"],
    "nicho_innovador":    ["string"]
  },
  "intro": "string",
  "sintesis_incumbente": "string",
  "sintesis_entrante": "string"
}
```

- Los arrays en `cuadrantes` pueden estar vacíos `[]`; el assembler renderizará `(ninguno)`.
- La suma de todos los nombres en los cuatro cuadrantes DEBE ser igual a la lista cerrada.
- Algunos modelos de OpenRouter envuelven el JSON en fences ` ```json ... ``` `; el parser (`_parse_llm_json`) los elimina antes de parsear.

---

## Grounding rules (resumidas para el implementador)

1. **Lista cerrada**: solo las empresas de `{closed_list_str}` pueden aparecer en `cuadrantes`.
2. **Sin inferencia de atributos**: si la ficha no tiene dato, indicarlo en la síntesis; no inventar.
3. **Modelo nunca hardcodeado**: el `llm` se inyecta desde la capa de infraestructura (ADR-002).
