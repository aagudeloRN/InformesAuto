"""Convierte texto markdown de chains a lista de bloques del modelo de documento.

Función pura — sin imports de infraestructura. Los marcadores inline
(**bold**, *italic*) se preservan en el texto; el renderer los interpreta.
"""

import re

from ic.domain.report_model import (
    DocumentBlock,
    Heading,
    Paragraph,
    TableBlock,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
_TABLE_SEP_RE = re.compile(r"^\|[\s\-|:]+\|$")


def parse_markdown(text: str) -> list[DocumentBlock]:
    """Convierte markdown a bloques semánticos."""
    lines = text.splitlines()
    blocks: list[DocumentBlock] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Heading
        m = _HEADING_RE.match(line)
        if m:
            level = min(len(m.group(1)), 4)
            blocks.append(Heading(text=m.group(2).strip(), level=level))
            i += 1
            continue

        # Markdown table — consume cabecera + separador + filas
        if _TABLE_ROW_RE.match(line.strip()):
            table_lines = [line]
            j = i + 1
            while j < len(lines) and _TABLE_ROW_RE.match(lines[j].strip()):
                table_lines.append(lines[j])
                j += 1
            block = _parse_table(table_lines)
            if block is not None:
                blocks.append(block)
            i = j
            continue

        # Bullet list
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            item_text = stripped[2:].strip()
            blocks.append(Paragraph(text=item_text, style="List Bullet"))
            i += 1
            continue

        # Blank line — skip
        if not stripped:
            i += 1
            continue

        # Normal paragraph
        blocks.append(Paragraph(text=stripped))
        i += 1

    return blocks


def _parse_table(table_lines: list[str]) -> TableBlock | None:
    """Devuelve TableBlock a partir de líneas de tabla markdown, o None si inválida."""
    # Filtra línea separadora (solo guiones)
    data_lines = [ln for ln in table_lines if not _TABLE_SEP_RE.match(ln.strip())]
    if len(data_lines) < 1:
        return None

    def _split(line: str) -> tuple[str, ...]:
        return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))

    header_row = _split(data_lines[0])
    rows = tuple(_split(ln) for ln in data_lines[1:])
    return TableBlock(headers=header_row, rows=rows)
