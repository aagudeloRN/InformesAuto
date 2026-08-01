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
    ALCANCE_LOCAL,
    ESTADO_CANDIDATO,
    ESTADO_DESCARTADO,
    ESTADO_VERIFICADO,
    TIPO_COMPETIDOR,
    Entidad,
    EntidadAtributo,
    EntidadSector,
)
from ic.domain.kb.ficha_parser import FICHA_KEYS
from ic.domain.kb.relevance import (
    LocalRow,
    ProductoRankRow,
    es_ruido_competidor,
    rank_by_product_overlap,
)
from ic.shared.text_productos import producto_overlap


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
    alcance: str | None = None
    segmento: str | None = None
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
            "alcance": fila.alcance,
            "segmento": fila.segmento,
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
            else "(nombre_normalizado, COALESCE(sector_gics, '')) WHERE nit IS NULL"
        )
        sql = text(
            f"INSERT INTO {tabla} (tipo, nombre, nombre_normalizado, nit, ciudad, pais, "
            " sector_gics, sub_gics, alcance, segmento, estado, aliases, n_menciones, n_chunks, "
            " n_sectores) "
            "VALUES (:tipo, :nombre, :nombre_normalizado, :nit, :ciudad, :pais, :sector_gics, "
            " :sub_gics, :alcance, :segmento, :estado, CAST(:aliases AS jsonb), :n_menciones, "
            " :n_chunks, :n_sectores) "
            f"ON CONFLICT {conflicto} DO UPDATE SET "
            "  nombre = EXCLUDED.nombre, "
            "  tipo = EXCLUDED.tipo, "
            "  ciudad = COALESCE(EXCLUDED.ciudad, {t}.ciudad), "
            "  pais = COALESCE(EXCLUDED.pais, {t}.pais), "
            "  sector_gics = COALESCE(EXCLUDED.sector_gics, {t}.sector_gics), "
            # No degrada: el merge (NULL) conserva sub_gics/alcance; la siembra/curación los fija.
            "  sub_gics = COALESCE(EXCLUDED.sub_gics, {t}.sub_gics), "
            "  alcance = COALESCE(EXCLUDED.alcance, {t}.alcance), "
            "  segmento = COALESCE(EXCLUDED.segmento, {t}.segmento), "
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

    def get_id_by_nombre_sector(
        self, nombre_normalizado: str, sector_gics: str | None
    ) -> int | None:
        """Id de una entidad ya consolidada por nombre normalizado (+sector). None si no existe.

        Solo LOOKUP (DT-064/T3): las fichas se persisten únicamente sobre entidades **ya ancladas**
        (globales/locales del KB); no se crea nada aquí. Si hay sector se restringe a él (evita
        casar un homónimo de otro grupo); si no, casa por nombre. Prefiere no-descartado/verificado.
        """
        if not nombre_normalizado:
            return None
        tabla = Entidad.__table__.fullname
        cond_sector = " AND sector_gics = :sector" if sector_gics else ""
        sql = text(
            f"SELECT id FROM {tabla} "
            "WHERE nombre_normalizado = :norm AND estado <> :descartado" + cond_sector + " "
            "ORDER BY (estado = :verificado) DESC, id ASC LIMIT 1"
        )
        params = {
            "norm": nombre_normalizado,
            "descartado": ESTADO_DESCARTADO,
            "verificado": ESTADO_VERIFICADO,
        }
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
        self, sector_gics: str, nombres: list[str]
    ) -> dict[str, dict[str, str]]:
        """Campos de ficha ya conocidos del KB para los competidores dados (DT-064/T4).

        Devuelve ``{nombre: {clave: valor}}`` restringido a las claves de ficha
        (``FICHA_KEYS``) y al sector. Alimenta el pre-fill del prompt (escribir desde hechos).
        `verificado` gana sobre `candidato` si hay ambos para una clave. Vacío → ``{}``.
        """
        if not sector_gics or not nombres:
            return {}
        ent = Entidad.__table__.fullname
        atr = EntidadAtributo.__table__.fullname
        sql = text(
            f"SELECT e.nombre, a.clave, a.valor "
            f"FROM {ent} e JOIN {atr} a ON a.entidad_id = e.id "
            "WHERE e.sector_gics = :sector AND a.clave = ANY(:claves) "
            "  AND e.nombre = ANY(:nombres) AND a.valor IS NOT NULL "
            "ORDER BY (a.estado = :verificado) DESC"
        )
        rows = self._db.execute(
            sql,
            {
                "sector": sector_gics,
                "claves": list(FICHA_KEYS),
                "nombres": list(nombres),
                "verificado": ESTADO_VERIFICADO,
            },
        ).fetchall()
        fichas: dict[str, dict[str, str]] = {}
        for nombre, clave, valor in rows:
            campos = fichas.setdefault(nombre, {})
            campos.setdefault(clave, valor)  # el primero (verificado) gana
        return fichas

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
        """Registra/actualiza una membresía sectorial (DT-050). Idempotente; no degrada verificado.

        Único por (entidad, sector, sub_gics). Re-ejecutar la siembra no duplica membresías.
        """
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
        sector_gics: str,
        productos_terms: set[str] | None = None,
        alcance: str | None = None,
        limit: int = 8,
    ) -> list[str]:
        """Nombres canónicos de competidores del grupo para anclar (DT-056/DT-063).

        Trae los candidatos del grupo GICS (excluye `descartado`, gate RN-001) con su **perfil de
        producto** (atributo `productos_perfil`, sembrado al descubrir el global) y **delega** el
        orden en `rank_by_product_overlap` (dominio puro): excluye ruido, filtra `alcance` si se
        pide (p. ej. `global` para 2.1.1) y ordena por SOLAPE con los productos de la empresa
        analizada (DT-063, reemplaza el sub-código). Sin `productos_terms` → orden por evidencia.
        """
        if not sector_gics:
            return []
        ent = Entidad.__table__.fullname
        atr = EntidadAtributo.__table__.fullname
        sql = text(
            f"SELECT e.nombre, e.nombre_normalizado, e.alcance, e.estado, e.n_chunks, "
            f"       a_prod.valor "
            f"FROM {ent} e "
            f"LEFT JOIN {atr} a_prod "
            f"  ON a_prod.entidad_id = e.id AND a_prod.clave = 'productos_perfil' "
            "WHERE e.sector_gics = :sector AND e.estado <> :descartado "
            "  AND e.tipo IN ('competidor', 'empresa')"
        )
        rows = self._db.execute(
            sql, {"sector": sector_gics, "descartado": ESTADO_DESCARTADO}
        ).fetchall()
        candidatos = [
            ProductoRankRow(
                nombre=r[0],
                nombre_normalizado=r[1] or "",
                descriptor=r[5] or "",
                alcance=r[2],
                verificado=(r[3] == ESTADO_VERIFICADO),
                tiebreak=int(r[4] or 0),
            )
            for r in rows
        ]
        # Tier de clase mundial: exigir solape (no traer globales de otra actividad; vacío → el
        # guard dispara el descubrimiento por producto). Sin productos → orden por evidencia.
        return rank_by_product_overlap(
            candidatos, productos_terms or set(),
            alcance=alcance, require_overlap=True, limit=limit,
        )

    def list_locales_by_sector(
        self,
        sector_gics: str,
        *,
        segmento: str | None = None,
        solo_establecidas: bool = False,
        productos_terms: set[str] | None = None,
        limit: int = 6,
    ) -> list[LocalRow]:
        """Jugadores LOCALES del directorio para anclar 2.1.2/2.1.3 (DT-050/DT-063). JOIN sectores.

        Filtra ``alcance='local'`` y (opcional) ``segmento`` (`startup` para 2.1.3;
        ``solo_establecidas`` = segmento IS NULL para 2.1.2). Excluye ``descartado`` (RN-001).
        Trae los más notables por **tamaño** (prefetch) y los **re-rankea por SOLAPE** de sus
        actividad/vertical/descripción con los productos de la empresa analizada (DT-063): así una
        láctea ve Colanta/Alquería antes que un cárnico grande del mismo grupo. `productos_terms`
        vacío → orden por tamaño (fallback). Path GLOBAL (`list_competidores_by_sector`) aparte.
        """
        if not sector_gics:
            return []
        ent = Entidad.__table__.fullname
        sec = EntidadSector.__table__.fullname
        atr = EntidadAtributo.__table__.fullname
        cond_seg = ""
        if segmento is not None:
            cond_seg = " AND e.segmento = :segmento"
        elif solo_establecidas:
            cond_seg = " AND e.segmento IS NULL"
        # Tamaño: se recorta en la coma decimal y se dejan solo dígitos (proxy monótono).
        tamano_num = (
            "NULLIF(regexp_replace(split_part(a_ing.valor, ',', 1), '[^0-9]', '', 'g'), '')"
            "::bigint"
        )
        # Prefetch generoso por tamaño; el re-rank fino por solape se hace en dominio (puro).
        prefetch = max(limit * 10, 40)
        sql = text(
            f"SELECT e.nombre, e.ciudad, es.vertical, a_ing.valor, e.segmento, "
            f"       (e.estado = :verificado) AS verificado, {tamano_num} AS tam, a_desc.valor, "
            f"       a_prod.valor "
            f"FROM {ent} e "
            f"JOIN {sec} es ON es.entidad_id = e.id "
            f"LEFT JOIN {atr} a_ing "
            f"  ON a_ing.entidad_id = e.id AND a_ing.clave = 'ingreso_operativo' "
            f"LEFT JOIN {atr} a_desc "
            f"  ON a_desc.entidad_id = e.id AND a_desc.clave = 'descripcion' "
            f"LEFT JOIN {atr} a_prod "
            f"  ON a_prod.entidad_id = e.id AND a_prod.clave = 'productos_perfil' "
            f"WHERE es.sector_gics = :sector AND e.alcance = :local "
            f"  AND e.estado <> :descartado AND e.tipo IN ('competidor', 'empresa'){cond_seg} "
            f"ORDER BY verificado DESC, tam DESC NULLS LAST "
            f"LIMIT :prefetch"
        )
        rows = self._db.execute(
            sql,
            {
                "sector": sector_gics, "local": ALCANCE_LOCAL, "descartado": ESTADO_DESCARTADO,
                "verificado": ESTADO_VERIFICADO, "segmento": segmento, "prefetch": prefetch,
            },
        ).fetchall()
        terms = productos_terms or set()

        def _clave(r):
            # Descriptor: perfil de producto (limpio) + vertical/CIIU + descripción.
            descriptor = f"{r[8] or ''} {r[2] or ''} {r[7] or ''}"
            return (-producto_overlap(descriptor, terms), not r[5], -(int(r[6]) if r[6] else 0))

        rows = sorted(rows, key=_clave)[:limit]
        return [
            LocalRow(
                nombre=r[0], ciudad=r[1], actividad=r[2],
                tamano=(str(r[3]) if r[3] else None), segmento=r[4],
            )
            for r in rows
        ]

    def descartar_ruido_competidores(self, dry_run: bool = False) -> list[str]:
        """Marca `descartado` el ruido residual del KB (medios/métricas) — curación DT-061/T3.

        Idempotente (re-run no re-marca: excluye ya-descartados) y **no degrada** `verificado`
        (guard `estado <> verificado` en el UPDATE, RN-001). El criterio de ruido es el predicado
        puro `es_ruido_competidor`; devuelve los nombres normalizados marcados (o los que se
        marcarían en `dry_run`).
        """
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
                    {"id": id_, "descartado": ESTADO_DESCARTADO, "verificado": ESTADO_VERIFICADO},
                )
        if not dry_run and marcados:
            self._db.commit()
        return marcados

    def backfill_memberships_from_entidades(self, fuente: str = "backfill") -> int:
        """Deriva membresías en `entidad_sectores` desde entidades con `sector_gics` (DT-050/T4).

        Unifica el KB preexistente (global/candidatos NER) en el modelo de membresías. Idempotente
        (ON CONFLICT DO NOTHING sobre el único (entidad, sector, sub)); re-run no duplica. Conserva
        sub_gics/alcance/estado de la entidad. Devuelve nº de membresías insertadas.
        """
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

    def count(self) -> int:
        tabla = Entidad.__table__.fullname
        return int(self._db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar() or 0)
