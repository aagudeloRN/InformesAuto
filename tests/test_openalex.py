"""Tests para OpenAlexConnector.

No realizan llamadas reales a la API — todo está mockeado
para no depender de disponibilidad externa ni consumir rate limit.
"""

from unittest.mock import MagicMock, patch

from ic.infrastructure.sources.openalex_connector import (
    OpenAlexConnector,
    _reconstruct_abstract,
)
from ic.shared.config import Settings


def _make_settings(email: str = "test@example.com") -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost:5434/db",
        db_schema="informes_ic",
        llm_local_embed_model="nomic-embed-text:latest",
        llm_local_draft_model="qwen2.5:7b",
        llm_local_analytic_model="qwen2.5:7b",
        openalex_email=email,
    )


_SAMPLE_WORK = {
    "id": "https://openalex.org/W123",
    "title": "Food industry trends in Latin America",
    "doi": "https://doi.org/10.1234/test",
    "publication_year": 2023,
    "cited_by_count": 42,
    "authorships": [{"author": {"display_name": "García Ramírez Juan"}}],
    "primary_location": {
        "source": {"display_name": "Journal of Food Science"}
    },
    "abstract_inverted_index": {
        "Food": [0],
        "trends": [1],
        "in": [2],
        "Colombia": [3],
    },
}


def _mock_response(works: list[dict], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {
        "meta": {"count": len(works), "per_page": len(works)},
        "results": works,
    }
    if status >= 400:
        import httpx
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestOpenAlexConnector:
    def test_search_returns_web_results(self):
        connector = OpenAlexConnector(_make_settings())
        with patch("httpx.get", return_value=_mock_response([_SAMPLE_WORK])):
            results = connector.search("food industry Colombia")
        assert len(results) == 1
        r = results[0]
        assert r.title == "Food industry trends in Latin America"
        assert r.url == "https://doi.org/10.1234/test"
        assert "Food trends in Colombia" in r.content

    def test_metadatos_apa_campos(self):
        connector = OpenAlexConnector(_make_settings())
        with patch("httpx.get", return_value=_mock_response([_SAMPLE_WORK])):
            results = connector.search("test")
        meta = results[0].metadatos
        assert meta["año"] == "2023"
        assert meta["fuente_nombre"] == "Journal of Food Science"
        assert meta["doi"] == "https://doi.org/10.1234/test"
        assert meta["cited_by_count"] == 42
        assert meta["autor"] is not None  # autor extraído de authorships

    def test_search_empty_on_503(self):
        """Si OpenAlex devuelve error, retorna lista vacía (no lanza excepción)."""
        connector = OpenAlexConnector(_make_settings())
        with patch("httpx.get", return_value=_mock_response([], status=503)):
            results = connector.search("cualquier cosa")
        assert results == []

    def test_search_empty_on_network_error(self):
        """Si hay error de red, retorna lista vacía."""
        import httpx
        connector = OpenAlexConnector(_make_settings())
        with patch("httpx.get", side_effect=httpx.RequestError("timeout")):
            results = connector.search("cualquier cosa")
        assert results == []

    def test_work_sin_abstract_usa_titulo(self):
        """Si el work no tiene abstract, el content usa título+fuente."""
        work_sin_abstract = {**_SAMPLE_WORK, "abstract_inverted_index": None}
        connector = OpenAlexConnector(_make_settings())
        with patch("httpx.get", return_value=_mock_response([work_sin_abstract])):
            results = connector.search("test")
        assert results[0].title in results[0].content

    def test_mailto_en_params(self):
        """El email de settings se envía como parámetro mailto."""
        connector = OpenAlexConnector(_make_settings(email="a.agudelo@rutan.org"))
        captured = {}
        with patch("httpx.get", return_value=_mock_response([])) as mock_get:
            connector.search("test")
            _, kwargs = mock_get.call_args
            captured = kwargs.get("params", {})
        assert captured.get("mailto") == "a.agudelo@rutan.org"

    def test_sin_email_no_mailto(self):
        """Sin email configurado, no se envía el parámetro mailto."""
        connector = OpenAlexConnector(_make_settings(email=""))
        with patch("httpx.get", return_value=_mock_response([])) as mock_get:
            connector.search("test")
            _, kwargs = mock_get.call_args
            params = kwargs.get("params", {})
        assert "mailto" not in params


class TestReconstructAbstract:
    def test_reconstruye_orden_correcto(self):
        index = {"Hello": [0], "world": [1], "food": [2]}
        result = _reconstruct_abstract(index)
        assert result == "Hello world food"

    def test_indice_vacio(self):
        assert _reconstruct_abstract({}) == ""

    def test_palabras_fuera_de_orden(self):
        index = {"second": [1], "first": [0], "third": [2]}
        result = _reconstruct_abstract(index)
        assert result == "first second third"
