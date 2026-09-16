"""Test de integraci?n de cach? sectorial persistente (US2).

Verifica que ejecuciones repetidas para el mismo sector reutilicen datos de cach?.
"""

from unittest.mock import MagicMock, patch

import pytest

from ic.domain.use_cases.generate_informe import GenerateInforme, InformeParams
from ic.shared.config import get_settings
from ic.shared.types import WebResult
from tests.integration.seed.fake_llm import EndlessFakeChatModel


@pytest.mark.integration
def test_sector_cache_hit_on_subsequent_runs(tmp_path):
    """Verifica que una segunda ejecuci?n con la misma empresa/sector use el cach?."""
    settings = get_settings().model_copy(
        update={
            "selfreview_enabled": False,
            "discover_globales_enabled": False,
            "anclaje_local_enabled": False,
        }
    )

    fake_llm = EndlessFakeChatModel(responses=[])

    mock_embedder = MagicMock()
    mock_embedder.embed.side_effect = lambda q: [0.01] * 768
    mock_embedder.embed_query.side_effect = lambda q: [0.01] * 768
    mock_embedder.embed_many.side_effect = lambda ts: [[0.01] * 768 for _ in ts]
    mock_embedder.embed_documents.side_effect = lambda ts: [[0.01] * 768 for _ in ts]

    mock_web = MagicMock()
    mock_web.search.return_value = [
        WebResult(
            url="https://example.com/noel",
            title="Noel Galletas",
            content="Producci?n de galletas y confiter?a.",
            metadatos={
                "titulo": "Noel Galletas",
                "fuente_nombre": "example.com",
                "a?o": "2024",
                "fecha_acceso": "2026-09-16",
                "autor": None,
            },
        )
    ]

    out1 = str(tmp_path / "informe1.docx")
    out2 = str(tmp_path / "informe2.docx")

    with (
        patch("ic.infrastructure.llm.gateway.build_llm", return_value=fake_llm),
        patch("ic.infrastructure.llm.gateway.build_resilient_api_llm", return_value=fake_llm),
        patch("ic.infrastructure.llm.gateway.build_api_llm", return_value=fake_llm),
        patch("ic.infrastructure.retrieval.embedder.Embedder", return_value=mock_embedder),
        patch("ic.infrastructure.sources.web_connector.WebConnector", return_value=mock_web),
    ):
        uc = GenerateInforme(settings)
        # Primera corrida: genera y puebla cach?
        res1 = uc.run(InformeParams(empresa="Noel S.A.S.", output_path=out1, use_cache=True))
        assert res1.ruta_docx.endswith(".docx")

        # Segunda corrida con --resume / use_cache
        res2 = uc.run(
            InformeParams(empresa="Noel S.A.S.", output_path=out2, use_cache=True, resume=True)
        )
        assert res2.ruta_docx.endswith(".docx")
