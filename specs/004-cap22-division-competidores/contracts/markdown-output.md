# Contract: Formato Markdown de Salida — Cap 2.2

**Tipo**: Contrato de formato de salida (internal module contract)
**Consumidores**: renderer docx (`parse_markdown`), presentación Streamlit, Cap 6 (síntesis N2), `save_capitulo`

---

## Estructura canónica

El texto generado en `Cap22Division.texto` DEBE conformarse exactamente a esta estructura:

```markdown
## 2.2. División de Competidores

<PÁRRAFO_INTRODUCTORIO>

| Enfoque de mercado | Jugadores Tradicionales (Modelos Consolidados) | Entrantes Innovadores (Modelos Ágiles / DeepTech / Startups) |
|--------------------|------------------------------------------------|---------------------------------------------------------------|
| **Masivo / Volumen** | Empresa A, Empresa B | Empresa C |
| **Nicho / Premium** | Empresa D | Empresa E, Empresa F |

### Síntesis de Presión Competitiva

#### La defensa del incumbente

<PÁRRAFO_INCUMBENTE>

#### El ataque del entrante y la servitización

<PÁRRAFO_ENTRANTE>
```

---

## Reglas de conformidad

### Heading

- El heading de nivel 2 (`## 2.2. División de Competidores`) es literal e inmutable.
- No se añaden headings adicionales antes del párrafo introductorio.

### Párrafo introductorio

- 1-2 oraciones.
- Explica la segmentación cruzando enfoque de mercado (volumen vs. nicho) con naturaleza del modelo operativo (tradicional vs. innovador/ágil).
- No menciona empresas específicas.

### Tabla 2×2

- Exactamente 2 filas de datos (Masivo/Volumen y Nicho/Premium). Sin filas adicionales.
- Exactamente 2 columnas de contenido (Tradicional e Innovador). Sin columnas adicionales.
- Fila de cabecera con columna `Enfoque de mercado` siempre presente.
- Nombres de empresa separados por `,` + espacio dentro de cada celda.
- Si un cuadrante no tiene empresas: `(ninguno)` — nunca celda vacía, nunca omitir la fila.
- Los nombres de empresa son exactamente los que figuran en el dataset de Cap 2.1 (sin variaciones ortográficas, sin abreviaciones).
- Cada empresa aparece **exactamente una vez** en toda la tabla (sin duplicados cross-cuadrante).

### Subsección Síntesis de Presión Competitiva

- Heading `### Síntesis de Presión Competitiva` es literal e inmutable.
- Dos sub-headings `#### La defensa del incumbente` y `#### El ataque del entrante y la servitización` son literales e inmutables.
- Cada sub-sección: 1-3 párrafos de prosa analítica.
- El párrafo del incumbente menciona: economías de escala / redes de distribución + vulnerabilidad estructural (sistemas legacy, costos de reconversión o lentitud normativa).
- El párrafo del entrante menciona: cuellos de botella técnicos específicos + presión de servitización + conexión con el sector de la empresa analizada (Cap 1). Si el contexto de Cap 1 no está disponible, se omite la conexión sectorial y se añade nota entre corchetes: `[Contexto sectorial no disponible]`.

---

## Condición de ausencia

Si `retrieval_suficiente = False`, el texto es un párrafo de ausencia estándar:

```markdown
## 2.2. División de Competidores

La segmentación de grupos estratégicos no pudo realizarse porque no se identificaron competidores suficientes en la sección 2.1. Se recomienda ampliar las fuentes de datos o ajustar los criterios de búsqueda antes de regenerar este subcapítulo.
```

El heading `## 2.2.` se preserva incluso en condición de ausencia (el renderer docx lo necesita para el índice).

---

## Validaciones del assembler

El assembler (`seccion22_assembler.py`) valida antes de emitir el markdown:

1. **Cobertura**: `set(nombres_en_tabla) == set(closed_list)` → si no, lanza `CoverageError` con la diferencia.
2. **Unicidad**: ningún nombre aparece en más de un cuadrante → si no, lanza `DuplicateError`.
3. **Ninguno literal**: cuadrantes vacíos muestran `(ninguno)`, no string vacío.

Si las validaciones fallan después de 2 reintentos del LLM, el assembler devuelve la condición de ausencia con un warning en los metadatos.
