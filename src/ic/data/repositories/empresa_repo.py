import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ic.data.models.empresa import Empresa


class EmpresaRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_by_name(self, nombre: str) -> Empresa:
        """Busca empresa por nombre exacto; crea si no existe. Idempotente."""
        existing = self._db.execute(
            select(Empresa).where(Empresa.nombre == nombre)
        ).scalar_one_or_none()
        if existing:
            return existing
        empresa = Empresa(nombre=nombre)
        self._db.add(empresa)
        self._db.commit()
        self._db.refresh(empresa)
        return empresa

    def get_by_id(self, empresa_id: uuid.UUID) -> Empresa | None:
        return self._db.get(Empresa, empresa_id)

    def list_all(self) -> list[Empresa]:
        return list(self._db.execute(select(Empresa).order_by(Empresa.nombre)).scalars())
