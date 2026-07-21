# ADR-011 — Modelo de documento intermedio y motor PDF

**Fecha:** 2026-07-21
**Estado:** Aprobado
**Fase:** 11

---

## Contexto

Hasta Fase 10, `assembler.py` (en `domain/`) importaba `DocxBuilder` de `infrastructure/`,
violando Dependency Agnosticism (PRIME DIRECTIVE §1.2). El `.docx` resultante era plano:
solo headings, viñetas y negrita, sin TOC, sin paginación, sin tablas Word, sin figuras.
No existía salida en PDF.

---

## Decisión

### 1. Modelo de documento intermedio

Introducir `domain/report_model.py` con bloques semánticos **inmutables** (`frozen=True`):

```
Heading, Paragraph, TableBlock, FigureBlock, CitationBlock, Callout, PageBreak, Toc
→ DocumentBlock (union type)
→ ReportDocument (contenedor con title, company, date, blocks, disclaimer)
```

`PilotAssembler` (domain) construye el `ReportDocument` usando `parse_markdown()` para
convertir el texto de las chains. No importa python-docx ni matplotlib.

### 2. Renderers en infrastructure/render/

```
infrastructure/render/docx_renderer.py   → python-docx (master editable)
infrastructure/render/pdf_renderer.py   → LibreOffice headless
```

La cadena es: `InformePiloto → ReportDocument → DocxRenderer → .docx → pdf_renderer → .pdf`

### 3. Motor PDF: LibreOffice headless

Disponible en el entorno (`/usr/bin/soffice`). Convierte el `.docx` master a PDF con
`soffice --headless --convert-to pdf`. Una única fuente de verdad de estilo (la plantilla
membrete en .docx) produce ambos formatos.

Alternativas descartadas:
- **WeasyPrint**: requeriría mantener un tercer renderer HTML→PDF con su propia hoja de estilos
  (dos fuentes de verdad para el formato visual).
- **docx2pdf**: solo disponible en macOS/Windows; no funciona en WSL2.

### 4. Charts en infrastructure/charts/

`infrastructure/charts/radar_chart.py` usa matplotlib (importado solo aquí). El orchestrator
genera la imagen PNG y pasa la ruta al assembler como `figura_benchmarking`. El domain
solo recibe un `str` (ruta), nunca matplotlib.

---

## Consecuencias

**Positivas:**
- `domain/` libre de python-docx y matplotlib (PRIME DIRECTIVE §1.2 satisfecho).
- Múltiples formatos posibles desde el mismo modelo (`ReportDocument`).
- Markdown inline (`*italic*`, `**bold**`, `|tabla|`) se renderiza correctamente en Word.
- Referencias APA con sangría francesa y marcadores `*cursiva*` (Fase 10) convertidos a italic.
- Callouts visuales para datos ausentes y accionables.
- Botón de descarga PDF en la UI Streamlit.

**Negativas / deuda:**
- LibreOffice headless añade ~5–15 s al tiempo de generación.
- El TOC generado requiere "Actualizar campos" en Word la primera vez que se abre el documento.
- Los datos del radar chart son placeholder (5 competidores × 5 dimensiones fijas). Datos
  estructurados desde LLM quedan para fases futuras (DT-019).

---

## Archivos creados / modificados

| Archivo | Acción |
|---------|--------|
| `src/ic/domain/report_model.py` | nuevo |
| `src/ic/domain/markdown_parser.py` | nuevo |
| `src/ic/infrastructure/render/docx_renderer.py` | nuevo |
| `src/ic/infrastructure/render/pdf_renderer.py` | nuevo |
| `src/ic/infrastructure/charts/radar_chart.py` | nuevo |
| `src/ic/domain/assembler.py` | refactorizado (elimina DocxBuilder dep) |
| `src/ic/domain/use_cases/generate_informe.py` | wiring nuevo pipeline |
| `src/ic/shared/types.py` | `tabla_data` en `CapBenchmarking` |
| `src/ic/presentation/app.py` | botón descarga PDF |
