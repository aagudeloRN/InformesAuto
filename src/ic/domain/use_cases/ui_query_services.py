"""Servicios de consulta y acciones UI para la capa de presentacion (SoC DT-038).

Desacopla la interfaz de usuario (Streamlit) de los repositorios y la base de datos,
retornando estructuras de datos estandar (dicts, tuples) sin acoplamiento a SQLAlchemy.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

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
                    "a?o": (d.metadatos or {}).get("a?o", (d.metadatos or {}).get("anio", "?")),
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
