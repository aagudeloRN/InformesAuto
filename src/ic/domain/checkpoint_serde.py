"""Serialización pura de capítulos para el checkpoint (T22.3, DT-030).

Convierte los dataclasses de capítulo (shared.types) a/desde dicts JSON-serializables,
sin tocar la BD ni librerías externas. El repositorio (data/) persiste el dict; el
orquestador (domain/use_cases) llama a estos helpers. RN-safe: round-trip fiel, no
altera contenido.
"""

from __future__ import annotations

from dataclasses import asdict

from ic.shared.types import (
    Cap21Globales,
    Cap21Jugadores,
    Cap21Regionales,
    Cap21Startups,
    Cap22Division,
    CapAccionables,
    CapBenchmarking,
    CapConvergencia,
    CapEcosistema,
    CapMercado,
    CapTendencias,
    ChunkResult,
    ClasificacionCompetidor,
    ClasificacionGICS,
    CuadranteKey,
    DescripcionEmpresa,
)

# Tipos que el checkpoint sabe (de)serializar, indexados por nombre de clase.
_REGISTRY: dict[str, type] = {
    cls.__name__: cls
    for cls in (
        DescripcionEmpresa,
        ClasificacionGICS,
        CapBenchmarking,
        CapMercado,
        CapTendencias,
        CapEcosistema,
        CapConvergencia,
        CapAccionables,
        Cap21Globales,
        Cap21Regionales,
        Cap21Startups,
        Cap21Jugadores,
        Cap22Division,
    )
}

_TYPE_KEY = "__type__"


def make_run_key(empresa: str, ciiu: str | None) -> str:
    """Clave determinista de corrida (misma empresa+ciiu → mismo run_key → resume)."""
    slug = empresa.strip().lower().replace(" ", "_").replace(".", "")
    return f"{slug}:{ciiu or 'auto'}"


def serialize_cap(obj) -> dict:
    """Serializa un capítulo/objeto de dominio a un dict JSON-serializable."""
    data = asdict(obj)
    data[_TYPE_KEY] = type(obj).__name__
    return data


def deserialize_cap(payload: dict):
    """Reconstruye el dataclass original desde el dict persistido.

    Lanza KeyError si el tipo no está registrado (defensa: no reconstruir a ciegas).
    """
    data = dict(payload)
    tname = data.pop(_TYPE_KEY)
    cls = _REGISTRY[tname]
    chunks = data.get("chunks_usados")
    if chunks:
        data["chunks_usados"] = [ChunkResult(**c) for c in chunks]
    if tname == "Cap22Division":
        raw_clases = data.get("clasificaciones") or []
        data["clasificaciones"] = [
            ClasificacionCompetidor(
                nombre=c["nombre"],
                cuadrante=CuadranteKey(c["cuadrante"]),
                dato_no_disponible=c.get("dato_no_disponible", False),
            )
            for c in raw_clases
        ]
    return cls(**data)
