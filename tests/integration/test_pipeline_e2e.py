"""Test de integraci?n E2E del pipeline completo (US1).

Marcado con @pytest.mark.integration para no ejecutarse en suite unitaria por defecto.
"""

from unittest.mock import MagicMock, patch

import pytest

from ic.domain.use_cases.generate_informe import GenerateInforme, InformeParams, InformeResult
from ic.shared.config import get_settings
from ic.shared.types import WebResult
from tests.integration.seed.fake_llm import EndlessFakeChatModel


@pytest.mark.integration
def test_pipeline_e2e_mocked_llm(tmp_path):
    """Valida la orquestaci?n completa E2E con PostgreSQL (o mocked DB) y LLM mockeado."""
    settings = get_settings().model_copy(
        update={
            "llm_budget_limit_usd": 10.0,
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
            url="https://example.com/noticia",
            title="Noticia",
            content="Contenido sectorial relevante sobre alimentos.",
            metadatos={
                "titulo": "Noticia",
                "fuente_nombre": "example.com",
                "a?o": "2024",
                "fecha_acceso": "2026-09-16",
                "autor": None,
            },
        )
    ]

    out_file = str(tmp_path / "informe_test_e2e.docx")
    params = InformeParams(
        empresa="Alpina S.A.S.",
        ciiu="1081",
        output_path=out_file,
        use_cache=False,
    )

    steps_recorded = []

    def on_step(n, total, label):
        steps_recorded.append((n, label))

    with (
        patch("ic.infrastructure.llm.gateway.build_llm", return_value=fake_llm),
        patch("ic.infrastructure.llm.gateway.build_resilient_api_llm", return_value=fake_llm),
        patch("ic.infrastructure.llm.gateway.build_api_llm", return_value=fake_llm),
        patch("ic.infrastructure.retrieval.embedder.Embedder", return_value=mock_embedder),
        patch("ic.infrastructure.sources.web_connector.WebConnector", return_value=mock_web),
    ):
        uc = GenerateInforme(settings)
        result = uc.run(params, on_step=on_step)

    assert isinstance(result, InformeResult)
    assert result.ruta_docx.endswith(".docx")
    assert len(steps_recorded) > 0
    assert result.tiempo_total_s > 0
