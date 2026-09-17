"""Repositorio del KB de entidades (DT-056).

Upsert idempotente: por `nit` cuando existe, si no por `(nombre_normalizado, sector_gics)`. Correr
el merge dos veces sobre el mismo sustrato NO duplica filas (ON CONFLICT DO UPDATE) y **no degrada**
el estado (`verificado` nunca vuelve a `candidato`). Los `aliases` se fusionan (unión de formas
superficiales). Provenance + estado candidato/verificado en todo dato (RN-001): el KB consolida,
la verificación es curada/HITL.

Las implementaciones de las queries más pesadas viven en ``_entidad_queries.py`` (DT-066 / FR-008).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.entidad import (
    ESTADO_CANDIDATO,
    ESTADO_DESCARTADO,
    ESTADO_VERIFICADO,
    Entidad,
    EntidadAtributo,
    EntidadSector,
)
from ic.data.repositories._entidad_locales import LocalRow
from ic.data.repositories._entidad_queries import (
    EntidadRow,
    _clave_exclusion,
)
from ic.data.repositories._entidad_queries import (
    list_competidores_by_sector as _list_competidores,
)
from ic.data.repositories._entidad_queries import (
    list_ficha_atributos_by_sector as _list_ficha,
)
from ic.data.repositories._entidad_queries import (
    list_locales_by_sector as _list_locales,
)
from ic.data.repositories._entidad_queries import (
    upsert_entidad as upsert_entidad_sql,
)
from ic.domain.kb.relevance import es_ruido_competidor

__all__ = ["EntidadRepository", "_clave_exclusion"]


class EntidadRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_entidad(self, fila: EntidadRow) -> int:
        """Upsert idempotente (DT-056/T3/T4). No degrada estado verificado; une aliases."""
        return upsert_entidad_sql(self._db, fila)

    def get_id_by_nombre_sector(
        self, nombre_norm: str, sector_gics: str | None = None
    ) -> int | None:
        """Busca ID por `nombre_normalizado` y sector opcional. Devuelve None si no existe."""
        if not nombre_norm:
            return None
        tabla = Entidad.__table__.fullname
        cond_sector = " AND sector_gics = :sector" if sector_gics else ""
        sql = text(
            f"SELECT id FROM {tabla} WHERE nombre_normalizado = :norm{cond_sector} "
            "ORDER BY (estado = :verificado) DESC, id DESC LIMIT 1"
        )
        params: dict[str, Any] = {"norm": nombre_norm, "verificado": ESTADO_VERIFICADO}
        if sector_gics:
            params["sector"] = sector_gics
        row = self._db.execute(sql, params).fetchone()
        return int(row[0]) if row else None

    def add_atributo(
        self,
        entidad_id: int,
        clave: str,
        valor: str | None,
        fuente: str,
        *,
        confianza: float | None = None,
        documento_id: str | None = None,
        estado: str = ESTADO_CANDIDATO,
    ) -> None:
        """Registra un atributo con su procedencia. Idempotente por (entidad, clave, fuente)."""
        tabla = EntidadAtributo.__table__.fullname
        sql = text(
            f"INSERT INTO {tabla} (entidad_id, clave, valor, fuente, confianza, documento_id, "
            " estado) "
            "VALUES (:entidad_id, :clave, :valor, :fuente, :confianza, "
            " CAST(:documento_id AS uuid), :estado) "
            "ON CONFLICT (entidad_id, clave, fuente) DO UPDATE SET "
            "  valor = EXCLUDED.valor, confianza = EXCLUDED.confianza, "
            "  documento_id = EXCLUDED.documento_id, estado = EXCLUDED.estado"
        )
        self._db.execute(
            sql,
            {
                "entidad_id": entidad_id,
                "clave": clave,
                "valor": valor,
                "fuente": fuente,
                "confianza": confianza,
                "documento_id": documento_id,
                "estado": estado,
            },
        )
        self._db.commit()

    def list_ficha_atributos_by_sector(
        self, sectores_gics: str | Sequence[str], nombres: list[str]
    ) -> dict[str, dict[str, str]]:
        """Campos de ficha ya conocidos del KB para los competidores dados (DT-064/T4/DT-UI04f)."""
        return _list_ficha(self._db, sectores_gics, nombres)

    def upsert_sector_membership(
        self,
        entidad_id: int,
        sector_gics: str,
        *,
        sub_gics: str | None = None,
        vertical: str | None = None,
        alcance: str | None = None,
        fuente: str = "",
        estado: str = ESTADO_CANDIDATO,
    ) -> None:
        """Registra/actualiza una membresía sectorial (DT-050). Idempotente."""
        tabla = EntidadSector.__table__.fullname
        sql = text(
            f"INSERT INTO {tabla} (entidad_id, sector_gics, sub_gics, vertical, alcance, fuente, "
            " estado) "
            "VALUES (:entidad_id, :sector_gics, :sub_gics, :vertical, :alcance, :fuente, :estado) "
            "ON CONFLICT (entidad_id, sector_gics, COALESCE(sub_gics, '')) DO UPDATE SET "
            "  vertical = COALESCE(EXCLUDED.vertical, {t}.vertical), "
            "  alcance = COALESCE(EXCLUDED.alcance, {t}.alcance), "
            "  fuente = EXCLUDED.fuente, "
            "  estado = CASE WHEN {t}.estado = 'verificado' THEN 'verificado' "
            "                ELSE EXCLUDED.estado END".format(t=tabla)
        )
        self._db.execute(
            sql,
            {
                "entidad_id": entidad_id,
                "sector_gics": sector_gics,
                "sub_gics": sub_gics,
                "vertical": vertical,
                "alcance": alcance,
                "fuente": fuente,
                "estado": estado,
            },
        )
        self._db.commit()

    def list_competidores_by_sector(
        self,
        sectores_gics: str | Sequence[str],
        productos_terms: set[str] | None = None,
        alcance: str | None = None,
        limit: int = 8,
        exclude_nombre: str | None = None,
    ) -> list[str]:
        """Nombres canónicos de competidores del grupo para anclar (DT-056/DT-063/DT-UI04f)."""
        return _list_competidores(
            self._db, sectores_gics, productos_terms, alcance, limit, exclude_nombre
        )

    def list_locales_by_sector(
        self,
        sector_gics: str | Sequence[str],
        *,
        segmento: str | None = None,
        solo_establecidas: bool = False,
        productos_terms: set[str] | None = None,
        limit: int = 6,
        exclude_nombre: str | None = None,
    ) -> list[LocalRow]:
        """Jugadores LOCALES del directorio para anclar 2.1.2/2.1.3 (DT-050/DT-063)."""
        return _list_locales(
            self._db,
            sector_gics,
            segmento=segmento,
            solo_establecidas=solo_establecidas,
            productos_terms=productos_terms,
            limit=limit,
            exclude_nombre=exclude_nombre,
        )

    def descartar_ruido_competidores(self, dry_run: bool = False) -> list[str]:
        """Marca `descartado` el ruido residual del KB (medios/métricas) — curación DT-061/T3."""
        tabla = Entidad.__table__.fullname
        sel = text(
            f"SELECT id, nombre_normalizado FROM {tabla} "
            "WHERE estado NOT IN (:descartado, :verificado) "
            "  AND tipo IN ('competidor', 'empresa')"
        )
        rows = self._db.execute(
            sel, {"descartado": ESTADO_DESCARTADO, "verificado": ESTADO_VERIFICADO}
        ).fetchall()
        upd = text(
            f"UPDATE {tabla} SET estado = :descartado, updated_at = now() "
            "WHERE id = :id AND estado <> :verificado"
        )
        marcados: list[str] = []
        for id_, norm in rows:
            if not es_ruido_competidor(norm or ""):
                continue
            marcados.append(norm)
            if not dry_run:
                self._db.execute(
                    upd,
                    {
                        "id": id_,
                        "descartado": ESTADO_DESCARTADO,
                        "verificado": ESTADO_VERIFICADO,
                    },
                )
        if not dry_run and marcados:
            self._db.commit()
        return marcados

    def backfill_memberships_from_entidades(self, fuente: str = "backfill") -> int:
        """Deriva membresías en `entidad_sectores` desde entidades con `sector_gics` (DT-050/T4)."""
        ent = Entidad.__table__.fullname
        sec = EntidadSector.__table__.fullname
        sql = text(
            f"INSERT INTO {sec} (entidad_id, sector_gics, sub_gics, alcance, fuente, estado) "
            f"SELECT id, sector_gics, sub_gics, alcance, :fuente, estado FROM {ent} "
            "WHERE sector_gics IS NOT NULL "
            "ON CONFLICT (entidad_id, sector_gics, COALESCE(sub_gics, '')) DO NOTHING"
        )
        n = self._db.execute(sql, {"fuente": fuente}).rowcount
        self._db.commit()
        return int(n or 0)

    def recompute_n_sectores(self) -> int:
        """Recalcula `entidades.n_sectores` = COUNT real de membresías (DT-050/T4). Idempotente."""
        ent = Entidad.__table__.fullname
        sec = EntidadSector.__table__.fullname
        sql = text(
            f"UPDATE {ent} e SET n_sectores = ("
            f"  SELECT count(DISTINCT sector_gics) FROM {sec} es WHERE es.entidad_id = e.id"
            "), updated_at = now()"
        )
        n = self._db.execute(sql).rowcount
        self._db.commit()
        return int(n or 0)

    def list_duplicados_por_nit(self) -> list[dict[str, Any]]:
        """Devuelve grupos de entidades duplicadas que comparten el mismo NIT no nulo."""
        from ic.data.repositories._entidad_reconciliation import find_duplicate_nits

        return find_duplicate_nits(self._db)

    def merge_entidades_por_nit(self, canonical_id: int, duplicate_ids: list[int]) -> None:
        """Fusiona entidades duplicadas en canonical_id consolidando relaciones y aliases."""
        from ic.data.repositories._entidad_reconciliation import (
            merge_entidades_por_nit as _merge_nit,
        )

        _merge_nit(self._db, canonical_id, duplicate_ids)

    def count(self) -> int:
        tabla = Entidad.__table__.fullname
        return int(self._db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar() or 0)
