import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from ic.domain.use_cases.ui_query_services import (
    add_competidor_manual,
    delete_documento_con_chunks,
    fetch_candidatos_competidores,
    list_documentos_indexados,
    list_empresas_conocidas,
    list_informes_recientes,
    mark_entidad_descartada,
    save_informe_feedback,
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
        metadatos={"año": "2023", "n_chunks": 12},
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
        assert res[0]["año"] == "2023"
        assert res[0]["n_chunks"] == 12
        assert res[0]["fecha"] == "2023-05-10 14:30"

        assert res[1]["id"] == str(doc2.id)
        assert res[1]["sector"] == "?"
        assert res[1]["activo"] is False
        assert res[1]["año"] == "?"
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


def test_fetch_candidatos_competidores():
    mock_local = MagicMock(nombre="Alpina")
    mock_start = MagicMock(nombre="FoodTech")

    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.data.models.entidad.ensure_entidades_tables"),
        patch("ic.data.repositories.entidad_repo.EntidadRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.list_competidores_by_sector.return_value = ["Nestle"]
        mock_repo.list_locales_by_sector.side_effect = [[mock_local], [mock_start]]
        mock_repo.get_id_by_nombre_sector.side_effect = [1, 2, 3]
        mock_repo_cls.return_value = mock_repo

        res = fetch_candidatos_competidores("Colanta", "302020")

        assert "globales" in res
        assert len(res["globales"]) == 1
        assert res["globales"][0]["nombre"] == "Nestle"

        assert len(res["regionales"]) == 1
        assert res["regionales"][0]["nombre"] == "Alpina"

        assert len(res["startups"]) == 1
        assert res["startups"][0]["nombre"] == "FoodTech"


def test_mark_entidad_descartada():
    with patch("ic.domain.use_cases.ui_query_services.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db

        res = mark_entidad_descartada(42)

        assert res is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


def test_add_competidor_manual():
    with (
        patch("ic.domain.use_cases.ui_query_services.SessionLocal"),
        patch("ic.data.models.entidad.ensure_entidades_tables"),
        patch("ic.data.repositories.entidad_repo.EntidadRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.upsert_entidad.return_value = 99
        mock_repo_cls.return_value = mock_repo

        res = add_competidor_manual("Nueva Empresa", "regional", "302020")

        assert res["id"] == 99
        assert res["nombre"] == "Nueva Empresa"
        assert res["tier"] == "regional"


def test_save_informe_feedback():
    inf_id = str(uuid.uuid4())
    with patch("ic.domain.use_cases.ui_query_services.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = "{}"
        mock_session_cls.return_value.__enter__.return_value = mock_db

        res = save_informe_feedback(inf_id, "Relevante", "Buen analisis")

        assert res is True
        assert mock_db.execute.call_count == 2
        mock_db.commit.assert_called_once()
