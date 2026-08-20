# Research: Cap 2.1 — Activar Sub-módulos Modulares y Numeración de Secciones

**Date**: 2026-08-20 | **Feature**: 003-cap21-activar-submodulos

## Decision 1: Thread-safety de Generate21Startups

**Decision**: Modificar `Generate21Startups.__init__` para aceptar `db_factory: Callable | None = None` como alternativa al `entidad_repo` existente.

**Rationale**: `Generate21Jugadores.execute()` invoca los tres sub-módulos en un `ThreadPoolExecutor`. Las sesiones SQLAlchemy no son thread-safe. El bloque `with SessionLocal() as db_kb:` en `_fn_cap2` cierra la sesión antes de que el `ThreadPoolExecutor` arranque el thread. Pasar un factory (callable) permite a `Generate21Startups.execute()` abrir su propia sesión fresca en el contexto del thread correcto.

**Alternatives considered**:
- Pre-fetch en `_fn_cap2` y pasar `list[LocalRow]` directamente: requeriría cambiar `Generate21Jugadores.execute()` también.
- Inyección por `execute()`: rompe el patrón de dependency injection de la clase.
- `scoped_session` de SQLAlchemy: agrega complejidad de configuración global.

**Backward compatibility**: El parámetro `entidad_repo` sigue disponible. Los tests existentes que inyectan `_FakeEntidadRepo` continúan funcionando sin cambios.

---

## Decision 2: Fuente del engine en generate_n1.py

**Decision**: Importar `engine` de `ic.data.database` de forma lazy dentro del body de `_fn_cap2`, exactamente igual al patrón ya existente en `generate_informe.py` (línea 415: `from ic.data.database import SessionLocal, engine`).

**Rationale**: `_PipelineContext` no expone `engine` como atributo (solo `run_key`). El `engine` es un singleton de módulo exportado por `ic.data.database`. No hay riesgo de múltiples instancias.

**Alternatives considered**: Agregar `engine` a `_PipelineContext`: requeriría modificar el dataclass y todos sus callers. No justificado para este scope.

---

## Decision 3: Valor de sub_gics para el cache key

**Decision**: Pasar `sub_gics=g_code` a `GenerateBenchmarking`. El `g_code` es el código GICS del grupo (ej. `"3020"` para Food Products), suficientemente granular para aislar caches por sector.

**Rationale**: La clave sectorial resultante es `f"sector_{g_code}_{g_code}"`. Esto es redundante pero funcional — en una corrida típica `sector_gics_code` en `execute()` y `sub_gics` del constructor son el mismo valor. La granularidad a sub-industria (ej. `"30201010"`) requeriría que el pipeline exponga el sub-código, que no está disponible actualmente.

**Alternatives considered**: Pasar `sub_gics=None` → clave `f"sector_{g_code}_any"` → mismo resultado; la redundancia con `sub_gics=g_code` no perjudica la funcionalidad.

---

## Decision 4: Verificación de chain builders disponibles

**Finding**: Los chain builders para los sub-módulos ya existen en `src/ic/domain/chains/`:
- `chain_cap2_21_globales.py` → `build_chain_cap2_21_globales(llm)`
- `chain_cap2_21_regionales.py` → `build_chain_cap2_21_regionales(llm)`
- `chain_cap2_21_startups.py` → `build_chain_cap2_21_startups(llm)`
- `chain_02c_pares_globales.py` → `build_chain_pares_globales(llm)` (candidatos globales para `Generate21Globales`)

**Conclusion**: No se requiere crear nuevos chain builders. Solo hay que importarlos.

---

## Decision 5: Candidatos chain para Generate21Globales

**Finding**: `Generate21Globales.__init__` requiere `chain_candidatos` y `chain_perfil`. El primero propone nombres de candidatos (LLM libre), el segundo redacta el perfil por candidato.
- `chain_candidatos` → `build_chain_pares_globales(llm)` (ya usado en `DiscoverGlobales`)
- `chain_perfil` → `build_chain_cap2_21_globales(llm)` (nuevo chain dedicado)

**Confirmation**: `build_chain_pares_globales` está importado en el cuerpo de `run_n1_parallel` (línea ~36 del archivo). Reutilizar la misma importación lazy.
