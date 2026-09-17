"""Servicios de consulta y acciones UI para la capa de presentacion (SoC DT-038).

Desacopla la interfaz de usuario (Streamlit) de los repositorios y la base de datos,
retornando estructuras de datos estandar (dicts, tuples) sin acoplamiento a SQLAlchemy.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from ic.data.database import SessionLocal
from ic.data.repositories.documento_repo import DocumentoRepository
from ic.data.repositories.empresa_repo import EmpresaRepository
from ic.data.repositories.informe_repo import InformeRepository

logger = logging.getLogger(__name__)


def list_empresas_conocidas(include_empty: bool = True) -> list[tuple[str, str]]:
    """Retorna lista de (id_str, nombre) de empresas conocidas."""
    base: list[tuple[str, str]] = (
        [("", "? ninguna (documento sectorial) ?")] if include_empty else []
    )
    try:
        with SessionLocal() as db:
            repo = EmpresaRepository(db)
            return base + [(str(emp.id), emp.nombre) for emp in repo.list_all()]
    except Exception as exc:
        logger.warning("Error al consultar empresas conocidas: %s", exc)
        return base


def list_documentos_indexados() -> list[dict[str, Any]]:
    """Retorna lista de documentos indexados como diccionarios con formato para UI."""
    try:
        with SessionLocal() as db:
            repo = DocumentoRepository(db)
            docs = repo.list_all()
            return [
                {
                    "id": str(d.id),
                    "nombre": d.nombre_archivo,
                    "tipo": d.tipo,
                    "sector": d.sector_gics or "?",
                    "activo": bool(d.activo),
                    "año": (d.metadatos or {}).get("año", (d.metadatos or {}).get("anio", "?")),
                    "n_chunks": (d.metadatos or {}).get("n_chunks", "?"),
                    "fecha": d.created_at.strftime("%Y-%m-%d %H:%M")
                    if getattr(d, "created_at", None)
                    else "?",
                }
                for d in docs
            ]
    except Exception as exc:
        logger.warning("Error al consultar documentos indexados: %s", exc)
        return []


def list_informes_recientes(
    limit: int = 10, offset: int = 0, empresa_filter: str | None = None
) -> list[dict[str, Any]]:
    """Retorna lista de informes recientes como diccionarios con formato para UI."""
    try:
        with SessionLocal() as db:
            repo = InformeRepository(db)
            rows = repo.list_recientes(limit=limit, offset=offset, empresa_filter=empresa_filter)
            return [
                {
                    "id": str(inf.id),
                    "empresa_nombre": emp,
                    "fecha": inf.created_at.strftime("%Y-%m-%d %H:%M")
                    if getattr(inf, "created_at", None)
                    else "?",
                    "estado": inf.estado.value if hasattr(inf.estado, "value") else str(inf.estado),
                    "costo_usd": inf.costo_usd,
                    "tiempo_generacion_s": inf.tiempo_generacion_s,
                    "metricas_fiabilidad": inf.metricas_fiabilidad or {},
                    "ruta_documento_final": inf.ruta_documento_final,
                }
                for inf, emp in rows
            ]
    except Exception as exc:
        logger.warning("Error al consultar informes recientes: %s", exc)
        return []


def set_documento_activo(doc_id: str, activo: bool) -> bool:
    """Activa o desactiva un documento en el repositorio."""
    try:
        with SessionLocal() as db:
            repo = DocumentoRepository(db)
            repo.set_activo(uuid.UUID(doc_id), activo)
            return True
    except Exception as exc:
        logger.warning("Error al actualizar estado del documento %s: %s", doc_id, exc)
        return False


def delete_documento_con_chunks(doc_id: str) -> int:
    """Elimina un documento y sus chunks asociados."""
    try:
        with SessionLocal() as db:
            repo = DocumentoRepository(db)
            return repo.delete_with_chunks(uuid.UUID(doc_id))
    except Exception as exc:
        logger.warning("Error al eliminar documento %s: %s", doc_id, exc)
        return 0


def fetch_candidatos_competidores(
    empresa: str, sector_gics: str, ciiu: str | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Consulta los competidores candidatos preliminares por tiers para HITL."""
    from ic.data.models.entidad import ALCANCE_GLOBAL, SEGMENTO_STARTUP, ensure_entidades_tables
    from ic.data.repositories.entidad_repo import EntidadRepository

    resultado: dict[str, list[dict[str, Any]]] = {
        "globales": [],
        "regionales": [],
        "startups": [],
    }
    if not sector_gics and not ciiu:
        return resultado

    try:
        with SessionLocal() as db:
            ensure_entidades_tables(db.get_bind())
            repo = EntidadRepository(db)
            sectores = [sector_gics] if sector_gics else []

            # 1. Globales
            glob_names = repo.list_competidores_by_sector(
                sectores, alcance=ALCANCE_GLOBAL, exclude_nombre=empresa, limit=10
            )
            for nombre in glob_names:
                ent_id = repo.get_id_by_nombre_sector(nombre, sector_gics)
                resultado["globales"].append(
                    {"id": ent_id, "nombre": nombre, "origen": "KB Global", "tier": "global"}
                )

            # 2. Regionales
            reg_rows = repo.list_locales_by_sector(
                sectores, solo_establecidas=True, exclude_nombre=empresa, limit=8
            )
            for r in reg_rows:
                ent_id = repo.get_id_by_nombre_sector(r.nombre, sector_gics)
                resultado["regionales"].append(
                    {
                        "id": ent_id,
                        "nombre": r.nombre,
                        "origen": "Directorio Local",
                        "tier": "regional",
                    }
                )

            # 3. Startups
            start_rows = repo.list_locales_by_sector(
                sectores, segmento=SEGMENTO_STARTUP, exclude_nombre=empresa, limit=8
            )
            for r in start_rows:
                ent_id = repo.get_id_by_nombre_sector(r.nombre, sector_gics)
                resultado["startups"].append(
                    {
                        "id": ent_id,
                        "nombre": r.nombre,
                        "origen": "StartIA / Ecosistema",
                        "tier": "startup",
                    }
                )
    except Exception as exc:
        logger.warning("Error al consultar candidatos preliminares de competidores: %s", exc)

    return resultado


def mark_entidad_descartada(entidad_id: int) -> bool:
    """Marca una entidad como descartada permanentemente en el KB.

    NOTA: Utilidad de curacion manual de BD. NO debe ser invocada por el flujo HITL
    de la UI (que maneja descartes unicamente en `st.session_state` / `InformeParams`).
    """
    from ic.data.models.entidad import ESTADO_DESCARTADO, Entidad

    try:
        with SessionLocal() as db:
            ent = Entidad.__table__.fullname
            sql = text(f"UPDATE {ent} SET estado = :desc, updated_at = now() WHERE id = :id")
            db.execute(sql, {"desc": ESTADO_DESCARTADO, "id": entidad_id})
            db.commit()
            return True
    except Exception as exc:
        logger.warning("Error al marcar entidad %d como descartada: %s", entidad_id, exc)
        return False


def add_competidor_manual(nombre: str, tier: str, sector_gics: str | None = None) -> dict[str, Any]:
    """Registra o estructura un competidor manual ingresado por el analista."""
    from ic.data.models.entidad import (
        ESTADO_VERIFICADO,
        TIPO_COMPETIDOR,
        ensure_entidades_tables,
    )
    from ic.data.repositories._entidad_queries import EntidadRow
    from ic.data.repositories.entidad_repo import EntidadRepository
    from ic.infrastructure.ner.entity_recognizer import normalize_entity

    nombre_clean = nombre.strip()
    tier_clean = tier.lower().strip()
    try:
        with SessionLocal() as db:
            ensure_entidades_tables(db.get_bind())
            repo = EntidadRepository(db)
            eid = repo.upsert_entidad(
                EntidadRow(
                    nombre=nombre_clean,
                    nombre_normalizado=normalize_entity(nombre_clean),
                    tipo=TIPO_COMPETIDOR,
                    sector_gics=sector_gics,
                    estado=ESTADO_VERIFICADO,
                    segmento="startup" if tier_clean == "startup" else None,
                )
            )
            return {
                "id": eid,
                "nombre": nombre_clean,
                "origen": "Manual (Analista)",
                "tier": tier_clean,
            }
    except Exception as exc:
        logger.warning("Error al agregar competidor manual '%s': %s", nombre, exc)
        return {
            "id": None,
            "nombre": nombre_clean,
            "origen": "Manual (Analista)",
            "tier": tier_clean,
        }


def save_informe_feedback(informe_id: str, rating: str, comentario: str | None = None) -> bool:
    """Persiste el feedback rapido de calidad del analista en el historial (Spec 007 / US3)."""
    from ic.data.models.historial_informe import HistorialInforme

    try:
        with SessionLocal() as db:
            inf = HistorialInforme.__table__.fullname
            sql_sel = text(f"SELECT metricas_fiabilidad FROM {inf} WHERE id = CAST(:id AS uuid)")
            curr_raw = db.execute(sql_sel, {"id": informe_id}).scalar() or {}
            curr = json.loads(curr_raw) if isinstance(curr_raw, str) else dict(curr_raw)

            curr["user_feedback"] = {
                "rating": rating,
                "comentario": comentario.strip() if comentario else "",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            sql_upd = text(
                f"UPDATE {inf} SET metricas_fiabilidad = CAST(:meta AS jsonb), "
                "updated_at = now() WHERE id = CAST(:id AS uuid)"
            )
            db.execute(sql_upd, {"meta": json.dumps(curr), "id": informe_id})
            db.commit()
            return True
    except Exception as exc:
        logger.warning("Error al guardar feedback para informe %s: %s", informe_id, exc)
        return False
