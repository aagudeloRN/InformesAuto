# ADR-013 — Persistencia web "solo lo citado" y ciclo de vida por sesión

**Fecha:** 2026-07-22
**Estado:** Aprobado
**Fase:** 14 (DT-020)

---

## Contexto

Hasta Fase 13, los resultados de búsqueda web se **persistían al buscar**: cada corrida
ingería en pgvector los chunks web de todas sus consultas, citados o no. Esto acumulaba un
backlog sin ciclo de vida (~1202 chunks al cierre de Fase 13) que crecía sin control con cada
informe y ocupaba slots de contexto compitiendo con el corpus sectorial (hallazgo Fase 14: la
purga de ese backlog subió la densidad de evidencia sectorial de 3.20 a 3.68 chunks/consulta en
el path de producción).

Política de datos acordada: **la información web solo debe persistir si fue efectivamente
citada en un informe** (presente en `chunks_usados`, que alimenta `build_references_section`).

---

## Decisión

Ciclo de vida web por **sesión de corrida** (enfoque *session ingest + purga*):

### 1. Ingesta etiquetada por sesión

Cada corrida genera un `session_id` (uuid). Los chunks web se ingieren en pgvector como hasta
ahora —para que participen del ranking con la reserva/cap de ADR-012 sin reescribir la ruta de
búsqueda— pero **etiquetados** con `metadatos.session_id`. Otras fuentes (PDF, académicas) no
llevan `session_id`.

### 2. Promoción "solo lo citado" al ensamblar

Al construir las referencias (`generate_informe._run_n3`), se calcula el conjunto de chunks web
citados (`chunk_id ∈ chunks_usados` con `fuente_tipo="web"`) y se invoca
`EmbeddingRepository.promote_cited_web(session_id, cited_ids)`:

- **Borra** los chunks web de la sesión **no** citados.
- **Promueve** los citados a permanentes: les quita `session_id` y les marca
  `metadatos.promoted="true"`.

### 3. Tres estados discriminables de un chunk web

| Estado | `session_id` | `promoted` | Significado |
|--------|--------------|------------|-------------|
| En sesión | presente | — | En una corrida en curso; visible para el retrieval |
| Promovido | ausente | `"true"` | Citado en un informe; permanente |
| Legacy | ausente | ausente | Backlog histórico pre-Fase-14; objetivo de la purga |

La marca `promoted` es lo que distingue un chunk citado de un legacy (ambos sin `session_id`),
evitando que la purga borre evidencia citada.

### 4. Barrido de huérfanos y purga única

- `sweep_stale_web_sessions(keep_session_id)` se ejecuta al **inicio** de cada corrida y borra
  chunks web con un `session_id` distinto del actual (huérfanos de corridas que crashearon
  antes de promover).
- `purge_unused_web_backlog()` (script `scripts/purge_web_backlog.py`, con dry-run) es una
  operación **única** que borra los chunks legacy (sin `session_id` ni `promoted`).

---

## Consecuencias

- **Positivas:** el conteo de chunks web deja de crecer con búsquedas descartadas; solo persiste
  evidencia efectivamente citada; se libera espacio de contexto (más evidencia sectorial aflora,
  3.20→3.68 chunks/consulta); el ranking pgvector + reserva/cap de ADR-012 quedan intactos (no
  se reescribe la ruta de búsqueda).
- **Costo/limitaciones:** un crash a mitad de corrida deja chunks en-sesión, mitigado por el
  barrido al inicio de la siguiente. El diseño asume corridas **secuenciales** (un usuario);
  corridas concurrentes podrían pisarse las sesiones (aceptable en el despliegue WSL actual).
- **Migración:** la promoción usa `jsonb_build_object` (no literales de llaves en f-strings) y
  el operador `-` de JSONB; idempotente y sin cambios de esquema.

---

## Alternativa descartada

**Retrieval 100% en memoria** (no persistir web nunca; embeber en memoria y fusionar por coseno
en Python, persistir solo lo citado al final). Fiel a la letra de "no persistir al buscar", pero
reescribía la ruta de merge de `search()` y cambiaba la semántica de retrieval respecto a la
línea base, invalidando el harness T14.1 para comparaciones. Se prefirió *session ingest + purga*
por mínima invasión y por preservar el ranking pgvector medido.
