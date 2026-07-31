"""DTOs estructurales de la ingesta del directorio local (DT-050). Puros, sin BD."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedMembership:
    """Una membresía sectorial derivada de la fuente (CIIU EMIS o vertical StartIA)."""

    sector_gics: str
    sub_gics: str | None = None
    vertical: str | None = None  # etiqueta de origen (texto CIIU o vertical StartIA)


@dataclass(frozen=True)
class ParsedAtributo:
    """Atributo de ficha con su clave canónica (la procedencia la fija el script)."""

    clave: str
    valor: str


@dataclass(frozen=True)
class ParsedEntidad:
    """Entidad estructural lista para que el script la envuelva con política (fuente/estado)."""

    nombre: str
    nombre_normalizado: str
    nit: str | None = None
    ciudad: str | None = None
    pais: str | None = None
    segmento: str | None = None
    memberships: list[ParsedMembership] = field(default_factory=list)
    atributos: list[ParsedAtributo] = field(default_factory=list)
