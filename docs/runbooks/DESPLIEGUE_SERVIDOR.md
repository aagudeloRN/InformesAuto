# Runbook — Despliegue en Servidor Local

> **Propósito:** dejar la UI Streamlit corriendo como servicio en el servidor local, reusando los
> servicios compartidos (Postgres+pgvector y Ollama) sin chocar con las otras apps del servidor.
>
> **Primer despliegue:** 2026-08-06 (DT-UI04b + estilo). Servidor `192.168.0.99`, UI en `:8503`.

---

## 1. Arquitectura del despliegue

- **UI:** contenedor `informesauto_streamlit` (imagen `informesauto-streamlit`, `Dockerfile.streamlit`),
  publica **`0.0.0.0:8503`** (LAN privada; Streamlit sin auth — aceptable en red de confianza).
- **BD (TIER-1, esquema dedicado en instancia compartida):** Postgres+pgvector
  `repositorio_postgres_server` (red externa `repositoriorn_repositorio_network`), db
  `repositorio_ctie`, esquema **`informes_ic`**. NO se levanta un Postgres propio.
- **Ollama:** corre en el **host** del servidor (`:11434`, con `nomic-embed-text`); el contenedor lo
  alcanza por `host.docker.internal` (mapeado a `host-gateway` vía `extra_hosts`).
- **Compose:** `docker-compose.server.yml` (solo el servicio `streamlit`; el `postgres` del
  `docker-compose.yml` de dev NO se usa aquí).

Puertos ya ocupados en el servidor (no tocar): 3000/3002/3005/3006, 5432/5433/5435, 6379,
8000/8001/8002/8005/8080, 9090, 11434/11435. **8503 quedó para InformesAuto.**

## 2. Primer despliegue (pasos ejecutados)

Todo desde la máquina de dev vía SSH (`n8n@192.168.0.99`). Secretos: solo en el `.env` del
servidor (nunca a git).

1. **Migrar el KB** (esquema `informes_ic`, ~500 MB / dump ~124 MB):
   ```bash
   # en dev: dump del esquema desde el Postgres compartido de dev (5434)
   docker exec -e PGPASSWORD=<pass> repositorio_postgres \
     pg_dump -U repositorio_user -d repositorio_ctie -n informes_ic -Fc -Z6 > /tmp/ic_kb.dump
   scp /tmp/ic_kb.dump n8n@192.168.0.99:/tmp/
   # en server: pgvector ya instalado; restaurar (crea el esquema, aislado de repositorio)
   docker cp /tmp/ic_kb.dump repositorio_postgres_server:/tmp/ic_kb.dump
   docker exec -e PGPASSWORD=<pass> repositorio_postgres_server \
     pg_restore -U repositorio_user -d repositorio_ctie --no-owner --no-privileges /tmp/ic_kb.dump
   ```
2. **Código al servidor** (`~/InformesAuto`) por rsync. ⚠️ **Excludes ANCLADOS con `/`** para no
   excluir la capa de código `src/ic/data/` con el patrón del `data/` de Postgres:
   ```bash
   rsync -az --delete \
     --exclude '/.git' --exclude '/.venv' --exclude '/output/' --exclude '/data/' \
     --exclude '/logs/' --exclude '__pycache__/' --exclude '/.env' \
     --exclude '/documentos_sectoriales/FuentesEMIS' --exclude '*.pdf' --exclude '*.docx' \
     ./ n8n@192.168.0.99:~/InformesAuto/
   ```
   (Un `--exclude 'data/'` SIN `/` inicial también borra `src/ic/data/` → el contenedor arranca
   pero falla `import ic.data`. Anclar siempre.)
3. **`.env` del servidor:** copiar el de dev y reescribir solo el host de la BD y Ollama:
   ```bash
   scp .env n8n@192.168.0.99:~/InformesAuto/.env
   ssh n8n@192.168.0.99 'cd ~/InformesAuto
     sed -i -E "s#@localhost:5434/#@repositorio_postgres_server:5432/#" .env
     sed -i -E "s#^OLLAMA_BASE_URL=.*#OLLAMA_BASE_URL=http://host.docker.internal:11434#" .env
     chmod 600 .env'
   ```
   (Mantiene API keys, `DB_SCHEMA=informes_ic`, `STREAMLIT_PORT=8503` y los flags
   `ANCLAJE_LOCAL_ENABLED`/`SECCION21_DETERMINISTA_ENABLED`/`DISCOVER_GLOBALES_ENABLED`.)
4. **Build + up:**
   ```bash
   ssh n8n@192.168.0.99 'cd ~/InformesAuto && docker compose -f docker-compose.server.yml up -d --build'
   ```

## 3. Verificación

```bash
docker ps --filter name=informesauto_streamlit           # Up (healthy)
curl -s -o /dev/null -w '%{http_code}' http://192.168.0.99:8503/_stcore/health   # 200
# BD + CSV + Ollama desde el contenedor (la app importa desde /app/src, no del wheel):
docker exec -w /app informesauto_streamlit uv run python -c "import sys; sys.path.insert(0,'/app/src');
from ic.data.database import SessionLocal; from sqlalchemy import text
from ic.shared.constants.ciiu_gics import sectores_ancla_local
print(sectores_ancla_local('1010','3511'))
print(SessionLocal().execute(text('select count(*) from informes_ic.entidades')).scalar())"
```

## 4. Actualizar el despliegue (nueva versión)

```bash
# dev: rsync (excludes anclados) → server ; luego:
ssh n8n@192.168.0.99 'cd ~/InformesAuto && docker compose -f docker-compose.server.yml up -d --build'
```
Migrar cambios de KB re-corriendo el dump/restore del §2.1 (o los scripts de siembra en el server).

## 5. Sembrar los .docx de casos de estudio (historial)

El historial (`informes_ic.historial_informes.ruta_documento_final`) referencia rutas como
`./output/<empresa>_informe.docx` (relativas a `/app`). Para que la UI del servidor los abra, los
`.docx` deben existir en `~/InformesAuto/output/` (bind mount → `/app/output`).

⚠️ **`output/` en el servidor es root** (lo creó el docker daemon), así que `rsync`/`scp` como `n8n`
falla con *Permission denied*. Sembrar vía `docker cp` (escribe en el bind mount con privilegios del
daemon):
```bash
# dev → stage escribible en el servidor → dentro del contenedor
rsync -az output/*.docx n8n@192.168.0.99:/tmp/ic_docx/
ssh n8n@192.168.0.99 'docker cp /tmp/ic_docx/. informesauto_streamlit:/app/output/ && rm -rf /tmp/ic_docx'
```
(Nombres con acento como `erco_energía_sas_informe.docx` se copian bien; deben coincidir EXACTO con
`ruta_documento_final` del historial.)

## 6. Modelos: la generación usa la NUBE, no el Ollama del servidor

El servidor **no tiene GPU** (Ollama lento). Configuración de routing (`.env`) para que la redacción
NO caiga en local: `LLM_API_FREE_MODEL` (openrouter/Nemotron) como `api_llm`, `LLM_API_SYNTH_MODEL`
(Gemini) para síntesis, fallback openrouter. El Ollama del host **solo** se usa para **embeddings**
(`nomic-embed-text`, barato en CPU). Los modelos locales (`qwen3`/`llama3.2`) solo actuarían si TODA
la nube fallara (degradaría mucho la UX — evitar quedarse sin cuota de API).

## 7. Deuda / notas

- **El wheel `ic` instalado por `uv sync` queda incompleto**; la app funciona porque `app.py`
  inserta `src/` en `sys.path`. Cualquier `uv run python -c "import ic.data"` sin `sys.path`
  falla — usar `sys.path.insert(0,'/app/src')` para diagnósticos. (Revisar el packaging del
  `pyproject.toml` en el futuro.)
- **`documentos_sectoriales/FuentesExternas/CatalogoVerticalesStartIAGICS.csv`** está *untracked* en
  git; solo lo usa la ingesta (`ingest/startia.py`), no la generación, por lo que el contenedor no
  lo necesita. Si se dockeriza la ingesta, trackearlo o copiarlo.
- **Sin auth en Streamlit:** válido en LAN privada; si se expone fuera, poner reverse proxy con auth.
- **Disco del servidor** ~84% al desplegar (huella ~2 GB: BD ~500 MB + imagen ~1.5 GB). Ampliar.
