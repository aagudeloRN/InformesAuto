"""Wrapper de lectura de Excel (openpyxl) — Dependency Agnosticism (CLAUDE.md TIER 1, regla 5).

El resto de la app (scripts de ingesta DT-050) depende de este wrapper, no de openpyxl. Lee en modo
``read_only`` (streaming, apto para los ~98k registros de EmpresasColombia sin cargar todo en RAM) y
entrega filas como diccionarios ``{encabezado: valor}`` a partir de una fila de cabecera dada.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any


def iter_excel_rows(
    path: str | Path, header_row: int = 1, sheet: str | None = None
) -> Iterator[dict[str, Any]]:
    """Itera las filas de datos de una hoja como dicts ``{encabezado: valor}``.

    - ``header_row``: fila (1-indexada) que contiene los encabezados. En EmpresasColombia es 8
      (filas 1-7 son banner ISI Markets); en StartIA es 1.
    - ``sheet``: nombre de hoja; None → la activa.
    - Se saltan las filas totalmente vacías. Los valores se devuelven tal cual (str/num/None); la
      normalización vive en los parsers puros (``shared/ingest``).
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet] if sheet else wb.active
        encabezados: list[str] | None = None
        for idx, fila in enumerate(ws.iter_rows(values_only=True), start=1):
            if idx < header_row:
                continue
            if idx == header_row:
                encabezados = [str(c).strip() if c is not None else "" for c in fila]
                continue
            if fila is None or all(c is None for c in fila):
                continue
            assert encabezados is not None
            yield {encabezados[i]: fila[i] for i in range(min(len(encabezados), len(fila)))}
    finally:
        wb.close()
