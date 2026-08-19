"""Implementaciones de queries extraídas de entidad_repo.py (DT-066 / FR-008).

Módulo privado del paquete ``repositories/``. La interfaz pública sigue siendo
``EntidadRepository`` en ``entidad_repo.py``; aquí viven los SQL builders y la
lógica de filtrado/dedup de las consultas más pesadas para mantener la cohesión
de datos y respetar el límite de 300 líneas por archivo (Constitution Principle I).
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Sequence
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
from ic.domain.kb.ficha_parser import FICHA_KEYS, SOURCE_ATTR_TO_FICHA
from ic.domain.kb.relevance import (
    LocalRow,
    ProductoRankRow,
    rank_by_product_overlap,
)
from ic.infrastructure.ner.entity_recognizer import normalize_entity
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


def _clave_exclusion(nombre: str) -> str:
    """Clave de comparación para excluir la empresa analizada (DT-UI04a): dedup por
    ``normalize_entity`` (minúsculas, sin sufijos societarios ni puntuación) **más** sin acentos,
    para que "ERCO ENERGÍA S.A.S." empate con "ERCO ENERGIA". Puro y determinista."""
    base = normalize_entity(nombre)
    return "".join(
        c for c in unicodedata.normalize("NFD", base) if unicodedata.category(c) != "Mn"
    )


def upsert_entidad(db: Session, fila: EntidadRow) -> int:
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
    entidad_id = db.execute(sql, params).scalar_one()
    db.commit()
    return int(entidad_id)


def list_ficha_atributos_by_sector(
    db: Session,
    sectores_gics: str | Sequence[str],
    nombres: list[str],
) -> dict[str, dict[str, str]]:
    """Campos de ficha ya conocidos del KB para los competidores dados (DT-064/T4/DT-UI04f).

    Devuelve ``{nombre: {clave_ficha: valor}}`` restringido a los sectores. Acepta uno o
    varios sectores GICS (DT-UI04f); compatibilidad hacia atrás con str. Alimenta el pre-fill
    del prompt (escribir desde hechos). Fuentes de cada campo canónico, por prioridad:
    1) atributo NATIVO de la clave de ficha (``FICHA_KEYS``); 2) alias de una fuente local
    (``SOURCE_ATTR_TO_FICHA``: descripción/actividad/tecnologías de StartIA/EmpresasColombia,
    para no dejar vacíos los tiers regional/startup); 3) la columna ``ciudad`` de la entidad
    → ``presencia_geografica``. Native > alias > columna; ``verificado`` > ``candidato``.
    (La columna ``pais`` NO alimenta ``pais_origen``: en las fuentes locales guarda la región,
    no el país; el país fiable llega como atributo nativo.) RN-001: solo re-etiqueta lo dado.
    Vacío → {}.
    """
    if isinstance(sectores_gics, str):
        sectores = [sectores_gics] if sectores_gics else []
    else:
        sectores = [s for s in sectores_gics if s]
    if not sectores or not nombres:
        return {}
    ent = Entidad.__table__.fullname
    atr = EntidadAtributo.__table__.fullname
    claves = list(FICHA_KEYS) + list(SOURCE_ATTR_TO_FICHA.keys())
    sql = text(
        f"SELECT e.nombre, e.ciudad, a.clave, a.valor "
        f"FROM {ent} e JOIN {atr} a ON a.entidad_id = e.id "
        "WHERE e.sector_gics = ANY(:sectores) AND a.clave = ANY(:claves) "
        "  AND e.nombre = ANY(:nombres) AND a.valor IS NOT NULL "
        # Native antes que alias (setdefault da prioridad al nativo), y verificado antes.
        "ORDER BY (a.clave = ANY(:ficha)) DESC, (a.estado = :verificado) DESC"
    )
    rows = db.execute(
        sql,
        {
            "sectores": sectores,
            "claves": claves,
            "ficha": list(FICHA_KEYS),
            "nombres": list(nombres),
            "verificado": ESTADO_VERIFICADO,
        },
    ).fetchall()
    fichas: dict[str, dict[str, str]] = {}
    ciudades: dict[str, str | None] = {}
    for nombre, ciudad, clave, valor in rows:
        campos = fichas.setdefault(nombre, {})
        ciudades.setdefault(nombre, ciudad)
        canon = clave if clave in FICHA_KEYS else SOURCE_ATTR_TO_FICHA.get(clave)
        if canon:
            campos.setdefault(canon, valor)  # native (por ORDER BY) y verificado ganan
    for nombre, ciudad in ciudades.items():
        if ciudad:
            fichas[nombre].setdefault("presencia_geografica", ciudad)
    return fichas


def list_competidores_by_sector(
    db: Session,
    sectores_gics: str | Sequence[str],
    productos_terms: set[str] | None = None,
    alcance: str | None = None,
    limit: int = 8,
    exclude_nombre: str | None = None,
) -> list[str]:
    """Nombres canónicos de competidores del grupo para anclar (DT-056/DT-063/DT-UI04f).

    Acepta uno o varios sectores GICS (DT-UI04f): empresas multi-sector ven competidores de
    todos sus sectores en una sola consulta. Trae los candidatos con su **perfil de producto**
    y **delega** el orden en `rank_by_product_overlap` (dominio puro): excluye ruido, filtra
    `alcance` si se pide (p. ej. `global` para 2.1.1) y ordena por SOLAPE con los productos
    de la empresa analizada (DT-063). Sin `productos_terms` → orden por evidencia.
    Compatibilidad hacia atrás: un `str` se normaliza internamente a lista de un elemento.
    """
    if isinstance(sectores_gics, str):
        sectores = [sectores_gics] if sectores_gics else []
    else:
        sectores = [s for s in sectores_gics if s]
    if not sectores:
        return []
    ent = Entidad.__table__.fullname
    atr = EntidadAtributo.__table__.fullname
    sql = text(
        f"SELECT e.nombre, e.nombre_normalizado, e.alcance, e.estado, e.n_chunks, "
        f"       a_prod.valor, e.aliases "
        f"FROM {ent} e "
        f"LEFT JOIN {atr} a_prod "
        f"  ON a_prod.entidad_id = e.id AND a_prod.clave = 'productos_perfil' "
        "WHERE e.sector_gics = ANY(:sectores) AND e.estado <> :descartado "
        "  AND e.tipo IN ('competidor', 'empresa')"
    )
    rows = db.execute(
        sql, {"sectores": sectores, "descartado": ESTADO_DESCARTADO}
    ).fetchall()
    # DT-UI04a + DT-UI04f: excluir la empresa analizada por nombre canónico Y aliases.
    norm_excl = _clave_exclusion(exclude_nombre) if exclude_nombre else None

    def _es_focal(row) -> bool:
        if not norm_excl:
            return False
        if _clave_exclusion(row[0]) == norm_excl:
            return True
        # row[6] = aliases JSONB (lista de strings o None)
        aliases = row[6] if isinstance(row[6], list) else []
        return any(_clave_exclusion(a) == norm_excl for a in aliases)

    # DT-UI04f: dedup por _clave_exclusion antes del re-rank (una entidad multi-sector
    # puede aparecer varias veces si está en más de un sector de la lista).
    vistos: set[str] = set()
    candidatos = []
    for r in rows:
        if _es_focal(r):
            continue
        clave = _clave_exclusion(r[0])
        if clave in vistos:
            continue
        vistos.add(clave)
        candidatos.append(
            ProductoRankRow(
                nombre=r[0],
                nombre_normalizado=r[1] or "",
                descriptor=r[5] or "",
                alcance=r[2],
                verificado=(r[3] == ESTADO_VERIFICADO),
                tiebreak=int(r[4] or 0),
            )
        )
    return rank_by_product_overlap(
        candidatos,
        productos_terms or set(),
        alcance=alcance,
        require_overlap=True,
        limit=limit,
    )


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
    """Jugadores LOCALES del directorio para anclar 2.1.2/2.1.3 (DT-050/DT-063). JOIN sectores.

    Filtra ``alcance='local'`` y (opcional) ``segmento`` (`startup` para 2.1.3;
    ``solo_establecidas`` = segmento IS NULL para 2.1.2). Excluye ``descartado`` (RN-001).
    Trae los más notables por **tamaño** (prefetch) y los **re-rankea por SOLAPE** de sus
    actividad/vertical/descripción con los productos de la empresa analizada (DT-063): así una
    láctea ve Colanta/Alquería antes que un cárnico grande del mismo grupo. `productos_terms`
    vacío → orden por tamaño (fallback). Path GLOBAL (`list_competidores_by_sector`) aparte.

    DT-UI04b: ``sector_gics`` acepta uno o **varios** sectores (el grupo del LLM + el grupo
    canónico del CIIU, ver ``sectores_ancla_local``). Las filas de todos los sectores se juntan
    en un solo pool y compiten por solape de producto: así una eléctrica clasificada en 1010
    ve a sus pares curados de 5510 (EPM/Celsia/Isagen), no mineras. Se **deduplica por nombre
    normalizado** (una entidad multi-sector aparece una vez; también colapsa duplicados
    cross-sector como "ERCO ENERGIA"×2 hasta la reconciliación DT-050b).
    """
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
        "NULLIF(regexp_replace(split_part(a_ing.valor, ',', 1), '[^0-9]', '', 'g'), '')"
        "::bigint"
    )
    prefetch = max(limit * 10, 40) * len(sectores)
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
    # DT-UI04a: la empresa analizada no debe aparecer como jugador local propio.
    norm_excl = _clave_exclusion(exclude_nombre) if exclude_nombre else None
    if norm_excl:
        rows = [r for r in rows if _clave_exclusion(r[0]) != norm_excl]
    terms = productos_terms or set()

    def _clave(r):
        descriptor = f"{r[8] or ''} {r[2] or ''} {r[7] or ''}"
        return (
            -producto_overlap(descriptor, terms),
            not r[5],
            -(int(r[6]) if r[6] else 0),
        )

    # Dedup por nombre normalizado tras el re-rank; conserva el mejor-rankeado.
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
        )
        for r in deduped
    ]
