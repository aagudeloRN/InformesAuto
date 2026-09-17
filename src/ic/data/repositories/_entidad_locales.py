"""Queries para jugadores locales (DT-050 / DT-063 / DT-UI04a)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import text

from ic.data.models.entidad import (
    ALCANCE_LOCAL,
    ESTADO_DESCARTADO,
    ESTADO_VERIFICADO,
    Entidad,
    EntidadAtributo,
    EntidadSector,
)
from ic.domain.kb.relevance import LocalRow
from ic.infrastructure.ner.entity_recognizer import normalize_entity
from ic.shared.text_productos import producto_overlap

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _clave_exclusion(nombre: str) -> str:
    """Clave de comparacion para excluir la empresa analizada (DT-UI04a): dedup por
    normalize_entity (minusculas, sin sufijos societarios ni puntuacion) mas sin acentos,
    para que 'ERCO ENERGIA S.A.S.' empate con 'ERCO ENERGIA'. Puro y determinista."""
    import unicodedata

    base = normalize_entity(nombre)
    return "".join(c for c in unicodedata.normalize("NFD", base) if unicodedata.category(c) != "Mn")


def list_locales_by_sector(
    db: Session,
    sector_gics: str | Sequence[str],
    *,
    segmento: str | None = None,
    solo_establecidas: bool = False,
    productos_terms: set[str] | None = None,
    limit: int = 6,
    exclude_nombre: str | None = None,
) -> list[LocalRow]:
    """Jugadores LOCALES del directorio para anclar 2.1.2/2.1.3 (DT-050/DT-063). JOIN sectores."""
    if isinstance(sector_gics, str):
        sectores = [sector_gics] if sector_gics else []
    else:
        sectores = [s for s in sector_gics if s]
    if not sectores:
        return []
    ent = Entidad.__table__.fullname
    sec = EntidadSector.__table__.fullname
    atr = EntidadAtributo.__table__.fullname
    cond_seg = ""
    if segmento is not None:
        cond_seg = " AND e.segmento = :segmento"
    elif solo_establecidas:
        cond_seg = " AND e.segmento IS NULL"
    tamano_num = (
        "NULLIF(regexp_replace(split_part(a_ing.valor, ',', 1), '[^0-9]', '', 'g'), '')::bigint"
    )
    prefetch = max(limit * 10, 40) * len(sectores)
    sql = text(
        f"SELECT e.nombre, e.ciudad, es.vertical, a_ing.valor, e.segmento, "
        f"       (e.estado = :verificado) AS verificado, {tamano_num} AS tam, a_desc.valor, "
        f"       a_prod.valor, "
        f"       NULLIF(regexp_replace(a_ven.valor, '[^0-9.]', '', 'g'), '')::float AS ventas_cop, "
        f"       COALESCE(e.n_menciones, 0) AS n_menciones "
        f"FROM {ent} e "
        f"JOIN {sec} es ON es.entidad_id = e.id "
        f"LEFT JOIN {atr} a_ing "
        f"  ON a_ing.entidad_id = e.id AND a_ing.clave = 'ingreso_operativo' "
        f"LEFT JOIN {atr} a_desc "
        f"  ON a_desc.entidad_id = e.id AND a_desc.clave = 'descripcion' "
        f"LEFT JOIN {atr} a_prod "
        f"  ON a_prod.entidad_id = e.id AND a_prod.clave = 'productos_perfil' "
        f"LEFT JOIN {atr} a_ven "
        f"  ON a_ven.entidad_id = e.id AND a_ven.clave = 'ventas_2025_cop' "
        f"WHERE es.sector_gics = ANY(:sectores) AND e.alcance = :local "
        f"  AND e.estado <> :descartado AND e.tipo IN ('competidor', 'empresa'){cond_seg} "
        f"ORDER BY verificado DESC, tam DESC NULLS LAST "
        f"LIMIT :prefetch"
    )
    rows = db.execute(
        sql,
        {
            "sectores": sectores,
            "local": ALCANCE_LOCAL,
            "descartado": ESTADO_DESCARTADO,
            "verificado": ESTADO_VERIFICADO,
            "segmento": segmento,
            "prefetch": prefetch,
        },
    ).fetchall()

    norm_excl = _clave_exclusion(exclude_nombre) if exclude_nombre else None
    if norm_excl:
        rows = [r for r in rows if _clave_exclusion(r[0]) != norm_excl]
    terms = productos_terms or set()

    def _clave(r):
        descriptor = f"{r[8] or ''} {r[2] or ''} {r[7] or ''}"
        ventas = r[9] if r[9] is not None else 0.0
        menciones = int(r[10]) if r[10] is not None else 0
        return (
            -producto_overlap(descriptor, terms),
            not r[5],
            -ventas,
            -menciones,
        )

    vistos: set[str] = set()
    deduped = []
    for r in sorted(rows, key=_clave):
        clave = _clave_exclusion(r[0])
        if clave in vistos:
            continue
        vistos.add(clave)
        deduped.append(r)
        if len(deduped) >= limit:
            break
    return [
        LocalRow(
            nombre=r[0],
            ciudad=r[1],
            actividad=r[2],
            tamano=(str(r[3]) if r[3] else None),
            segmento=r[4],
            ventas_2025_cop=(float(r[9]) if r[9] is not None else None),
            n_menciones=(int(r[10]) if r[10] is not None else 0),
        )
        for r in deduped
    ]
