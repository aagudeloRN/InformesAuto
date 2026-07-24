# Rúbrica de Calidad del Informe — derivada del patrón Noel

> **Origen:** Fase 20 (Gap Analysis). Derivada de `InformeSectoryCompetitivoNoel.docx`
> (informe manual de referencia) y de los `source_prompts/*.docx` originales.
> **Propósito:** convertir "el informe todavía no se parece al que quiero" en una medición
> repetible, aplicable de forma manual y como *LLM-judge*.
> **Versión:** 1.0 · **Fecha:** 2026-07-24

---

## 1. Cómo se usa

Cada capítulo se puntúa en **5 dimensiones**, cada una de **0 a 3**:

| Punt. | Significado |
|------|-------------|
| 0 | Ausente / no cumple |
| 1 | Presente pero deficiente (genérico, incompleto, sin evidencia) |
| 2 | Cumple con carencias menores |
| 3 | Equivalente al patrón Noel |

**Dimensiones (comunes a todos los capítulos):**

- **E — Estructura:** ¿están los subcapítulos esperados, en el orden y numeración correctos?
- **P — Profundidad:** datos concretos, cifras, nombres propios vs generalidades de relleno.
- **V — Evidencia/Citación:** afirmaciones sustentadas y trazables a fuente (APA 7, RN-002);
  ausencias declaradas con la plantilla, no inventadas (RN-001).
- **F — Elementos visuales (Formato):** tablas, fichas y figuras que el patrón exige.
- **T — Tono:** ejecutivo, storytelling sin viñetas, sin muletillas de IA, es-CO neutro.

**Score del capítulo** = suma (0–15). **Score del informe** = promedio ponderado (ver §4).
Umbral de aceptación por capítulo: **≥ 11/15** (≈ 73%) y **ninguna dimensión en 0**.

El evaluador registra, por capítulo, las 5 cifras + una nota de una línea por cada dimensión
< 2. La plantilla de salida está en §5.

---

## 2. Rúbrica por capítulo (esperado = patrón Noel)

### Resumen Ejecutivo (N3)
- **E:** texto corrido, sin encabezados de sección; ~1 página.
- **P:** gancho narrativo + propósito + problema + solución + 3 hallazgos + llamado a la acción
  (6 elementos del `source_prompt 11`). Cada dato con interpretación estratégica.
- **V:** hallazgos coherentes con los capítulos; sin datos nuevos no presentes en el cuerpo.
- **F:** sin listas fragmentadas (es prosa continua).
- **T:** C-Level; prohibido "es importante", "se recomienda", "se observa", "hay oportunidades".

### Cap 1 — Descripción de la Empresa (N0)
- **E:** 9 secciones exactas (Descripción general … Oportunidades y riesgos) + Clasificación GICS.
- **P:** cada afirmación específica de la empresa; CIIU/RUES como punto de partida; inferencias
  marcadas con "Inferencia:".
- **V:** todo trazable al contexto web; ausencias con "Dato no disponible en fuentes consultadas".
- **F:** ficha/tabla de identificación de la empresa (portada + ficha, como Noel T1/T2).
- **T:** analítico, sin bienvenidas ni disculpas.

### Cap 2 — Análisis Competitivo (N1)
- **E:** **2.1** Jugadores Clave (Globales / Regionales LatAm / Startups) · **2.2** División de
  competidores (matriz 2×2 + síntesis) · **2.3 Mercado** · **2.4** Módulos Innovación/Inversión/RRHH
  · **2.5** Análisis de Brechas. *(El patrón Noel tiene las 5; ver brecha 2.3 en §3.)*
- **P:** 14 actores (8 globales + 3 regionales + 3 startups) con los 8 puntos de la ficha;
  cifras de cuota de mercado / ingresos reales.
- **V:** cada ficha citada `(Autor, año)`; nunca nombre de archivo; empresa analizada excluida.
- **F:** **fichas en tabla** (7 columnas tipo Noel T3/T5/T7) + matriz 2×2 + **radar** + tabla de
  mercado por región (Noel T10).
- **T:** 2.1 fichas; 2.2/2.4/2.5 storytelling sin viñetas.

### Cap 3 — Análisis Sectorial Tendencial (N1)
- **E:** párrafo intro fijo · **3.1** 6 tendencias (2 T / 2 E / 2 S) · **3.2** 4 MECE · **3.3**
  casos globales (1 por MECE) + casos locales (1 por tendencia tecnológica).
- **P:** títulos sugestivos; datos cuantitativos post-2026; horizonte temporal (corto/mediano/largo);
  casos ≥150 palabras con empresa/qué hizo/resultado.
- **V:** nivel de confianza (Alto/Medio/Bajo) justificado; casos locales **del mismo sector GICS**
  (ver DT-036); sin inventar.
- **F:** — (capítulo narrativo; sin tablas obligatorias).
- **T:** ejecutivo; sin "podría/quizás"; storytelling.

### Cap 4 — Panorama Ecosistema (N1)
- **E (patrón Noel):** **4.1** Inversiones en startups/locales · **4.2** Integraciones verticales
  · **4.3** Fusiones y adquisiciones (M&A) · **4.4** Joint ventures · **4.5** Alianzas de compra.
  3 eventos por subcapítulo. *(La cadena actual produce otra estructura — ver brecha mayor en §3.)*
- **P:** por evento: Título + ejecución + **capacidad estratégica adquirida** + **vulnerabilidad
  mitigada**; foco en el ecosistema local (Medellín/Antioquia/Colombia).
- **V:** cada evento citado; sin relleno; empresas reales distintas de la analizada.
- **F:** — (narrativo por eventos con título en negrilla).
- **T:** analítico y objetivo; storytelling sin viñetas.

### Cap 5 — Convergencia Empresarial en Áreas Estratégicas del Distrito (N2)
- **E:** exactamente **4 áreas** — 5.1 Sostenibilidad Ambiental · 5.2 Transformación Digital y
  Gobierno Inteligente · 5.3 Desarrollo Social-Humano · 5.4 Desarrollo Económico. *(No más, no
  menos — ver brecha "deriva de áreas" en §3.)*
- **P:** por área: oportunidad concreta + justificación + 3 acciones con título en negrilla
  (≥100 palabras c/u); ≥300 palabras por área; sin repetir ideas entre áreas.
- **V:** derivado de caps previos + contexto territorial (Convergencia.pdf global).
- **F:** — (narrativo).
- **T:** consultor senior; storytelling sin viñetas.

### Cap 6 — Accionables Estratégicos (N2)
- **E:** exactamente 6 accionables, cada uno con título en negrilla + descripción + justificación.
- **P:** cruzan hallazgos de Caps 2/3/4/5; ejecutables; ≥150 palabras; 6 dimensiones distintas
  (competitividad, transformación digital, sostenibilidad, talento, ecosistema, mercado).
- **V:** cada accionable referencia un hallazgo concreto de un capítulo previo (coherencia, Q1/F22).
- **F:** — (narrativo).
- **T:** consultivo; sin "Accionable N:"; storytelling.

### Secciones transversales
- **Metodología** (Heading 1 propio en Noel): describe fuentes, proceso y alcance. **Ausente hoy.**
- **Aviso sobre el uso de IA** (Heading 2 bajo Metodología en Noel): declaración formal.
  Hoy solo existe un `disclaimer` de una línea al pie (ver brecha en §3).
- **Referencias** (APA 7, RN-002): lista final trazable, sin nombres de archivo.

---

## 3. Brechas estructurales del patrón (resumen; detalle y fase destino en `FASE20_HALLAZGOS.md`)

| Brecha | Patrón Noel | Estado actual | Severidad |
|--------|-------------|---------------|-----------|
| **2.3 Mercado** | Subcap presente + tabla mercado por región (T10) | No implementado (era `source_prompt 4/5`) | 🔴 |
| **Cap 4 estructura** | 4.1–4.5 movimientos (M&A/JV/alianzas) con eventos | Cadena produce Local/Global/Disruptores | 🔴 |
| **Metodología + Aviso IA** | Secciones formales propias | Solo disclaimer de 1 línea | 🟠 |
| **Fichas de competidor en tabla** | Tablas 7 columnas (T3–T8) | Markdown pipe pedido; 0 tablas en 2/3 outputs | 🟠 |
| **Sesgo sectorial en prompts** | Neutro (era para Noel/alimentos) | "FoodTech"/"agroindustrial" hardcodeado | 🟠 |
| **Cap 5 — nº de áreas** | 4 fijas | Deriva (avianca 5.1–5.7) | 🟠 |

---

## 4. Ponderación para el score del informe

| Capítulo | Peso |
|----------|------|
| Resumen Ejecutivo | 10% |
| Cap 1 Descripción | 10% |
| Cap 2 Competitivo | 20% |
| Cap 3 Tendencial | 15% |
| Cap 4 Ecosistema | 15% |
| Cap 5 Convergencia | 10% |
| Cap 6 Accionables | 15% |
| Transversales (Metodología/Aviso IA/Referencias) | 5% |

**Informe aceptable:** score ponderado ≥ 73% **y** ningún capítulo con dimensión en 0.

---

## 5. Plantilla de evaluación (copiar por informe)

```
Informe: <empresa> · Fecha: <yyyy-mm-dd> · Evaluador: <manual|llm-judge>

| Capítulo            | E | P | V | F | T | Σ/15 | Notas (dim < 2) |
|---------------------|---|---|---|---|---|------|-----------------|
| Resumen Ejecutivo   |   |   |   |   |   |      |                 |
| Cap 1 Descripción   |   |   |   |   |   |      |                 |
| Cap 2 Competitivo   |   |   |   |   |   |      |                 |
| Cap 3 Tendencial    |   |   |   |   |   |      |                 |
| Cap 4 Ecosistema    |   |   |   |   |   |      |                 |
| Cap 5 Convergencia  |   |   |   |   |   |      |                 |
| Cap 6 Accionables   |   |   |   |   |   |      |                 |
| Transversales       |   |   |   |   |   |      |                 |

Score ponderado: __%  ·  Veredicto: <acepta|rechaza>
```

Para el modo *LLM-judge*: pasar el `.docx` (convertido a texto) + esta rúbrica + la plantilla,
con temperatura 0 y la instrucción de puntuar solo con evidencia textual del informe.
