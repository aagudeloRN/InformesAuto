"""Parser puro de EmpresasColombia (ISI Markets/WVB) → ParsedEntidad (DT-050).

Cada fila del Excel es una empresa colombiana con su(s) código(s) CIIU embebido(s) en la columna
"Sector (Local)". Se mapea cada CIIU a un grupo GICS por división (``ciiu_division_to_gics``) y se
refina el sub-código en el grupo 3020 (``resolve_sub_gics``) desde el texto de actividad. Multi-
actividad ("… (M7010); … (M7020)") → varias membresías. Puro (RN-001: no fabrica; solo mapea el
texto presente). La política de fuente/estado/alcance la aplica el script de siembra.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ic.shared.constants.ciiu_gics import (
    ciiu_division_to_gics,
    extract_all_ciiu_from_text,
)
from ic.shared.constants.gics_groups import resolve_sub_gics
from ic.shared.ingest.dtos import ParsedAtributo, ParsedEntidad, ParsedMembership

# Encabezados exactos del Excel (fila 8). Centralizados para tolerar el orden de columnas.
COL_NOMBRE = "Compañía"
COL_SECTOR_LOCAL = "Sector (Local)"
COL_ACTIVIDADES = "Actividades principales (Local)"
COL_CIUDAD = "Ciudad"
COL_REGION = "Estado/Provincia/Región"
COL_NIT = "CO-NIT"
COL_INGRESO = "Total Ingreso Operativo"
COL_EMPLEADOS = "Número de empleados"
COL_FORMA_LEGAL = "Forma Legal"
COL_EJECUTIVOS = "Principales Ejecutivos"
COL_DESCRIPCION = "Descripción de la compañía / productos"


def _limpio(valor: Any) -> str | None:
    """Normaliza una celda a str no vacío o None (los Excel traen ' ' como relleno)."""
    if valor is None:
        return None
    s = str(valor).strip()
    return s or None


def _nit_normalizado(valor: Any) -> str | None:
    """Deja solo dígitos del CO-NIT (clave de dedup). None si no hay dígitos."""
    if valor is None:
        return None
    digitos = "".join(c for c in str(valor) if c.isdigit())
    return digitos or None


def parse_empresa_colombia(
    row: dict[str, Any], *, normalize: Callable[[str], str]
) -> ParsedEntidad | None:
    """Fila cruda → ParsedEntidad, o None si no hay nombre (fila inválida).

    ``normalize`` es la función de normalización de nombre inyectada (``normalize_entity``), para
    no invertir capas (shared no depende de infrastructure).
    """
    nombre = _limpio(row.get(COL_NOMBRE))
    if not nombre:
        return None

    sector_local = _limpio(row.get(COL_SECTOR_LOCAL)) or ""
    actividades = _limpio(row.get(COL_ACTIVIDADES)) or ""
    texto_clasificacion = f"{sector_local} {actividades}"

    memberships: list[ParsedMembership] = []
    vistos: set[str] = set()
    for ciiu in extract_all_ciiu_from_text(texto_clasificacion):
        gics = ciiu_division_to_gics(ciiu)
        if not gics or gics in vistos:
            continue
        vistos.add(gics)
        sub = resolve_sub_gics(texto_clasificacion, gics)
        memberships.append(
            ParsedMembership(sector_gics=gics, sub_gics=sub, vertical=sector_local or None)
        )

    atributos: list[ParsedAtributo] = []
    for clave, col in (
        ("ingreso_operativo", COL_INGRESO),
        ("n_empleados", COL_EMPLEADOS),
        ("forma_legal", COL_FORMA_LEGAL),
        ("ejecutivos", COL_EJECUTIVOS),
        ("descripcion", COL_DESCRIPCION),
        ("actividad", COL_SECTOR_LOCAL),
    ):
        valor = _limpio(row.get(col))
        if valor:
            atributos.append(ParsedAtributo(clave=clave, valor=valor))

    return ParsedEntidad(
        nombre=nombre,
        nombre_normalizado=normalize(nombre),
        nit=_nit_normalizado(row.get(COL_NIT)),
        ciudad=_limpio(row.get(COL_CIUDAD)),
        pais=_limpio(row.get(COL_REGION)),
        segmento=None,
        memberships=memberships,
        atributos=atributos,
    )
