# Feature Specification: 007 ? Curaci?n Interactiva HITL y Reconciliaci?n de Entidades por NIT

**Feature Name**: `007-hitl-curacion-reconciliacion-entidades`
**Created**: 2026-09-16
**Status**: Draft
**Priority**: P1 (Core Business & Intelligence Precision)
**Sequence**: Spec 007 (Opci?n A: HITL + Reconciliaci?n) -> Inmediatamente seguido por Spec 008 (Opci?n B: Ingesta Masiva Paralela de PDFs).

---

## 1. Contexto y Justificaci?n de Negocio

El sistema de Inteligencia Competitiva genera informes estructurados a partir de datos curados en el Knowledge Base (KB), corpus documental indexado (EMIS/PDFs) y b?squedas web dirigidas.

Para maximizar la relevancia del an?lisis estrat?gico y evitar "ruido" en el Cap?tulo 2 (Benchmarking) y Cap?tulos N1/N2:
1. **Curaci?n Humana Previa (HITL Pre-Generaci?n)**: El analista debe poder revisar en la interfaz de usuario los competidores candidatos (globales, regionales, startups) identificados para el sector/empresa, descartar aquellos que no sean pertinentes al foco del negocio, agregar competidores espec?ficos y confirmar la lista antes de ejecutar la redacci?n costosa de los cap?tulos.
2. **Reconciliaci?n de Entidades por NIT (`DT-050b`)**: Diversas fuentes (directorio local StartIA, Empresas Colombia, informes EMIS y NER web) han insertado entidades que representan la misma organizaci?n jur?dica o comercial bajo ligeras variantes de nombre (ej. *"ERCO ENERGIA"*, *"ERCO ENERG?A S.A.S."*, *"Erco Energ?a"*). La reconciliaci?n por NIT fusiona estas filas en una entidad can?nica consolidada con sus membres?as y atributos unificados.

---

## 2. Registro Expl?cito de Deuda y Secuenciaci?n (Opci?n A vs Opci?n B)

> [!IMPORTANT]
> **Secuenciaci?n de Roadmap acordada**:
> - **Spec 007 (Este Spec ? Opci?n A)**: Foco en Precisi?n de Negocio y Experiencia del Analista:
>   - Panel Interactivo de Curaci?n y Validaci?n HITL en Streamlit (`src/ic/presentation/views/`).
>   - Algoritmo y script de Reconciliaci?n de Entidades por NIT (`DT-050b`) en `src/ic/data/` y `src/ic/domain/`.
> - **Spec 008 (Pr?ximo Spec ? Opci?n B)**: Foco en Infraestructura y Capacidad de Carga:
>   - Paralelizaci?n de ingesta multi-worker entre archivos PDF (`scripts/ingest_batch.py`).
>   - Enriquecimiento autom?tico de fuentes secundarias para sectores secundarios (DT-UI04e / DT-049).

---

## 3. User Stories y Criterios de Aceptaci?n

### User Story 1 ? Reconciliaci?n Can?nica de Entidades por NIT (`DT-050b`)
**Como** analista de inteligencia competitiva,
**Quiero** que las entidades del KB que comparten el mismo NIT o clave un?voca se fusionen en un ?nico registro can?nico,
**Para** evitar duplicaciones en el anclaje, dispersi?n de atributos y competidores redundantes en el informe.

#### Criterios de Aceptaci?n (US1):
1. **Detecci?n de Duplicados**: Un servicio de reconciliaci?n identifica pares/grupos de entidades con el mismo `nit` (ignorado si NIT es nulo/vac?o o '0').
2. **Selecci?n del Registro Can?nico**: Se preserva el registro con estado m?s alto (`verificado` > `candidato`), mayor n?mero de atributos/menciones o nombre m?s completo.
3. **Fusi?n de Relaciones**:
   - Reasigna `entidad_sectores` y `entidad_atributos` de los duplicados al registro can?nico (con `ON CONFLICT DO NOTHING / UPDATE`).
   - Agrega los nombres variantes de los duplicados a la campo `aliases TEXT[]` (columna en `entidades`; migración `ALTER TABLE` si no existe) de la entidad can?nica.
   - Elimina de forma segura las entidades redundantes hu?rfanas sin romper integridad referencial.
4. **Script de Mantenimiento**: Existe un script ejecutable `scripts/reconciliar_entidades_nit.py` con modo `--dry-run` y `--execute` idempotente.
5. **Migración DDL Previa**: Antes de ejecutar cualquier lógica de fusión, el repositorio aplica `ALTER TABLE entidades ADD COLUMN IF NOT EXISTS aliases TEXT[] DEFAULT '{}'`.

---

### User Story 2 ? Flujo Interactivo de Curaci?n HITL Pre-Generaci?n
**Como** usuario del sistema en Streamlit,
**Quiero** inspeccionar y curar los competidores propuestos antes de que se redacten los cap?tulos completos,
**Para** eliminar empresas que no tengan relaci?n con el negocio y garantizar que el benchmarking sea 100% preciso.

#### Criterios de Aceptaci?n (US2):
1. **Paso 1: Resoluci?n y Descubrimiento Preliminar**: Al ingresar empresa y sector, si la opci?n *"Validaci?n humana previa de competidores"* est? activa, el sistema ejecuta la resoluci?n preliminar (GICS + consulta de KB de candidatos globales, regionales y startups) y presenta la lista interactiva organizada por tiers.
2. **Paso 2: Edici?n y Descarte en UI**:
   - Cada competidor se muestra con su nombre, segmento/tier, origen y bot?n/checkbox para **mantener**, **descartar** o **agregar competidor manual**.
   - El usuario puede desmarcar competidores ruidosos (ej. empresas de software en un informe de l?cteos).
3. **Paso 3: Retroalimentaci?n y Lanzamiento**:
   - Al pulsar *"Confirmar competidores y generar informe"*, la lista curada se inyecta directamente al `InformeParams` / pipeline de generaci?n.
   - Si el usuario marca una entidad como "descartada", queda excluida de `InformeParams` para esta generación únicamente. El estado **no** se persiste en el KB — el analista puede revisar la lista completa en la siguiente corrida.

---

### User Story 3 ? Auditor?a y Feedback Post-Generaci?n en Streamlit
**Como** analista,
**Quiero** visualizar en el visor de historial los competidores anclados que fueron usados en el informe y calificar la relevancia del an?lisis,
**Para** retroalimentar el sistema de calidad continuo.

#### Criterios de Aceptaci?n (US3):
1. En la vista de historial (`view_historial.py`), cada informe muestra el desglose de competidores utilizados por subsecci?n 2.1.
2. Permite registrar feedback r?pido (relevante / con observaciones) que queda guardado en la base de datos de auditor?a.

---

## Clarifications

### Session 2026-09-17

- Q: ¿Los aliases se almacenan en campo JSONB en la tabla `entidades` o en tabla separada? → A: Campo `aliases TEXT[]` o `aliases JSONB` en la tabla `entidades` existente; requiere migración `ALTER TABLE` si la columna no existe aún.
- Q: ¿El descarte HITL persiste en el KB o aplica solo a la sesión actual? → A: Solo sesión — el descarte vive en `st.session_state`; no escribe `estado = 'descartado'` en la BD.
- Q: ¿La columna `aliases` ya existe en la tabla de entidades o requiere migración DDL? → A: No existe aún; T001 debe iniciar con `ALTER TABLE entidades ADD COLUMN aliases TEXT[] DEFAULT '{}'`.
- Q: ¿Cuál es el criterio determinista para seleccionar la entidad canónica entre duplicados de igual estado? → A: Prioridad: estado (`verificado` > `candidato`) → cantidad de atributos → longitud del nombre → `id` mayor como tiebreaker.
- Q: ¿Qué muestra el panel HITL cuando no se encuentran candidatos para el sector/empresa? → A: Panel vacío con mensaje "No se encontraron candidatos en el KB para este sector" + sección de entrada manual activa para que el analista agregue competidores antes de generar.

---

## 4. Invariantes y Restricciones T?cnicas

1. **L?mite de L?neas (Constituci?n I)**: Ning?n archivo en `src/` puede superar las **300 l?neas**. Todos los nuevos m?dulos (`view_hitl.py`, `reconciliacion.py`, etc.) deben dise?arse de forma modular.
2. **Calidad y Cobertura**: 100% de los tests unitarios e integraci?n pasando; 0 errores de `ruff`.
3. **Tono y Lenguaje**: Espa?ol neutro corporativo (`es-CO`), sin lenguaje imperativo en UI o prompts (RN-007).
4. **Idempotencia**: Cualquier acci?n de curaci?n o reconciliaci?n en base de datos debe ser segura e idempotente.
