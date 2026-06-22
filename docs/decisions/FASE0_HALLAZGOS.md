# Hallazgos de Fase 0 — Andamiaje

**Fecha:** 2026-06-22  
**Fase:** 0 — Andamiaje (Docker + BD + modelos ORM)

Registro de decisiones operativas y hallazgos imprevistos durante la ejecución de
Fase 0 que afectan fases siguientes.

---

## 1. Instancia PostgreSQL compartida ya corriendo

**Hallazgo:** Al intentar `docker compose up -d`, el puerto 5434 ya estaba ocupado por
el contenedor `repositorio_postgres` (`pgvector/pgvector:pg16`), que es la instancia
compartida del entorno de desarrollo del host.

**Credenciales del entorno:**
```
POSTGRES_USER=repositorio_user
POSTGRES_DB=repositorio_ctie
Host: localhost:5434
```

**Decisión tomada:** Se conectó directamente a la instancia compartida existente. El
`docker-compose.yml` creado en este proyecto sigue siendo útil para entornos sin
instancia compartida (CI, nuevos desarrolladores), pero en el entorno de trabajo actual
**no se levanta**: el `.env` apunta a `repositorio_ctie`.

**Impacto en Fase 2+:** El esquema `informes_ic` existe dentro de `repositorio_ctie`.
Los tests y scripts que conectan a BD deben tener un `.env` con las credenciales reales
del shared instance. El `docker-compose.yml` del repo actúa como fallback documentado.

---

## 2. Bug: `repr()` en `StrEnum` para `CheckConstraint`

**Hallazgo:** Al construir `CheckConstraint` con:
```python
f"tipo IN ({', '.join(repr(v) for v in TipoDocumento)})"
```
SQLAlchemy genera SQL inválido: `tipo IN (<TipoDocumento.PDF_SECTORIAL: 'pdf_sectorial'>...)`.

**Fix aplicado:** Usar `.value`:
```python
f"tipo IN ({', '.join(repr(v.value) for v in TipoDocumento)})"
```
Esto genera: `tipo IN ('pdf_sectorial', 'informe_emis', 'otro')` — SQL válido.

**Aplica a:** Todo `CheckConstraint` que itere sobre `StrEnum` en los modelos ORM.

---

## 3. Dimensión de embeddings confirmada: 768

`nomic-embed-text:latest` produce vectores de 768 dimensiones. La columna
`embedding VECTOR(768)` en `embeddings_vectoriales` está alineada con este valor.

**Impacto en Fase 2:** El pipeline de ingesta debe generar embeddings con
`nomic-embed-text` (configurado en `LLM_LOCAL_EMBED_MODEL` en `.env`) y pasar
exactamente 768 floats al insertar en `embeddings_vectoriales`. Si se cambia de modelo
de embeddings, hay que migrar la columna.

---

## 4. Sin Alembic en Fase 0

**Decisión:** Se usa `Base.metadata.create_all()` vía `scripts/create_schema.py`
en lugar de Alembic.

**Razón:** El esquema cambiará durante el piloto (Fases 2–5). Alembic agrega fricción
de autogeneración de migraciones en cada cambio de modelo mientras el schema es
inestable. Se agrega cuando el schema se estabilice (post-piloto o antes de Fase 6).

**Procedimiento de cambio de schema mientras no haya Alembic:**
1. Modificar el modelo ORM.
2. Bajar el contenedor / conectarse a la BD y `DROP TABLE` de las afectadas (si en dev).
3. Re-ejecutar `uv run python scripts/create_schema.py`.

---

## 5. Estado de tablas creadas (verificado)

```
informes_ic.empresas                ✓
informes_ic.historial_informes      ✓
informes_ic.documentos_locales      ✓
informes_ic.embeddings_vectoriales  ✓ (VECTOR(768), extensión pgvector activa)
```

4 smoke tests pasando (`tests/test_database.py`).
