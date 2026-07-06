import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ic.data.models.historial_informe import HistorialInforme
from ic.shared.constants import EstadoInforme


class InformeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, empresa_id: uuid.UUID, parametros: dict) -> HistorialInforme:
        informe = HistorialInforme(
            empresa_id=empresa_id,
            estado=EstadoInforme.PENDIENTE,
            parametros_entrada=parametros,
        )
        self._db.add(informe)
        self._db.commit()
        self._db.refresh(informe)
        return informe

    def update_estado(self, informe_id: uuid.UUID, estado: str) -> None:
        informe = self._db.get(HistorialInforme, informe_id)
        if informe is None:
            raise ValueError(f"Informe {informe_id} no encontrado")
        informe.estado = estado
        self._db.commit()

    def update_completado(
        self,
        informe_id: uuid.UUID,
        ruta_docx: str,
        costo: float,
        tiempo_s: float | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> None:
        informe = self._db.get(HistorialInforme, informe_id)
        if informe is None:
            raise ValueError(f"Informe {informe_id} no encontrado")
        informe.estado = EstadoInforme.COMPLETADO
        informe.ruta_documento_final = ruta_docx
        informe.costo_usd = costo
        if tiempo_s is not None:
            informe.tiempo_generacion_s = tiempo_s
        if tokens_in is not None:
            informe.tokens_in = tokens_in
        if tokens_out is not None:
            informe.tokens_out = tokens_out
        informe.completed_at = datetime.now(UTC)
        self._db.commit()

    def get_by_id(self, informe_id: uuid.UUID) -> HistorialInforme | None:
        return self._db.get(HistorialInforme, informe_id)
