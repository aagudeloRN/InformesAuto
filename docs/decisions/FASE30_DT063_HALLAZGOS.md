# Fase 30 — DT-063: Descubrimiento de competidores guiado por producto/servicio

> Estado: implementado (rama `develop`). Gate: ruff 0, 548 fast tests. E2E pendiente de correr
> (sección al final). Reemplaza el sub-código GICS como driver del descubrimiento.

## Contexto

El E2E de Alpina (lácteos) con DT-050/DT-062 activos reveló que anclar el descubrimiento en el
**sub-código GICS** (302010/20/30) es frágil: el nombre del grupo 3020 es *"Alimentos, bebidas y
**tabaco**"*, y `resolve_sub_gics` leyó "tabaco" de esa etiqueta en la descripción → DT-062 sembró
**globales de tabaco** (Philip Morris, BAT…) en el tier de clase mundial 2.1.1 de una empresa láctea.
Además el sub solo existe para 3020 (los otros 24 grupos no tienen granularidad) → parche mono-sector.

**Decisión (usuario):** el driver debe ser **la descripción de la empresa — sus productos/servicios**
(ya es un capítulo, Cap 1), no un sub-código adivinado. Ser crítico y **genérico**, no parchar un
caso. Ver [[feedback_discovery_producto_driven]].

## Arquitectura — dos capas + fallback

- **Recall / guardrail:** el **grupo GICS** acota el dominio (prompt de globales) y trae los
  candidatos del directorio local. Barato, O(1), evita drift.
- **Precisión:** los **productos/servicios** (sección "## Productos y servicios" de Cap 1) →
  (1) steerean el prompt de globales (DT-062), (2) re-rankean locales/startups del directorio por
  **solape de keywords** producto↔actividad. Genérico para los 25 grupos.
- **Fallback:** descripción pobre/sin sección → nivel grupo (orden por evidencia/tamaño), **nunca**
  un sub adivinado. Esto mata el bug de Alpina por construcción: el "tabaco" de la etiqueta del sector
  vive en "Descripción general", no en "Productos y servicios" → no contamina.

## Componentes

| Capa | Archivo | Rol |
|---|---|---|
| shared | `shared/text_productos.py` | `extract_productos_servicios`, `producto_terms`, `producto_overlap` (puros) |
| shared | `shared/types.py` | `DescripcionEmpresa.productos_servicios` |
| domain | `domain/use_cases/generate_empresa_description.py` | puebla el campo desde Cap 1 |
| domain | `domain/chains/chain_02c_pares_globales.py` | prompt por `{productos}`+`{sector_gics}` |
| domain | `domain/use_cases/discover_globales.py` | `discover(sector_gics, productos)`; sin sub-código |
| domain | `domain/kb/relevance.py` | `ProductoRankRow` + `rank_by_product_overlap` (require_overlap) |
| data | `data/repositories/entidad_repo.py` | `list_competidores_by_sector` (global, JOIN `productos_perfil`) y `list_locales_by_sector` (local, re-rank por solape) |
| domain | `domain/use_cases/generate_n1.py` | pasa `productos`/`productos_terms`; elimina `sub_code`; guard por producto; siembra `productos_perfil` del global corroborado |

Nota: `resolve_sub_gics`/`sub_gics_label`, la columna `sub_gics` y `filter_rank_competidores` **quedan**
(no se borran; el directorio EMIS aún tagea `sub_gics` informativo). Dejan de ser el driver del
descubrimiento → sin churn de esquema. Auto-sanado del KB: el descubrimiento re-siembra los globales
relevantes (Nestlé/Danone…) con su `productos_perfil` en la corrida, así el anclaje los recupera aunque
la semilla previa no tuviera perfil.

## Verificación E2E — Alpina (lácteos), DT-063

Corrida con `anclaje_local_enabled=true discover_globales_enabled=true --ciiu 1040`.

**Bug intermedio hallado y corregido (`fix(dt063)`):** al pasar `--ciiu`, `generate_informe`
reconstruía `ctx.empresa` a mano y **perdía `productos_servicios`** → señal vacía → require_overlap no
filtraba → fallback a grupo (tabaco reaparecía). Fix: `dataclasses.replace` (preserva el campo) + red
de seguridad que re-deriva de `texto`.

**Resultado tras el fix (log + docx):**
- `DiscoverGlobales productos='…Alpina…fabrica y comercializa…'` (señal NO vacía), 12/12 corroborados.
- Competidores anclados (KB=8): **Fonterra, Danone, Arla Foods, Bel Group, Abbott, Kraft Heinz,
  Kellogg's, Coca-Cola** — todo lácteos/alimentos/bebidas.
- docx 2.1: **0 tabaco, 0 cerveza** (antes: Philip Morris, BAT, Japan Tobacco). Anti-mezcla ajeno=0.
- **Objetivo cumplido:** el descubrimiento y el anclaje son product-driven; el tabaco de la etiqueta
  del sector ya no contamina 2.1.1.

**Matiz (ortogonal a DT-063):** en esta corrida el LLM gratuito (Nemotron) **rehusó redactar las
fichas** de 2.1 ("con las fuentes proporcionadas no es posible…") → no se materializaron en prosa. Es
variabilidad del modelo + evidencia delgada (DT-049), no del pipeline de descubrimiento. Los
competidores correctos SÍ se identificaron y anclaron.

**Pendiente:** confirmar disjunción con una cervecera y una tabacalera (globales de cerveza / tabaco
respectivamente); y atacar la fiabilidad de redacción de fichas (DT-049 / evidencia).

## Quick-win (NurtureKB) — CERRADO

Aprovechar la descripción de Cap 1 (ya pagada) de la empresa analizada:
- **NurtureKB** guarda ahora `alcance=local` + atributo `productos_perfil` de la empresa analizada
  (`feat(dt063): NurtureKB…`). `list_locales_by_sector` incluye `productos_perfil` en el descriptor
  del re-rank. **Verificado en vivo:** Alpina quedó en el KB (`alcance=local`, `verificado`, 3020) con
  `descripcion` + `productos_perfil` → se reusará como competidor regional rankeado por solape cuando
  se analice otra láctea (idea del usuario, ciclo cerrado). 550 fast tests.

## Hallazgo del E2E con self-review (semilla de DT-064)

E2E con `selfreview_enabled=true`: **el self-review rescata capítulos** (Cap 2 **6→11**, Cap 5 9→14,
Cap 6 10→15; Cap 4 4→4 sin mejora por evidencia delgada). Las 7 tablas de fichas se renderizaron.

**Pero el contenido de las fichas es incorrecto** — al inspeccionar el .docx:
- 2.1.1 Globales: **Bavaria (cerveza), British American Tobacco (tabaco)** ❌
- 2.1.2 Regionales: Brinsa (sal), Gaseosas de Córdoba — colombianas pero no lácteas
- 2.1.3 Startups: EATCLOUD, AGROFERTAS

**El conjunto anclado era correcto (Danone/Kellogg's/Fonterra… lácteos), pero las fichas NO lo usan.**
Dos causas de raíz (→ DT-064):
1. **La síntesis escribe las fichas desde el RAG**, no desde la lista anclada. El RAG contiene
   cerveza/tabaco (las queries genéricas de sector "Alimentos, bebidas y tabaco líderes globales" lo
   traen). El anclaje DT-063 guía la *identificación de entidades* + *búsqueda dirigida*, pero el
   prompt final elige nombres del RAG contaminado.
2. **El self-review re-sintetiza SIN el anclaje**: `review_web_cap` regenera con su propio prompt y
   **no recibe** `kb_competidores`/`jugadores_locales` → al rescatar (6→11) reescribió desde RAG →
   volvieron Bavaria/BAT.

Fix = **DT-064** (`docs/architecture/DT064_PLAN.md`): inyectar la lista anclada como **sujetos
explícitos** de las fichas en benchmarking **y** en el self-review; **persistir** los datos de ficha
por competidor (reuso + menos variabilidad); detector de negativas.

## Sucesores

- Si el solape de keywords se queda corto (actividad CIIU coarsa) → **embeddings pgvector**
  producto↔actividad (futuro).
- Purga opcional de los globales de tabaco huérfanos de la corrida buggeada (sin `productos_perfil`;
  hoy filtrados por require_overlap).
- DT-050b (reconciliación de entidades + HITL) sigue vigente.
