"""Tests para EmpresaRepository (fast, mocked — sin BD real)."""

import uuid
from unittest.mock import MagicMock

from ic.data.repositories.empresa_repo import EmpresaRepository


def _make_repo():
    db = MagicMock()
    return EmpresaRepository(db), db


def test_upsert_returns_existing_when_found():
    repo, db = _make_repo()
    fake_empresa = MagicMock()
    fake_empresa.id = uuid.uuid4()
    fake_empresa.nombre = "Noel S.A.S."
    db.execute.return_value.scalar_one_or_none.return_value = fake_empresa

    result = repo.upsert_by_name("Noel S.A.S.")

    assert result is fake_empresa
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_upsert_creates_when_not_found():
    repo, db = _make_repo()
    db.execute.return_value.scalar_one_or_none.return_value = None

    repo.upsert_by_name("Nueva Empresa S.A.")

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_upsert_idempotente_returns_same_id():
    """Dos llamadas con el mismo nombre deben devolver el mismo objeto."""
    repo, db = _make_repo()
    fake_empresa = MagicMock()
    fake_empresa.id = uuid.uuid4()
    db.execute.return_value.scalar_one_or_none.return_value = fake_empresa

    r1 = repo.upsert_by_name("Empresa Repetida")
    r2 = repo.upsert_by_name("Empresa Repetida")

    assert r1.id == r2.id
    db.add.assert_not_called()


def test_get_by_id_delegates_to_db():
    repo, db = _make_repo()
    empresa_id = uuid.uuid4()
    fake_empresa = MagicMock()
    db.get.return_value = fake_empresa

    result = repo.get_by_id(empresa_id)

    assert result is fake_empresa
    db.get.assert_called_once()


def test_historial_update_completado_saves_tokens():
    """InformeRepository.update_completado persiste tokens_in y tokens_out."""
    from ic.data.repositories.informe_repo import InformeRepository
    from ic.shared.constants import EstadoInforme

    informe_id = uuid.uuid4()
    fake_informe = MagicMock()
    fake_informe.estado = EstadoInforme.PENDIENTE

    db = MagicMock()
    db.get.return_value = fake_informe

    repo = InformeRepository(db)
    repo.update_completado(
        informe_id=informe_id,
        ruta_docx="/tmp/test.docx",
        costo=0.0,
        tiempo_s=120.5,
        tokens_in=1000,
        tokens_out=500,
    )

    assert fake_informe.tokens_in == 1000
    assert fake_informe.tokens_out == 500
    assert fake_informe.estado == EstadoInforme.COMPLETADO
    db.commit.assert_called_once()
