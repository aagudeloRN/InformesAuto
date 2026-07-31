"""Crosswalk Vertical StartIA → código de grupo GICS (DT-050/T2). Puro.

El catálogo ``documentos_sectoriales/FuentesExternas/CatalogoVerticalesStartIAGICS.csv`` mapea cada
Vertical StartIA (FinTech, AgTech, …) a un nombre de Grupo Industrial GICS. Se resuelve a código con
``extract_gics_code`` (que tolera el nombre sin el sufijo "(GICS XXXX)", ver
``feedback_extract_gics_code``). El CSV viene en cp1252 (acentos), no UTF-8.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from ic.shared.constants.gics_groups import extract_gics_code

_CSV_PATH = (
    Path(__file__).resolve().parents[4]
    / "documentos_sectoriales"
    / "FuentesExternas"
    / "CatalogoVerticalesStartIAGICS.csv"
)


@lru_cache(maxsize=1)
def _vertical_to_gics() -> dict[str, str]:
    """Carga el CSV una vez: {vertical_lower: código GICS}. Ignora verticales no resolubles."""
    mapping: dict[str, str] = {}
    with open(_CSV_PATH, newline="", encoding="cp1252") as f:
        reader = csv.reader(f)
        next(reader, None)  # cabecera: Vertical, Descripción, Grupo Industrial (GICS)
        for fila in reader:
            if len(fila) < 3:
                continue
            vertical = fila[0].strip()
            code = extract_gics_code(fila[2].strip())
            if vertical and code:
                mapping[vertical.lower()] = code
    return mapping


def vertical_to_gics(vertical: str | None) -> str | None:
    """Código GICS de una Vertical StartIA (case-insensitive), o None si no está en el catálogo."""
    if not vertical:
        return None
    return _vertical_to_gics().get(vertical.strip().lower())
