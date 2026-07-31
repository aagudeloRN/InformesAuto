# Propuesta — Base de conocimiento de empresas (directorio + acumulación)

> **Estado:** IMPLEMENTADA en Fase 29 (2026-07-31, rama `feature/fase29-dt050`). Ver
> `FASE29_HALLAZGOS.md` para el diseño final y las desviaciones respecto de esta propuesta:
> - El mapeo Sector(Local)→GICS NO necesitó tabla texto→GICS: el CIIU viene **embebido** en el texto
>   → mapeo por **división** (`ciiu_division_to_gics`).
> - En lugar de una tabla `empresas_directorio` separada se reusó la KB `entidades` (dedup por NIT,
>   `alcance=local`, `segmento`) + tabla nueva `entidad_sectores` (multi-sector con provenance).
> - Anclaje = contexto estructurado **y** búsqueda dirigida (flag `anclaje_local_enabled`, default OFF).
> - Curación humana sigue pendiente (HITL, F24/F25); el directorio entra como `candidato`.
> Registrada como **DT-050**. Documentada durante el cierre de F21 (2026-07-24).
> **No es un ADR**: es el diseño discutido/aprobado en Plan Mode (Fase 29).

## 1. Problema que resuelve

- **DT-049 (evidencia local delgada):** los informes citan pocas fuentes y dejan en ausencia las
  fichas de competidores y los jugadores locales (Cap 2.1 regionales, Cap 4 local, casos locales
  del Cap 3). El corpus EMIS aporta panorama de mercado, pero **no un directorio de empresas
  reales del sector** con datos básicos (razón social, ciudad, actividad, tamaño, NIT).
- **Trabajo repetido:** todo informe de un sector busca los mismos competidores/jugadores. Hoy esa
  búsqueda se recomputa en cada corrida (web) y, por ADR-013, la mayor parte se descarta. No hay
  memoria: dos informes del sector 3020 no comparten el trabajo de identificación de empresas.

**Idea del usuario:** mantener una tabla de empresas identificadas que **se nutra con cada informe**
y se pueda **curar con intervención humana** más adelante, de modo que un nuevo informe del mismo
sector reutilice lo ya conocido en lugar de re-buscar.

## 2. Activos disponibles

### 2.1 Corpus EmpresasColombia (semilla) — ALTA relevancia para lo local

`documentos_sectoriales/FuentesEMIS/EmpresasColombia/` — **10 archivos Excel, ~97.935 empresas
colombianas** (ISI Markets / WVB). Header en la fila 8 (filas 1–7 son banner/copyright). Columnas:

| Columna | Ejemplo (Grupo Nutresa) | Uso para el informe |
|---|---|---|
| Compañía | `Grupo Nutresa S.A.` | nombre del jugador local |
| Sector (Local) | `Elaboración De Productos Alimenticios` | → mapear a GICS (ver §4) |
| Actividades principales (Local) | idem | actividad / clasificación |
| Total Ingreso Operativo | `20.578.987,8` | tamaño (benchmarking) |
| Ciudad / Estado-Región | `Medellín` / `Antioquia` | foco local (Medellín/Antioquia) |
| Número de empleados | `47.033 (2025)` | tamaño |
| Descripción de la compañía | texto | ficha / contexto |
| Principales Ejecutivos | `Angela María Tafur...` | ficha |
| Activos Totales / Capital Registrado | cifras | tamaño |
| CO-NIT | `890900050` | **clave única** (identidad, dedup) |
| Forma Legal / Estatus Operacional | `S.A.` / `Operacional` | filtros |

Veredicto: **muy relevante como semilla de jugadores locales** (Cap 2 regionales, Cap 4 local,
casos locales). Grupo Nutresa (Alimentos, Medellín) es competidor directo de Alpina y está en el
listado. **No** trae cuota de mercado ni perfil estratégico → complementa el EMIS y la web, no los
reemplaza. Es un **punto de partida**, como dijo el usuario.

### 2.2 Hallazgos de cada informe (acumulación)

Cada corrida identifica competidores/actores (Cap 2, Cap 4). Persistirlos permite que el sistema
"aprenda" y que informes futuros del mismo sector partan de una lista curable.

## 3. Diseño propuesto

### 3.1 Nueva tabla `informes_ic.empresas_directorio`

Distinta de la tabla `empresas` existente (que modela **la empresa analizada** del informe, ver
`EmpresaRepository`). Esta es un **directorio de empresas conocidas** (competidores/jugadores).

| Campo | Tipo | Nota |
|---|---|---|
| `id` | UUID PK | |
| `nombre` | TEXT | razón social |
| `nit` | TEXT UNIQUE NULL | CO-NIT; clave natural de dedup |
| `sector_gics` | TEXT NULL | resuelto por §4 |
| `sector_local` | TEXT NULL | texto original del Excel |
| `ciudad` / `region` | TEXT NULL | foco local |
| `actividad` | TEXT NULL | |
| `descripcion` | TEXT NULL | |
| `ingreso_operativo` / `n_empleados` / `activos` | TEXT/NUM NULL | tamaño |
| `metadatos` | JSONB | ejecutivos, forma legal, ISIN/LEI, ticker, etc. |
| `fuente` | TEXT | `excel_isimarkets` \| `informe` \| `web` \| `manual` |
| `curado` | BOOL default FALSE | **curación humana futura** (el usuario: "todavía no") |
| `curado_por` / `curado_en` | TEXT/timestamp NULL | trazabilidad de curación |
| `creado_en` / `actualizado_en` | timestamp | |

Índices: `nit` (unique parcial), `sector_gics`, y GIN sobre `nombre` (búsqueda). Migración
idempotente al estilo `ensure_*_columns()`.

### 3.2 Flujo de uso (dos ganchos, sin romper el DAG)

1. **Semilla (una vez):** `scripts/seed_empresas_directorio.py` lee los 10 Excel (saltando las
   filas de banner), normaliza y hace upsert por NIT. ~98k filas → correr en tmux/nohup.
2. **Lectura en generación:** antes de la búsqueda web de Cap 2/4, consultar el directorio por
   `sector_gics` (+ ciudad si aplica) y **inyectar como contexto estructurado** una lista de
   jugadores locales (nombre, ciudad, actividad, tamaño). Reduce dependencia de la web y da
   evidencia local citable. RN-001 se respeta: es dato recuperado de una fuente, no del LLM.
3. **Escritura tras generación:** de las entidades identificadas en Cap 2/4, hacer upsert al
   directorio con `fuente="informe"` y `curado=FALSE`. Así el sistema se nutre solo.
4. **Curación (futuro, no ahora):** panel Streamlit para revisar/editar/aprobar (`curado=TRUE`).

### 3.3 Dos formas de consumo (a decidir en Plan Mode)

- **A — Contexto estructurado (recomendado para el directorio):** inyectar la lista al prompt
  (como ya se hace con `{retrieval_*}`). Simple, barato, determinista.
- **B — Chunks RAG:** ingestar `descripcion` como embeddings para recuperación semántica. Más
  costo/ruido; solo si el volumen por sector lo amerita.

## 4. Retos a resolver (Plan Mode)

1. **Mapeo Sector (Local) → GICS.** El Excel trae clasificación colombiana en texto
   ("Elaboración De Productos Alimenticios"), no GICS. Reutilizar `ciiu_gics.py` (CIIU→GICS) si se
   puede derivar CIIU, o construir una tabla de mapeo texto→GICS (revisable). Sin mapeo, el
   directorio no filtra por sector del informe.
2. **Volumen (~98k).** La semilla es masiva; el uso en generación debe filtrar por sector+ciudad y
   limitar (top-N por tamaño) para no inflar el prompt.
3. **Calidad/dedup.** NIT como clave; normalizar nombres; manejar filas con NIT vacío.
4. **Privacidad/ToS.** Datos de ISI Markets/WVB: verificar que se pueden almacenar/usar (mismo
   criterio ADR-013 para resultados de terceros).
5. **No confundir con `EmpresaRepository`** (empresa analizada) ni con `DocumentoLocal` (corpus).

## 5. Relevancia y encaje en el roadmap

- **Relevancia:** ALTA para cerrar la mitad "local" de DT-049 (jugadores locales, casos locales),
  MEDIA en general (no aporta cuota de mercado ni perfil estratégico → complementa EMIS+web).
- **Encaje:** **Fase 23 (Fuentes)** es el hogar natural (misma familia que el corpus EMIS y la
  búsqueda paga). Se propone como **DT-050** con tareas propias (semilla + tabla + lectura/escritura
  + mapeo GICS). La **curación humana** se pospone (panel UI) y puede ir con el HITL (F24/F25).
- **Alternativa:** si se prioriza, puede ser una mini-fase previa a F23 porque el gancho de lectura
  ya mejora Cap 2/4 sin depender de la búsqueda paga.

## 6. Próximo paso sugerido

Aprobar en Plan Mode el alcance mínimo: (a) tabla + migración, (b) script de semilla con mapeo
GICS por NIT/CIIU, (c) gancho de lectura en Cap 2/4 (contexto estructurado), dejando la escritura
automática y la curación para iteraciones siguientes.

## 7. Criterio del usuario (2026-07-24) — a incorporar en el diseño

- **La tabla debe crecer, mejorarse y validarse de forma incremental**, no ser un volcado estático
  del Excel. Se nutre y corrige con las búsquedas que el sistema haga en cada informe.
- **No todas las ~98k empresas merecen citarse como competencia relevante** para la empresa
  analizada: hace falta un criterio de **relevancia/selección** (por sector, tamaño, cercanía
  geográfica, coincidencia de actividad) antes de inyectarlas como competidores. El Excel es
  materia prima, no verdad de competencia.
- **Valor a largo plazo:** este tipo de tabla es un activo para **proyectos futuros** más allá del
  informe actual. Se trabajará **a profundidad más adelante** (no en la fase de hoy).
- Implicación de diseño: separar "directorio bruto" (semilla, todas las empresas) de "candidatos
  de competencia" (subconjunto relevante por informe, con score de relevancia y curación humana).
