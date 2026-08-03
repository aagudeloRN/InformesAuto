"""Parser puro de StartIA (startups de Medellín) → ParsedEntidad (DT-050/T2).

Cada fila es una startup con una o varias Verticales ("FINTECH; HRTECH"). Cada vertical se mapea a
un grupo GICS por el crosswalk (``vertical_to_gics``) → una membresía por vertical resoluble (multi-
vertical es feature). ``segmento='startup'`` alimenta el tier 2.1.3. Trae ficha (etapa, ronda, web,
LinkedIn, fundación, empleados). Puro (RN-001). Política de fuente/estado la aplica el script.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ic.shared.constants.startia_gics import vertical_to_gics
from ic.shared.ingest.dtos import ParsedAtributo, ParsedEntidad, ParsedMembership

SEGMENTO_STARTUP = "startup"

COL_NOMBRE = "NOMBRE_STARTUP"
COL_RAZON = "RAZON_SOCIAL"
COL_NIT = "NIT"
COL_CIUDAD = "CIUDAD"
COL_VERTICALES = "VERTICALES"


def _limpio(valor: Any) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    return s or None


def _split_verticales(valor: Any) -> list[str]:
    """"FINTECH; HRTECH" → ['FINTECH', 'HRTECH']. Tolera ';' y ','."""
    if valor is None:
        return []
    bruto = str(valor).replace(",", ";")
    return [v.strip() for v in bruto.split(";") if v.strip()]


def parse_startia(
    row: dict[str, Any], *, normalize: Callable[[str], str]
) -> ParsedEntidad | None:
    """Fila cruda StartIA → ParsedEntidad (segmento=startup), o None si no hay nombre."""
    nombre = _limpio(row.get(COL_NOMBRE)) or _limpio(row.get(COL_RAZON))
    if not nombre:
        return None

    memberships: list[ParsedMembership] = []
    vistos: set[str] = set()
    for vertical in _split_verticales(row.get(COL_VERTICALES)):
        gics = vertical_to_gics(vertical)
        if not gics or gics in vistos:
            continue
        vistos.add(gics)
        memberships.append(ParsedMembership(sector_gics=gics, sub_gics=None, vertical=vertical))

    atributos: list[ParsedAtributo] = []
    for clave, col in (
        ("etapa", "ETAPA"),
        ("ultima_ronda", "ULTIMA_RONDA"),
        ("sitio_web", "SITIO_WEB"),
        ("linkedin", "LINKEDIN"),
        ("ano_fundacion", "ANO_FUNDACION"),
        ("empleados", "NUMERO_EMPLEADOS"),
        ("descripcion", "DESCRIPCION"),
        ("verticales", COL_VERTICALES),
        # DT-065: columnas ricas que faltaban. `tecnologias` alimenta la ficha (factor_diferencial,
        # vía SOURCE_ATTR_TO_FICHA); `ventas_2025_cop` = ingresos (metadata). Requiere re-seed.
        ("tecnologias", "TECNOLOGIAS"),
        ("ventas_2025_cop", "VENTAS_2025_(COP)"),
    ):
        valor = _limpio(row.get(col))
        if valor:
            atributos.append(ParsedAtributo(clave=clave, valor=valor))

    return ParsedEntidad(
        nombre=nombre,
        nombre_normalizado=normalize(nombre),
        nit=_nit_normalizado(row.get(COL_NIT)),
        ciudad=_limpio(row.get(COL_CIUDAD)),
        pais=None,
        segmento=SEGMENTO_STARTUP,
        memberships=memberships,
        atributos=atributos,
    )


def _nit_normalizado(valor: Any) -> str | None:
    if valor is None:
        return None
    digitos = "".join(c for c in str(valor) if c.isdigit())
    return digitos or None
