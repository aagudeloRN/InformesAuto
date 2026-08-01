# DT-064 — Esquema de ficha de competidor (derivado de la verdad de terreno)

> Producto del **paso 1 (comparación ligera)** acordado el 2026-08-01. Se derivó leyendo la sección
> **2.1 Jugadores Clave** de los 5 informes manuales del cliente en `docs/ReportesHumanos/` (NO
> trackeados, `.gitignore`). Cobertura: **alimentos** (Noel, Alsec) + **no-alimentos** (Andercol
> químicos, Emtelco BPO/telecom, Guane software). Este archivo es un **esquema derivado** (no contiene
> datos propietarios de competidores) → es la especificación de T3 (persistencia) / T4 (pre-fill).

## Hallazgo principal

El esquema de ficha del humano es **idéntico y estable en los 5 informes**, e **independiente del
sector** (food y no-food usan exactamente los mismos campos y la misma partición en 3 tiers). Esto
confirma que el mecanismo debe ser **genérico**, no food-specific (coherente con DT-063).

Además: **los campos que ya pide el sistema** (`chain_03_benchmarking`, "8 puntos") **mapean 1:1** con
los campos del humano. Por tanto la brecha de DT-064 **no es de campos** sino de:
1. **Sujetos** de las fichas globales (hoy salen del RAG contaminado, no de la lista anclada) → T1/T2.
2. **Persistencia** de los valores de cada campo por competidor → T3/T4.
3. **Estabilidad** de la redacción (negativas del LLM) → T5.

## Estructura de 2.1 (verdad de terreno)

Tres tiers, en este orden, cada uno como bloque titulado + 2 tablas + línea de citas APA-inline:

| Tier | Etiqueta humana | Nº típico | Criterio de pertenencia |
|------|-----------------|-----------|-------------------------|
| **Globales** | `Referentes Globales` | 7–8 | Multinacionales consolidadas, presencia >100 países, gigantes del sector. |
| **Regionales** | `Referentes Regionales (Latam/Colombia)` | 3 | Líderes LatAm/Colombia, ingresos locales, exportación regional. |
| **Startups** | `Startups` o `Startups / FoodTech` (etiqueta adaptada al sector) | 3 | Emergentes tech/nicho, disruptores, modelo SaaS/B2B. |

El label del tier startup se **adapta al sector** (`Startups / FoodTech` en food; `Startups` a secas en
químicos/BPO/software). Los tiers **nunca se omiten** en los 5 informes.

## Campos por competidor (unión de las dos tablas por tier)

Cada tier se presenta con **dos tablas**:

**Tabla A — ficha (7 columnas):**
`Empresa | País de Origen | Resumen Estratégico | Portafolio / Productos Clave | Canales y Precios |
Presencia Geográfica | {Factor Diferencial | Propuesta de Valor}`

**Tabla B — "Mayor Fortaleza" (3 columnas):**
`Empresa | {Propuesta de Valor | Mayor Fortaleza} | {Mayor Fortaleza | Factor Diferencial}`

La 7ª columna de la Tabla A y las columnas 2–3 de la Tabla B **varían levemente** entre informes
(reordenan Factor Diferencial / Propuesta de Valor / Mayor Fortaleza), pero el **conjunto-unión de
campos es fijo**:

| Campo canónico (clave sugerida `entidad_atributos`) | Descripción | Ejemplo de granularidad esperada |
|---|---|---|
| `pais_origen` | País de la casa matriz | "EE. UU.", "Suiza", "España / Colombia" |
| `resumen_estrategico` | 1–2 frases de posicionamiento estratégico | con cifras: nº empleados, ingresos, nº países |
| `portafolio` | Productos/servicios clave | marcas/líneas concretas |
| `canales_precios` | Modelo de canal y posicionamiento de precio | "B2B outcome-based", "Masivo retail", "SaaS" |
| `presencia_geografica` | Alcance geográfico | ">150 países", "Colombia, España, LatAm" |
| `factor_diferencial` | Factor innovador/diferenciador | producto o capacidad patentada, cifra de inversión |
| `propuesta_valor` | Propuesta de valor al cliente | 1 frase |
| `mayor_fortaleza` | Mayor fortaleza competitiva | 1 frase |

→ 8 campos de contenido + `Empresa` (nombre) + `tier` (global/regional/startup). Coincide con los
"8 puntos" del system prompt actual.

## Profundidad y tono (spec cualitativo)

- **Celdas concretas y cuantificadas**: nº de empleados ("~490.000"), países ("189 países"), cifras
  US$ ("inversión de US$500 millones"), marcas nominales ("Oreo, Ritz"). Nada de relleno genérico.
- **1–2 frases por celda**. Sin adjetivos vacíos salvo con cifra que los respalde.
- **Citas APA-inline por tier** al cierre del bloque: `(Fuente, año. Fuente, año.)` — varias fuentes
  reales por tier (el humano usa 5–10 fuentes distintas por tier; contrasta con la evidencia delgada
  DT-049 del sistema, 3 refs).

## Implicaciones para las tareas DT-064

- **T1/T2 (sujetos anclados):** el tier **Globales** debe poblarse EXCLUSIVAMENTE con los globales
  anclados (`kb_competidores`); Regionales/Startups desde `{jugadores_locales}` (ya existe). El RAG
  solo llena los 8 campos de esos sujetos, nunca elige otros.
- **T3 (persistencia):** claves `entidad_atributos` = los 8 campos canónicos de arriba + `tier`.
  Provenance candidato (RN-001), idempotente (patrón DT-056).
- **T4 (pre-fill):** inyectar los 8 campos ya conocidos del KB como contexto estructurado (como
  `{jugadores_locales}`) → el LLM escribe desde hechos.
- **Set de evaluación (paso 4):** estas fichas humanas son el ground truth de regresión (nombres +
  valores por campo) y calibran la rúbrica v1.0.
