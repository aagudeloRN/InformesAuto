# Hallazgos y decisiones operativas — Fase 4

**Fecha:** 2026-06-25  
**Alcance:** Ensamblado .docx + Citación APA 7 + Ingesta PDF  
**Tests al cierre:** 27/27 pasando

---

## H4-01: Los metadatos APA deben viajar desde el conector, no extraerse post-facto

**Contexto:** Al diseñar el formatter APA, se detectó que `ChunkResult.metadatos`
era `None` en todos los chunks provenientes de `WebConnector`, porque el conector
solo almacenaba `fuente_url` y `contenido`. Sin `{titulo, fuente_nombre, año}` no
se puede producir una cita APA correcta.

**Decisión:** Los metadatos APA se construyen **en el momento de la búsqueda web**
(`_build_metadatos()` en `web_connector.py`) y se propagan hasta el JSONB de
`EmbeddingVectorial` via `metadatos_extra`. Esto mantiene la trazabilidad completa
desde el chunk hasta la referencia impresa en el .docx.

**Implicación para Fase 5:** Los conectores nuevos (OpenAlex, arXiv, Crossref) deben
seguir el mismo patrón: llenar `metadatos_extra` con al menos
`{titulo, fuente_nombre, año, autor, url}` en el momento de la ingesta.

---

## H4-02: `chunks_usados` en el DTO evita re-query innecesario

**Contexto:** El assembler necesita construir la sección de referencias a partir de
los chunks que el LLM efectivamente consultó. Las alternativas consideradas:
1. Re-hacer la query vectorial en el assembler (duplica trabajo, puede dar resultados distintos).
2. Guardar IDs y releer de BD (acoplamiento al repositorio en el dominio).
3. Transportar los chunks en el DTO (zero acoplamiento extra).

**Decisión:** Opción 3: `CapBenchmarking.chunks_usados: list[ChunkResult]` — el use
case llena el campo antes de retornar. El assembler lo consume directamente.

**Implicación para Fase 5:** Todos los DTOs de capítulos N1 deben incluir
`chunks_usados`. El DAG orquestador los pasa todos al assembler final.

---

## H4-03: DocxBuilder no parsea Markdown completo — regex simple es suficiente para el piloto

**Contexto:** Los LLMs devuelven Markdown. Se evaluaron:
- `markdown2` / `mistune` → conversor Markdown→HTML, luego HTML→docx (muy complejo).
- `pypandoc` → requiere pandoc instalado en el sistema.
- Regex sobre los patrones que realmente usa el modelo (`##`, `**…**`, `- `) → simple y suficiente.

**Decisión:** Regex simple en `DocxBuilder.add_markdown_section()`. Solo convierte:
`##`→Heading, `**text**`→bold run, `- `→List Bullet. Cualquier Markdown más complejo
(tablas, código, imágenes) pasa como texto plano sin error.

**Límite conocido:** Las tablas Markdown del LLM pasan como texto. Si en Fase 5 el
modelo genera tablas comparativas (Cap 3 tendencias, Cap 4 ecosistema), habrá que
añadir conversión de tabla a `DocxBuilder` o pedir al LLM que no use tablas Markdown.

---

## H4-04: La plantilla .dotx es opcional — el builder tiene fallback limpio

**Contexto:** La plantilla membrete corporativa tiene datos de la empresa cliente y
no debe ir al repositorio. Se necesitaba un comportamiento seguro cuando la plantilla
no existe.

**Decisión:** `DocxBuilder.__init__` comprueba `os.path.exists(template_path)` antes
de cargar. Si falla (ruta vacía o archivo ausente), crea un `Document()` limpio.
La ruta se configura via `DOCX_TEMPLATE_PATH` en `.env`.

**Cómo configurar para Fase 5:** Copiar `011 Hoja membreteESP.dotx` a
`assets/plantilla_membrete.dotx` (carpeta en `.gitignore`) y añadir al `.env`:
```env
DOCX_TEMPLATE_PATH=assets/plantilla_membrete.dotx
```

---

## H4-05: `ingest_pdf.py` aplica su propia migración de columna

**Contexto:** El modelo ORM `DocumentoLocal` necesitaba `metadatos JSONB` para
guardar el SHA-256. El proyecto no usa Alembic; el schema se gestiona con `create_all`.

**Decisión:** `ingest_pdf.py` ejecuta `ALTER TABLE … ADD COLUMN IF NOT EXISTS` al
arrancar. Es idempotente: si la columna ya existe, no falla. No se toca `create_schema.py`
para no acoplar el script de inicialización a Fase 4.

**Deuda técnica:** Si en Fase 5 se añaden más columnas a modelos existentes, evaluar
si conviene introducir Alembic o seguir con el patrón de migraciones en script.

---

## H4-06: Prompt-00 queda fuera de Fase 4

**Contexto original:** Prompt-00 (generación de ecuaciones de búsqueda para cada
canal: OpenAlex, arXiv, Crossref, web) estaba planificado en Fase 4 pero es
lógica de orquestación del DAG, no de ensamblado.

**Decisión:** Se mueve a Fase 5 junto con los capítulos N1 restantes.
Prompt-00 debe ejecutarse antes de los capítulos N1 (forma parte del nivel N0).
