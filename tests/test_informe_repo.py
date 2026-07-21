"""Tests unitarios para InformeRepository (fast — sin BD real)."""

import uuid
from unittest.mock import MagicMock

from ic.data.repositories.informe_repo import InformeRepository


def _make_informe(id_: uuid.UUID | None = None):
    inf = MagicMock()
    inf.id = id_ or uuid.uuid4()
    return inf


class TestListRecientes:
    def test_list_recientes_llama_execute(self):
        db = MagicMock()
        db.execute.return_value.all.return_value = []
        repo = InformeRepository(db)
        result = repo.list_recientes()
        assert result == []
        db.execute.assert_called_once()

    def test_list_recientes_respeta_limit(self):
        db = MagicMock()
        db.execute.return_value.all.return_value = []
        repo = InformeRepository(db)
        repo.list_recientes(limit=5)
        call_args = db.execute.call_args[0][0]
        # La query debe contener LIMIT — verificamos en el string compilado
        assert "LIMIT" in str(call_args).upper()

    def test_list_recientes_desempaqueta_tuplas(self):
        inf = _make_informe()
        db = MagicMock()
        db.execute.return_value.all.return_value = [(inf, "Noel S.A.S.")]
        repo = InformeRepository(db)
        result = repo.list_recientes()
        assert len(result) == 1
        assert result[0][0] is inf
        assert result[0][1] == "Noel S.A.S."

    def test_list_recientes_aplica_offset(self):
        db = MagicMock()
        db.execute.return_value.all.return_value = []
        repo = InformeRepository(db)
        repo.list_recientes(limit=10, offset=10)
        call_args = str(db.execute.call_args[0][0]).upper()
        assert "OFFSET" in call_args

    def test_list_recientes_aplica_filtro_empresa(self):
        db = MagicMock()
        db.execute.return_value.all.return_value = []
        repo = InformeRepository(db)
        repo.list_recientes(empresa_filter="Noel")
        call_args = str(db.execute.call_args[0][0]).upper()
        assert "ILIKE" in call_args or "LIKE" in call_args
