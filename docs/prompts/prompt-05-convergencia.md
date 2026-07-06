# Prompt-05: Capítulo 5 — Convergencia Empresarial en Áreas Estratégicas

**Rol:** Consultor senior en estrategia empresarial y transformación digital  
**Entrada:** `{descripcion_empresa}`, `{sector_gics}`, `{retrieval_caps_anteriores}`,
`{retrieval_convergencia_territorial}`, `{dofa_came_contexto}`  
**Salida:** Markdown con 4 secciones (5.1–5.4), storytelling, sin viñetas  
**Fuentes:**
- Outputs de Cap 2 (benchmarking), Cap 3 (tendencias), Cap 4 (ecosistema) via RAG
- Documento de convergencia territorial del distrito (Medellín/Antioquia) via RAG (ingesta PDF manual)
- Búsquedas web: políticas de desarrollo sectorial, áreas estratégicas municipales/nacionales
- Información DOFA/CAME derivada del análisis de caps anteriores

---

## Diferencia clave respecto al prompt original (NotebookLM)

El prompt original consume dos PDFs:
- `Convergencia.pdf` — informe de convergencia territorial del distrito (Plan de Desarrollo, áreas estratégicas)
- `DescripcionNoel.pdf` — descripción de la empresa

En el sistema automatizado, estas fuentes se sustituyen por:
- **Ingesta PDF manual** del informe de convergencia local: `InformeConvergenciaLocal2026V3RvADAA.pdf`
  via `scripts/ingest_pdf.py` antes de ejecutar el pipeline
- **RAG sobre outputs de caps anteriores** (tendencias, ecosistema, benchmarking) ya indexados
- **Búsquedas web** sobre las 4 áreas estratégicas aplicadas al sector de la empresa

---

## Secciones del capítulo

```
5.1 Área Estratégica: Sostenibilidad Ambiental
5.2 Área Estratégica: Transformación Digital y Gobierno Inteligente
5.3 Área Estratégica: Desarrollo Social-Humano
5.4 Área Estratégica: Desarrollo Económico
```

Para cada área:
- Oportunidad concreta basada en tendencias
- Justificación (por qué esta área estratégica aplica a esta empresa)
- 3 acciones específicas con título descriptivo en negrilla
- Storytelling, texto corrido, sin viñetas
- Sin citaciones inline en el cuerpo (referencias al final)

---

## System Prompt

```
Eres un consultor senior en estrategia empresarial y transformación digital con más de 15 años
de experiencia asesorando empresas en América Latina. Tienes conocimiento profundo en análisis
de tendencias tecnológicas, económicas y sociales, frameworks de competitividad y planificación
estratégica.

REGLAS DE CONTENIDO:
- Sustenta cada afirmación en los fragmentos de fuentes proporcionados.
- Si un dato no está disponible: "Dato no disponible en fuentes consultadas."
- No inventar información. No inferir datos sin evidencia en el contexto.
- IDIOMA: español latino neutro. Prohibido usar otro idioma.

REGLAS DE ESTILO:
- Tono ejecutivo y directo.
- Prohibido: "podría", "quizás", "en resumen", "por lo tanto", "cabe destacar".
- Sin adjetivos vacíos (innovador, disruptivo) salvo evidencia cuantificable.
- Cada sección: texto corrido (storytelling), sin viñetas.
- Varía el ritmo: alterna frases cortas (≤12 palabras) con frases más largas.
- Sin mini-checklists ni meta-comentarios al final.
```

## Prompt de usuario

```
Genera el "Capítulo 5. Convergencia Empresarial en las Áreas Estratégicas del Distrito"
para el informe de inteligencia competitiva de la empresa descrita a continuación.

DESCRIPCIÓN DE LA EMPRESA:
{descripcion_empresa}

CLASIFICACIÓN SECTORIAL:
{sector_gics}

HALLAZGOS DE CAPS ANTERIORES (RAG sobre benchmarking, tendencias, ecosistema):
{retrieval_caps_anteriores}

CONTEXTO TERRITORIAL Y ÁREAS ESTRATÉGICAS DEL DISTRITO:
{retrieval_convergencia_territorial}

Inicia con el siguiente párrafo introductorio (transcríbelo exactamente):
"La convergencia empresarial analiza cómo las estrategias de la empresa se alinean con las
prioridades del territorio y las tendencias del sector, identificando puntos de intersección que
generan ventajas competitivas sostenibles y contribuyen al desarrollo regional."

## 5.1 Área Estratégica: Sostenibilidad Ambiental

Identifica oportunidades concretas para la empresa en sostenibilidad ambiental derivadas del
contexto territorial y sectorial. Explica el por qué de cada oportunidad. Propone 3 acciones
específicas con título en negrilla. Formato: storytelling sin viñetas.

## 5.2 Área Estratégica: Transformación Digital y Gobierno Inteligente

Ídem para transformación digital: cómo la empresa puede aprovechar las iniciativas de
digitalización del sector y del territorio.

## 5.3 Área Estratégica: Desarrollo Social-Humano

Ídem para desarrollo social: talento, inclusión, bienestar, responsabilidad empresarial
en el contexto del sector y el territorio.

## 5.4 Área Estratégica: Desarrollo Económico

Ídem para desarrollo económico: competitividad, exportaciones, empleo, encadenamientos
productivos, inversión en el sector.

Reglas de presentación:
- Cada área: mínimo 300 palabras.
- Acciones específicas: título en negrilla + párrafo de al menos 100 palabras.
- No repetir ideas entre áreas.
- Sin citaciones inline.
```

---

## Fuentes que requieren acción manual previa

| Fuente | Tipo | Acción requerida |
|--------|------|------------------|
| Informe de Convergencia Local (ej. Alcaldía Medellín) | PDF | `scripts/ingest_pdf.py --titulo "..." --fuente "Alcaldía de Medellín" --año 2026` |
| Plan de Desarrollo Municipal | PDF | ídem |
| Agenda Digital Colombia | web/PDF | Búsqueda automática o ingesta manual |
| Cap 2 chunks (benchmarking) | RAG interno | Ya disponible si Cap 2 se ejecutó |
| Cap 3 chunks (tendencias) | RAG interno | Ya disponible si Cap 3 se ejecutó |
| Cap 4 chunks (ecosistema) | RAG interno | Ya disponible si Cap 4 se ejecutó |

---

## Notas de implementación

- **Tier LLM:** `synth` (Nemotron Ultra free) — este cap requiere síntesis cruzada de múltiples fuentes.
- **MIN_CHUNKS:** 5 (mayor que N1 analíticos; la convergencia necesita más contexto base).
- **Query RAG sugerida para caps anteriores:**
  ```
  "{sector_gics} {nombre_empresa} tendencias ecosistema benchmarking estrategia"
  ```
- **Query RAG sugerida para convergencia territorial:**
  ```
  "{sector_gics} {nombre_empresa} sostenibilidad transformación digital desarrollo económico Medellín"
  ```
- **Búsquedas web automáticas:**
  ```python
  web_queries = [
      f"{sector_gics} sostenibilidad ambiental Colombia regulaciones",
      f"{sector_gics} transformación digital gobierno inteligente Colombia",
  ]
  ```
- **Barrera de sincronización:** Caps 2, 3 y 4 deben estar persistidos antes de ejecutar Cap 5.
  Este capítulo es N2 en el DAG (consume outputs de N1).
- **DOFA/CAME:** En Fase 5E se puede derivar del cruce de benchmarking (Cap 2) + tendencias (Cap 3)
  sin un prompt separado, o generar un mini-capítulo DOFA como paso intermedio.
