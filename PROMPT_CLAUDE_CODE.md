# PROMPT INICIAL PARA CLAUDE CODE

## Contexto cargado

Lee primero el archivo `README_CONTEXTO.md` en la raíz de este proyecto. Ese archivo contiene:
- Decisiones arquitectónicas cerradas (ADRs)
- Estado actual del proyecto
- Lo que falta por hacer
- Estructura de los 18 prompts originales
- El próximo paso exacto

## Tu tarea: Fase de Análisis de Prompts

**Objetivo:** Revisar los tres prompts del piloto y generar sus versiones parametrizadas `.md`.

**Entrada (archivos a revisar):**
- `/uploads/1__Prompt_Descripción_Empresa.docx`
- `/uploads/2__Prompt_Sector_GIS_de_la_empresa.docx`
- `/uploads/3__Prompt_-_Capítulo_2_-_Benchmarking.docx`

**Salida esperada:**
- `docs/prompts/prompt-01-descripcion-empresa.md` (parametrizado)
- `docs/prompts/prompt-02-sector-gics.md` (parametrizado)
- `docs/prompts/prompt-03-benchmarking.md` (parametrizado)

Plus: documento de decisión sobre refinamientos.

**Subtareas concretas:**

### 1. Leer y documentar cada prompt

Para cada uno de los tres prompts `.docx`:
- Extrae el texto completo
- Identifica la sección "# Rol / # Tarea / # Descripción" (estructura de NotebookLM)
- Identifica todas las variables que debería recibir como entrada (ej. {nombre_empresa}, {competidores}, etc.)
- Identifica las fuentes que debería consumir (retrieval web, PDFs, etc.)
- Documenta en un archivo temporal cualquier patrón de "refinamiento iterativo" que veas (pasos de "Mejora Capítulo X")

### 2. Decidir sobre refinamientos iterativos

Para cada paso de refinamiento que encuentres, aplica esta matriz:

| Refinamiento | ¿Instrucción de formato/estilo? | ¿Requiere nueva llamada LLM? | Decisión |
|---|---|---|---|
| Quita prefijos "Tecnológica 1/Económica 2" | Sí | No | → Collapse al system prompt |
| Divide en dos párrafos respirables | Sí | Potencialmente | → Collapse al system prompt (instrucción de formato) |
| Corrige citas APA | Sí | Sí | → Conserva como paso (post-generación, validación) |
| Amplía sección X | No | Sí | → Conserva como paso (nueva generación) |

Documenta tu decisión en `docs/decisions/REFINAMIENTOS_DECISION.md`.

### 3. Generar plantillas parametrizadas

Para cada prompt, crea una versión `.md` con:

```markdown
# Prompt-NN: [Nombre del capítulo]

**Rol:** [descripción de la tarea]  
**Entrada:** [variables que recibe: ej. {nombre_empresa}, {sector_gics}, {retrieval_competidores}]  
**Salida:** [formato esperado: markdown, JSON, texto, etc.]  
**Fuentes:** [dónde recupera datos: web, pdfs, retrieval, entrada usuario]

## System Prompt (constante, se usa en todos los LLM calls para este capítulo)

[Instrucciones generales que debería recibir el modelo: tono, restricciones de alucinación, formato APA, etc.]

## Prompt de usuario (parametrizado con variables)

[El prompt de generación, con placeholders como {nombre_empresa}, {competidores_list}, etc.]

## Post-processing (pasos LLM adicionales, si aplica)

[Si hay refinamientos que conservas como pasos reales, documentarlos aquí con qué trigger disparan]

## Notas de implementación

[Qué conectores de retrieval necesita, umbral de relevancia esperado, etc.]
```

### 4. Crear documento de decisión

Archivo `docs/decisions/REFINAMIENTOS_DECISION.md` con tabla resumen:

| Prompt | Refinamiento | Costo en llamadas | Decisión final | Justificación |
|--------|---|---|---|---|
| Descripción Empresa | [tipo] | [N llamadas actuales] | Collapse/Conserva | [porqué] |
| ... | ... | ... | ... | ... |

**Criterio de decisión:** Si el refinamiento es puramente instrucción de estilo/formato, collapse. Si requiere razonamiento/validación nuevo, conserva pero evalúa el costo real contra el presupuesto de 1 USD/informe.

---

## Cómo trabajar

1. **Usa Plan Mode obligatorio.** Primera acción: proponer plan de lectura de los tres prompts.
2. **No asumas estructura.** Abre los archivos `.docx` y extrae su contenido. Los encabezados en este README son observaciones, no especificación.
3. **Si algo no encaja:** vuelve a Plan Mode. No improvises.
4. **Commits frecuentes:** cada `.md` generado, cada decisión documentada.
5. **Si encuentras dependencias entre los tres prompts** (ej. el Benchmarking necesita la salida de Descripción): documéntalo.

---

## Herramientas disponibles

- `python-docx` ya instalado (puedes usarlo para extraer `.docx` limpio)
- CLAUDE.md y hooks ya configurados; disparan automáticamente en pre-commit/post-edit
- Los ADRs están en `/docs/architecture/` (o los tienes en el archivo de descarga)

---

## Qué espero de esta fase

Al terminar, tendré:

✅ Lectura completa de los tres prompts originales  
✅ Parametrización clara de variables de entrada  
✅ Decisión sobre refinamientos (tabla)  
✅ Tres plantillas `.md` listas para pasar a Fase 0 de código  
✅ Un documento que especifique exactamente cuántas llamadas LLM hace cada capítulo

Esto desbloquea Fase 0 (andamiaje) sin supuestos.

---

## Archivos de referencia dentro del proyecto

```
/docs/architecture/
  ADR-001-*.md
  ADR-002-*.md
  ADR-003-*.md
  PRIME_DIRECTIVE.md (la que debes copiar si no está)

/CLAUDE.md (lee si algo es ambiguo)

/README_CONTEXTO.md (referencia rápida)
```

---

Comienza. Propón tu plan de lectura/análisis en Plan Mode.
