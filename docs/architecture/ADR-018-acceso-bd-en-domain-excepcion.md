# ADR-018 — Acceso a BD desde `domain/`: excepción tolerada

**Fecha:** 2026-10-26
**Estado:** Aprobado
**Origen:** `/speckit-analyze` de la spec 008 (hallazgo C2)

---

## Contexto

La Constitución I dice que ningún archivo mezcla lógica de negocio con acceso a BD y que las
capas solo dependen hacia abajo. En la práctica, 13 archivos de `src/ic/domain/` importan
`SessionLocal` (la fábrica de sesiones de SQLAlchemy), entre ellos `use_cases/auto_enrich.py`
(spec 008). Este último también construye `EmbeddingVectorial` (modelo de la tabla).

El SQL en sí no vive en `domain/`: lo ejecutan los repositorios de `data/`
(`EmbeddingRepository`, `EmbeddingEstadoRepository`). Lo que `domain/` hace es abrir la sesión.

## Decisión

Se **tolera** esta excepción de forma temporal:

1. Los casos de uso existentes pueden abrir `SessionLocal` y pasarla a un repositorio.
2. Ningún caso de uso nuevo debe escribir SQL ni importar `sqlalchemy` directamente.
3. Para casos de uso nuevos, preferir recibir la sesión o el repositorio ya construido.
4. La corrección definitiva (mover la apertura de sesión a `data/` o `infrastructure/`) se
   hará en una spec de refactor aparte, no dentro de la 008.

## Consecuencias

- El Constitution Check de la spec 008 pasa de "PASS con excepción conocida" a
  "EXCEPCIÓN DOCUMENTADA (ADR-018)".
- La deuda queda visible en `docs/architecture/ROADMAP.md` (Deudas pendientes).
- Si se decide enmendar la Constitución en lugar de refactorizar, requiere PR con incremento
  de versión, como indica su sección Governance.
