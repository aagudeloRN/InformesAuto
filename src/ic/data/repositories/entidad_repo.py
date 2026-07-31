"""Repositorio del KB de entidades (DT-056).

Upsert idempotente: por `nit` cuando existe, si no por `(nombre_normalizado, sector_gics)`. Correr
el merge dos veces sobre el mismo sustrato NO duplica filas (ON CONFLICT DO UPDATE) y **no degrada**
el estado (`verificado` nunca vuelve a `candidato`). Los `aliases` se fusionan (unión de formas
superficiales). Provenance + estado candidato/verificado en todo dato (RN-001): el KB consolida,
la verificación es curada/HITL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from ic.data.models.entidad import (
    ESTADO_CANDIDATO,
    ESTADO_DESCARTADO,
    ESTADO_VERIFICADO,
    TIPO_COMPETIDOR,
    Entidad,
    EntidadAtributo,
)


@dataclass
class EntidadRow:
    """DTO de una entidad canónica a consolidar (con su señal de procedencia)."""

    nombre: str
    nombre_normalizado: str
    tipo: str = TIPO_COMPETIDOR
    nit: str | None = None
    ciudad: str | None = None
    pais: str | None = None
    sector_gics: str | None = None
    sub_gics: str | None = None
    estado: str = ESTADO_CANDIDATO
    aliases: list[str] = field(default_factory=list)
    n_menciones: int | None = None
    n_chunks: int | None = None
    n_sectores: int | None = None


class EntidadRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_entidad(self, fila: EntidadRow) -> int:
        """Inserta/actualiza una entidad y devuelve su id. Idempotente; no degrada estado.

        Ruta de conflicto según haya NIT (clave fuerte) o no (nombre normalizado + sector).
        `aliases` se fusiona (unión sin duplicados); `estado` sube pero nunca baja de verificado.
        """
        tabla = Entidad.__table__.fullname
        aliases_json = json.dumps(sorted(set(fila.aliases)))
        params = {
            "tipo": fila.tipo,
            "nombre": fila.nombre,
            "nombre_normalizado": fila.nombre_normalizado,
            "nit": fila.nit,
            "ciudad": fila.ciudad,
            "pais": fila.pais,
            "sector_gics": fila.sector_gics,
            "sub_gics": fila.sub_gics,
            "estado": fila.estado,
            "aliases": aliases_json,
            "n_menciones": fila.n_menciones,
            "n_chunks": fila.n_chunks,
            "n_sectores": fila.n_sectores,
        }
        # Conflicto por NIT (parcial) o por (nombre_normalizado, sector). RETURNING id funciona
        # incluso en conflicto porque es DO UPDATE (no DO NOTHING).
        conflicto = (
            "(nit) WHERE nit IS NOT NULL"
            if fila.nit
            else "(nombre_normalizado, COALESCE(sector_gics, ''))"
        )
        sql = text(
            f"INSERT INTO {tabla} (tipo, nombre, nombre_normalizado, nit, ciudad, pais, "
            " sector_gics, sub_gics, estado, aliases, n_menciones, n_chunks, n_sectores) "
            "VALUES (:tipo, :nombre, :nombre_normalizado, :nit, :ciudad, :pais, :sector_gics, "
            " :sub_gics, :estado, CAST(:aliases AS jsonb), :n_menciones, :n_chunks, :n_sectores) "
            f"ON CONFLICT {conflicto} DO UPDATE SET "
            "  nombre = EXCLUDED.nombre, "
            "  tipo = EXCLUDED.tipo, "
            "  ciudad = COALESCE(EXCLUDED.ciudad, {t}.ciudad), "
            "  pais = COALESCE(EXCLUDED.pais, {t}.pais), "
            "  sector_gics = COALESCE(EXCLUDED.sector_gics, {t}.sector_gics), "
            # No degrada: el merge (NULL) conserva el sub_gics; la siembra/curación lo fija.
            "  sub_gics = COALESCE(EXCLUDED.sub_gics, {t}.sub_gics), "
            # No degradar: verificado se conserva aunque llegue un candidato.
            "  estado = CASE WHEN {t}.estado = 'verificado' THEN 'verificado' "
            "                ELSE EXCLUDED.estado END, "
            # Unión de aliases (formas superficiales del mismo nombre normalizado).
            "  aliases = ( SELECT COALESCE(jsonb_agg(DISTINCT a ORDER BY a), '[]'::jsonb) "
            "              FROM jsonb_array_elements_text({t}.aliases || EXCLUDED.aliases) a ), "
            "  n_menciones = EXCLUDED.n_menciones, "
            "  n_chunks = EXCLUDED.n_chunks, "
            "  n_sectores = EXCLUDED.n_sectores, "
            "  updated_at = now() "
            "RETURNING id".format(t=tabla)
        )
        entidad_id = self._db.execute(sql, params).scalar_one()
        self._db.commit()
        return int(entidad_id)

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

    def list_competidores_by_sector(
        self, sector_gics: str, sub_gics: str | None = None, limit: int = 8
    ) -> list[str]:
        """Nombres canónicos de competidores/empresas del sector para anclar (DT-056/DT-061).

        Excluye entidades `descartado` (gate RN-001). Cuando `sub_gics` (DT-061) se resuelve para
        la empresa analizada, prioriza los pares de la MISMA sub-actividad y los `verificado`
        (siembra curada) por delante de los candidatos NER del grupo. Orden:
        verificado → match de sub_gics → evidencia (n_chunks). Devuelve la forma display (`nombre`).
        """
        if not sector_gics:
            return []
        tabla = Entidad.__table__.fullname
        sql = text(
            f"SELECT nombre FROM {tabla} "
            "WHERE sector_gics = :sector AND estado <> :descartado "
            "  AND tipo IN ('competidor', 'empresa') "
            "ORDER BY (estado = :verificado) DESC, "
            "         (:sub IS NOT NULL AND sub_gics = :sub) DESC, "
            "         COALESCE(n_chunks, 0) DESC, COALESCE(n_menciones, 0) DESC "
            "LIMIT :limit"
        )
        rows = self._db.execute(
            sql,
            {
                "sector": sector_gics,
                "sub": sub_gics,
                "descartado": ESTADO_DESCARTADO,
                "verificado": ESTADO_VERIFICADO,
                "limit": limit,
            },
        ).fetchall()
        return [r[0] for r in rows]

    def count(self) -> int:
        tabla = Entidad.__table__.fullname
        return int(self._db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar() or 0)
