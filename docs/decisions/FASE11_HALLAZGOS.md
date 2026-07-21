# Hallazgos Técnicos — Fase 11

**Fecha:** 2026-07-21
**Rama:** feature/fase11-formato-documento
**Tests fast:** 162 passed, 2 skipped
**Ruff:** 0 errores

---

## Objetivos de la fase

1. **T11.1** — Modelo de documento intermedio (`domain/report_model.py`)
2. **T11.2** — `infrastructure/render/docx_renderer.py`: portada, TOC, paginación, cursivas APA,
   tablas, figuras, callouts. Refactor `assembler.py` para eliminar dependencia de `DocxBuilder`.
3. **T11.3** — Tablas reales en Cap 2: `markdown_parser.py` convierte `|col|col|` → `TableBlock`
4. **T11.4** — Figura (radar chart): `infrastructure/charts/radar_chart.py` (matplotlib aislado)
5. **T11.5** — PDF: `infrastructure/render/pdf_renderer.py` (LibreOffice headless)
6. **T11.7** — Callouts para datos ausentes y accionables

---

## H11-01 — Modelo de documento: frozen dataclasses con listas

**Problema:** `frozen=True` en dataclasses con campos `list` genera `TypeError: unhashable type`
si se intenta hashear el objeto. Para `TableBlock` (que tiene `headers` y `rows`), se optó por
`tuple[str, ...]` en vez de `list[str]` para hacer los bloques completamente inmutables y
hashables sin excepción en runtime.

**Decisión:** Los 8 tipos de bloque usan `frozen=True`. `TableBlock` usa tuples para headers/rows.
`ReportDocument` (el contenedor) usa `@dataclass` sin frozen (su lista de bloques puede crecer
durante la construcción en el assembler).

**Archivos:** `src/ic/domain/report_model.py`

---

## H11-02 — Markdown parser: tablas detectadas por líneas `| col |`

**Problema:** Las chains de Cap 2 emiten texto con fichas markdown (headers `##`, bullets `-`).
El parser debía detectar tablas `|col|col|` si el LLM las producía, sin cambiar el prompt.

**Solución:** `parse_markdown()` usa regex `^\|(.+)\|$` para detectar líneas de tabla y las
consume en bloque (cabecera + separador + filas). El separador (`|---|---|`) se detecta por
`^\|[\s\-|:]+\|$` y se omite. El resultado es un `TableBlock` con `headers` y `rows`.

**Uso real:** La sección 2.1 de chain_03 produce fichas en prosa (no tablas markdown), pero la
sección 2.2 puede producir una tabla de posicionamiento. El parser las captura automáticamente
sin modificar los prompts.

**Archivos:** `src/ic/domain/markdown_parser.py`

---

## H11-03 — Cursivas APA: marcadores `*texto*` funcionan con inline parser

**Problema:** Los marcadores `*cursiva*` emitidos por `apa_formatter.py` en Fase 10 debían
convertirse a italic runs en Word. El renderer inline usa `re.split(r"(\*\*.+?\*\*|\*.+?\*)")` 
para alternar entre bold (`**`), italic (`*`) y texto plano.

**Tradeoff:** El regex es greedy dentro del marcador pero no entre marcadores. Esto significa
que `*título con * asterisco*` puede confundir el parser. En la práctica, los strings APA
no contienen asteriscos literales dentro del texto cursivado.

**Archivos:** `src/ic/infrastructure/render/docx_renderer.py` (`_add_inline_text`)

---

## H11-04 — TOC requiere "Actualizar campos" en Word al abrir

**Problema:** `python-docx` inserta el campo `TOC` como instrucción XML (`w:fldChar` +
`w:instrText`), pero no pre-renderiza las entradas. Word las genera la primera vez que
el usuario abre el archivo y acepta "Actualizar campos".

**Decisión:** Comportamiento aceptado y documentado. Es el comportamiento estándar de
python-docx para TOC — la alternativa (libreoffice headless + macro) añade complejidad
sin beneficio práctico dado que el analista edita el docx antes de distribuirlo.

**Archivos:** `src/ic/infrastructure/render/docx_renderer.py` (`_add_toc_field`)

---

## H11-05 — Radar chart: matplotlib Agg backend obligatorio en WSL2

**Problema:** WSL2 sin display. matplotlib levanta `RuntimeError: Invalid DISPLAY variable`
con el backend por defecto (TkAgg).

**Solución:** `matplotlib.use("Agg")` en el módulo `radar_chart.py` antes de cualquier
import de `matplotlib.pyplot`. El backend Agg renderiza a buffer en memoria y guarda PNG
sin necesidad de pantalla.

**Regla derivada:** Todo módulo que use matplotlib en este proyecto debe llamar
`matplotlib.use("Agg")` al inicio (no confiar en la variable de entorno MPLBACKEND).

**Archivos:** `src/ic/infrastructure/charts/radar_chart.py`

---

## H11-06 — PDF con LibreOffice headless: tiempo ~5–15 s adicionales

**Decisión:** Se eligió LibreOffice headless (`soffice --headless --convert-to pdf`) sobre
WeasyPrint y docx2pdf. WeasyPrint requeriría un tercer renderer HTML con su propia CSS.
docx2pdf no funciona en Linux. LibreOffice ya estaba instalado (`/usr/bin/soffice`).

**Riesgo aceptado:** El proceso `soffice` puede tardar 5–15 s y tiene un timeout de 60 s.
El PDF se genera después del docx; si falla, se loguea warning y el sistema devuelve solo el docx
(el campo `ruta_pdf` de `InformeResult` queda `None`). El usuario aún puede descargar el docx.

**Archivos:** `src/ic/infrastructure/render/pdf_renderer.py`,
`src/ic/domain/use_cases/generate_informe.py`

---

## H11-07 — Dependency Agnosticism restaurado en assembler

**Problema original:** `assembler.py` (en `domain/`) importaba `DocxBuilder` de `infrastructure/`,
violando PRIME DIRECTIVE §1.2.

**Solución:** `PilotAssembler` ya no recibe un `DocxBuilder`. El método público es ahora
`build(informe, figura_benchmarking) -> ReportDocument`. El orchestrator
(`generate_informe._run_n3`) crea el `DocxRenderer` (infrastructure) y lo llama con el
`ReportDocument` (domain). El `DocxBuilder` original se conserva en `infrastructure/`
(sus tests directos siguen pasando).

**Archivos:** `src/ic/domain/assembler.py`, `src/ic/domain/use_cases/generate_informe.py`

---

## Estado de deuda técnica al cierre de Fase 11

| ID | Descripción | Estado |
|----|-------------|--------|
| DT-004 | `generate_informe.py` ≥300 líneas | 🟡 400 L → separar en Fase 12 (T12.5) |
| DT-015 | APA 7 no fiel | ✅ Cerrado Fase 10 |
| DT-016 | Formato .docx pobre | ✅ Cerrado — portada, TOC, tablas, figuras, PDF |
| DT-017 | Footer/disclaimer hardcodeado | ✅ Cerrado Fase 10 |
| DT-018 | Hook check-ruff.sh en settings.json | 🟡 Parcial — pendiente acción manual |
| DT-019 | Datos estructurados radar chart desde LLM | ⬜ Fase 12 o posterior |

---

## Próximos pasos (Fase 12)

Ver `docs/architecture/ROADMAP_FASE9+.md` sección "FASE 12".

**Prioridades candidatas:**
1. Extraer `_run_n1` de `generate_informe.py` a `use_cases/generate_n1.py` (cierra DT-004)
2. Datos estructurados desde chain_03 para radar chart real (cierra DT-019)
3. Preview HTML del informe en la UI
4. Exportar a Google Drive / email (Fase 13)
