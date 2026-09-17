"""Caso de uso de reconciliacion canonica de entidades por NIT (DT-050b).

Identifica entidades duplicadas que comparten el mismo NIT no nulo/vacio/'0' y las fusiona
en una unica entidad canonica determinista, reasignando sus membresias y atributos,
consolidando sus nombres variantes en `aliases` (JSONB) y eliminando duplicados.
"""

from __future__ import annotations

import logging
from typing import Any

from ic.data.models.entidad import ESTADO_VERIFICADO
from ic.data.repositories.entidad_repo import EntidadRepository

logger = logging.getLogger(__name__)


def _select_canonical_entity(
    miembros: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Selecciona la entidad canonica segun la regla determinista (Q4 Spec 007).

    Criterio de prioridad:
    1. Estado `verificado` > `candidato`
    2. Mayor `n_atributos` (con fallback a `n_menciones`)
    3. Mayor longitud del nombre
    4. Mayor `id` como tiebreaker
    """

    def key_fn(item: dict[str, Any]) -> tuple[int, int, int, int]:
        es_verificado = 1 if item.get("estado") == ESTADO_VERIFICADO else 0
        n_attrs = item.get("n_atributos")
        n_atributos = int(n_attrs) if n_attrs is not None else int(item.get("n_menciones") or 0)
        len_nombre = len(str(item.get("nombre") or ""))
        ent_id = int(item.get("id") or 0)
        return (es_verificado, n_atributos, len_nombre, ent_id)

    sorted_miembros = sorted(miembros, key=key_fn, reverse=True)
    canonical = sorted_miembros[0]
    duplicates = sorted_miembros[1:]
    return canonical, duplicates


class ReconcileEntidades:
    """Ejecuta la reconciliacion de entidades por NIT."""

    def __init__(self, repo: EntidadRepository) -> None:
        self.repo = repo

    def reconcile(self, dry_run: bool = False) -> dict[str, Any]:
        """Busca y fusiona grupos de duplicados por NIT.

        Args:
            dry_run: Si es True, simula la fusion sin modificar la base de datos.

        Returns:
            Dict con estadisticas de grupos procesados y entidades fusionadas.
        """
        grupos = self.repo.list_duplicados_por_nit()
        total_grupos = len(grupos)
        total_fusionadas = 0
        resumen_grupos: list[dict[str, Any]] = []

        for g in grupos:
            nit = g["nit"]
            miembros = g["miembros"]
            if len(miembros) < 2:
                continue

            canonical, duplicates = _select_canonical_entity(miembros)
            dup_ids = [d["id"] for d in duplicates]
            total_fusionadas += len(dup_ids)

            info_grupo = {
                "nit": nit,
                "canonica_id": canonical["id"],
                "canonica_nombre": canonical["nombre"],
                "duplicados_ids": dup_ids,
                "duplicados_nombres": [d["nombre"] for d in duplicates],
            }
            resumen_grupos.append(info_grupo)

            if not dry_run:
                logger.info(
                    "Fusionando NIT %s: canonica #%d (%s) <- duplicados %s",
                    nit,
                    canonical["id"],
                    canonical["nombre"],
                    dup_ids,
                )
                self.repo.merge_entidades_por_nit(canonical["id"], dup_ids)

        return {
            "total_grupos": total_grupos,
            "total_fusionadas": total_fusionadas,
            "dry_run": dry_run,
            "grupos": resumen_grupos,
        }
