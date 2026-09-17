"""Consultas y funciones de fusion para reconciliacion de entidades por NIT (DT-050b)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.entidad import Entidad, EntidadAtributo, EntidadSector


def find_duplicate_nits(db: Session) -> list[dict[str, Any]]:
    """Devuelve grupos de entidades duplicadas que comparten el mismo NIT no nulo."""
    ent = Entidad.__table__.fullname
    atr = EntidadAtributo.__table__.fullname
    sql = text(
        f"SELECT e.nit, jsonb_agg(jsonb_build_object("
        f"  'id', e.id, 'nombre', e.nombre, 'estado', e.estado, "
        f"  'n_menciones', COALESCE(e.n_menciones, 0), "
        f"  'n_atributos', (SELECT count(*) FROM {atr} a WHERE a.entidad_id = e.id), "
        f"  'created_at', e.created_at"
        f")) as miembros "
        f"FROM {ent} e "
        f"WHERE e.nit IS NOT NULL AND trim(e.nit) <> '' AND trim(e.nit) <> '0' "
        f"GROUP BY e.nit HAVING count(*) > 1"
    )
    rows = db.execute(sql).fetchall()
    res = []
    for row in rows:
        res.append({"nit": row[0], "miembros": row[1]})
    return res


def merge_entidades_por_nit(db: Session, canonical_id: int, duplicate_ids: list[int]) -> None:
    """Merge idempotente de entidades duplicadas en canonical_id."""
    if not duplicate_ids:
        return
    ent = Entidad.__table__.fullname
    sec = EntidadSector.__table__.fullname
    atr = EntidadAtributo.__table__.fullname

    # 1. Obtener nombres y aliases de la entidad canonica y duplicados
    sql_names = text(
        f"SELECT nombre, aliases FROM {ent} WHERE id = ANY(:dup_ids) OR id = :canon_id"
    )
    rows = db.execute(sql_names, {"dup_ids": duplicate_ids, "canon_id": canonical_id}).fetchall()

    all_aliases = set()
    for row in rows:
        nombre, aliases_raw = row[0], row[1]
        if nombre:
            all_aliases.add(nombre)
        if isinstance(aliases_raw, list):
            for a in aliases_raw:
                if a:
                    all_aliases.add(str(a))

    # 2. Reasignar membresias sectoriales sin duplicar
    sql_sec = text(
        f"UPDATE {sec} SET entidad_id = :canon_id "
        f"WHERE entidad_id = ANY(:dup_ids) "
        f"  AND (sector_gics, COALESCE(sub_gics, '')) NOT IN ("
        f"    SELECT sector_gics, COALESCE(sub_gics, '') FROM {sec} WHERE entidad_id = :canon_id"
        f"  )"
    )
    db.execute(sql_sec, {"canon_id": canonical_id, "dup_ids": duplicate_ids})
    db.execute(
        text(f"DELETE FROM {sec} WHERE entidad_id = ANY(:dup_ids)"), {"dup_ids": duplicate_ids}
    )

    # 3. Reasignar atributos sin duplicar por (clave, fuente)
    sql_atr = text(
        f"UPDATE {atr} SET entidad_id = :canon_id "
        f"WHERE entidad_id = ANY(:dup_ids) "
        f"  AND (clave, fuente) NOT IN ("
        f"    SELECT clave, fuente FROM {atr} WHERE entidad_id = :canon_id"
        f"  )"
    )
    db.execute(sql_atr, {"canon_id": canonical_id, "dup_ids": duplicate_ids})
    db.execute(
        text(f"DELETE FROM {atr} WHERE entidad_id = ANY(:dup_ids)"), {"dup_ids": duplicate_ids}
    )

    # 4. Actualizar aliases en la entidad canonica
    aliases_json = json.dumps(sorted(list(all_aliases)))
    sql_update_canon = text(
        f"UPDATE {ent} SET aliases = CAST(:aliases AS jsonb), "
        "updated_at = now() WHERE id = :canon_id"
    )
    db.execute(sql_update_canon, {"aliases": aliases_json, "canon_id": canonical_id})

    # 5. Eliminar las entidades duplicadas fusionadas
    sql_del = text(f"DELETE FROM {ent} WHERE id = ANY(:dup_ids)")
    db.execute(sql_del, {"dup_ids": duplicate_ids})
    db.commit()
