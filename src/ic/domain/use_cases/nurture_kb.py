"""Base viva del KB (DT-056/T4): cada corrida nutre el KB con la empresa principal.

Idea del usuario: ya pagamos el costo de describir la empresa analizada hoy → se reutiliza para
que, cuando mañana se analice otra empresa del mismo sector, esta ya esté disponible como
competidor anclado (cierra la causa D del diagnóstico: sin memoria entre corridas).

Gate anti-envenenamiento (RN-001), condición de diseño, no opcional:
- La **identidad** de la empresa (nombre + sector) la pide el usuario → entidad `verificado`
  (prioridad `usuario`).
- Los **campos enriquecidos** (descripción, derivada de web/LLM) entran como `candidato` con su
  procedencia → nunca se tratan como hecho verificado sin curación.

Domain: usa el repositorio (data), no toca SQLAlchemy directamente (TIER 1/3).
"""

from __future__ import annotations

import logging

from ic.data.models.entidad import (
    ESTADO_CANDIDATO,
    ESTADO_VERIFICADO,
    FUENTE_WEB,
    TIPO_EMPRESA,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow

logger = logging.getLogger(__name__)


def _normalizar(nombre: str) -> str:
    """Clave de dedup consistente con el NER (evita import de infraestructura en domain)."""
    from ic.infrastructure.ner.entity_recognizer import normalize_entity

    return normalize_entity(nombre)


class NurtureKB:
    def __init__(self, repo: EntidadRepository) -> None:
        self._repo = repo

    def execute(
        self,
        nombre: str,
        sector_gics: str | None,
        descripcion: str | None = None,
        fuente_descripcion: str = FUENTE_WEB,
    ) -> int | None:
        """Upsert de la empresa principal como entidad `verificado`; descripción como `candidato`.

        Idempotente (upsert por nombre+sector). Devuelve el id de la entidad, o None si el nombre
        está vacío (nunca fabrica una entidad sin nombre — RN-001).
        """
        if not nombre or not nombre.strip():
            return None
        entidad_id = self._repo.upsert_entidad(EntidadRow(
            nombre=nombre.strip(),
            nombre_normalizado=_normalizar(nombre),
            tipo=TIPO_EMPRESA,
            sector_gics=sector_gics or None,
            estado=ESTADO_VERIFICADO,  # identidad pedida por el usuario (prioridad usuario)
            aliases=[nombre.strip()],
        ))
        if descripcion and descripcion.strip():
            # Campo enriquecido: candidato con procedencia (web/LLM), no hecho verificado.
            self._repo.add_atributo(
                entidad_id, "descripcion", descripcion.strip()[:2000],
                fuente_descripcion, estado=ESTADO_CANDIDATO,
            )
        logger.info("KB nutrido con empresa principal '%s' (id=%s)", nombre, entidad_id)
        return entidad_id
