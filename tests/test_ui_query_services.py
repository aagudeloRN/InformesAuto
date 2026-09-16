import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from ic.domain.use_cases.ui_query_services import (
    delete_documento_con_chunks,
    list_documentos_indexados,
    list_empresas_conocidas,
    list_informes_recientes,
    set_documento_activo,
)


def test_list_empresas_conocidas_success():
    emp1 = MagicMock(id=uuid.uuid4(), nombre="Nutresa")
    emp2 = MagicMock(id=uuid.uuid4(), nombre="Bancolombia")

    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.domain.use_cases.ui_query_services.EmpresaRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.list_all.return_value = [emp1, emp2]
        mock_repo_cls.return_value = mock_repo

        result = list_empresas_conocidas()

        assert len(result) == 3
        assert result[0] == ("", "? ninguna (documento sectorial) ?")
        assert result[1] == (str(emp1.id), "Nutresa")
        assert result[2] == (str(emp2.id), "Bancolombia")


def test_list_empresas_conocidas_without_empty():
    emp1 = MagicMock(id=uuid.uuid4(), nombre="Nutresa")

    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.domain.use_cases.ui_query_services.EmpresaRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.list_all.return_value = [emp1]
        mock_repo_cls.return_value = mock_repo

        result = list_empresas_conocidas(include_empty=False)

        assert len(result) == 1
        assert result[0] == (str(emp1.id), "Nutresa")


def test_list_empresas_conocidas_error_fallback():
    with patch(
        "ic.domain.use_cases.ui_query_services.SessionLocal", side_effect=Exception("DB down")
    ):
        result = list_empresas_conocidas()
        assert result == [("", "? ninguna (documento sectorial) ?")]


def test_list_documentos_indexados():
    doc1 = MagicMock(
        id=uuid.uuid4(),
        nombre_archivo="informe.pdf",
        tipo="financiero",
        sector_gics="302020",
        activo=True,
        metadatos={"a?o": "2023", "n_chunks": 12},
        created_at=datetime(2023, 5, 10, 14, 30),
    )
    doc2 = MagicMock(
        id=uuid.uuid4(),
        nombre_archivo="sector.pdf",
        tipo="sectorial",
        sector_gics=None,
        activo=False,
        metadatos=None,
        created_at=None,
    )

    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.domain.use_cases.ui_query_services.DocumentoRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.list_all.return_value = [doc1, doc2]
        mock_repo_cls.return_value = mock_repo

        res = list_documentos_indexados()

        assert len(res) == 2
        assert res[0]["id"] == str(doc1.id)
        assert res[0]["nombre"] == "informe.pdf"
        assert res[0]["activo"] is True
        assert res[0]["a?o"] == "2023"
        assert res[0]["n_chunks"] == 12
        assert res[0]["fecha"] == "2023-05-10 14:30"

        assert res[1]["id"] == str(doc2.id)
        assert res[1]["sector"] == "?"
        assert res[1]["activo"] is False
        assert res[1]["a?o"] == "?"
        assert res[1]["n_chunks"] == "?"
        assert res[1]["fecha"] == "?"


def test_list_documentos_indexados_error():
    with patch(
        "ic.domain.use_cases.ui_query_services.SessionLocal", side_effect=Exception("DB error")
    ):
        res = list_documentos_indexados()
        assert res == []


def test_list_informes_recientes():
    inf_mock = MagicMock(
        id=uuid.uuid4(),
        created_at=datetime(2024, 1, 15, 10, 0),
        estado=MagicMock(value="COMPLETO"),
        costo_usd=0.045,
        tiempo_generacion_s=12.5,
        metricas_fiabilidad={"score": 0.95},
        ruta_documento_final="/tmp/out.docx",
    )
    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.domain.use_cases.ui_query_services.InformeRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.list_recientes.return_value = [(inf_mock, "Nutresa")]
        mock_repo_cls.return_value = mock_repo

        res = list_informes_recientes(limit=5, offset=10, empresa_filter="Nutresa")

        mock_repo.list_recientes.assert_called_once_with(
            limit=5, offset=10, empresa_filter="Nutresa"
        )
        assert len(res) == 1
        assert res[0]["id"] == str(inf_mock.id)
        assert res[0]["empresa_nombre"] == "Nutresa"
        assert res[0]["estado"] == "COMPLETO"
        assert res[0]["costo_usd"] == 0.045
        assert res[0]["fecha"] == "2024-01-15 10:00"


def test_set_documento_activo():
    doc_id = uuid.uuid4()
    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.domain.use_cases.ui_query_services.DocumentoRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        success = set_documento_activo(str(doc_id), False)

        mock_repo.set_activo.assert_called_once_with(doc_id, False)
        assert success is True


def test_delete_documento_con_chunks():
    doc_id = uuid.uuid4()
    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.domain.use_cases.ui_query_services.DocumentoRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.delete_with_chunks.return_value = 15
        mock_repo_cls.return_value = mock_repo

        deleted_chunks = delete_documento_con_chunks(str(doc_id))

        mock_repo.delete_with_chunks.assert_called_once_with(doc_id)
        assert deleted_chunks == 15
