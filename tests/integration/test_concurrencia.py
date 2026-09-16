"""Test de integraci?n de concurrencia y thread-safety en Cap 2.1 (US3)."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ic.domain.use_cases._informe_context import InformeParams, _PipelineContext
from ic.domain.use_cases.generate_n1 import run_n1_parallel
from ic.shared.config import get_settings


@pytest.mark.integration
def test_cap21_thread_concurrency():
    """Valida ejecuci?n concurrente multi-hilo en la fase N1 sin colisiones ni memory corruption."""
    settings = get_settings()

    mock_llm = MagicMock()

    def _gen(*args, **kwargs):
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="An?lisis concurrente v?lido."))]
        )

    mock_llm._generate = MagicMock(side_effect=_gen)

    ctx = _PipelineContext(
        params=InformeParams(empresa="Nutresa S.A.", ciiu="1081"),
        settings=settings,
        step_fn=MagicMock(),
        total_start=0.0,
        session_id="test-concurrency-sess",
        api_llm=mock_llm,
        api_llm_synth=mock_llm,
        llm=mock_llm,
        empresa=MagicMock(
            texto="Empresa colombiana l?der en alimentos.",
            productos_servicios="Galletas, caf?, pastas",
        ),
        gics=MagicMock(grupo_gics="3020 - Alimentos, Bebidas y Tabaco"),
    )

    # Ejecutar N1
    with (
        patch("ic.domain.use_cases.generate_benchmarking.GenerateBenchmarking") as mock_bench,
        patch("ic.domain.use_cases.generate_tendencias.GenerateTendencias") as mock_tend,
        patch("ic.domain.use_cases.generate_ecosistema.GenerateEcosistema") as mock_eco,
        patch("ic.domain.use_cases.generate_mercado.GenerateMercado") as mock_mercado,
    ):
        mock_bench.return_value.execute.return_value = MagicMock(
            texto="Benchmarking ok", chunks_usados=[]
        )
        mock_tend.return_value.execute.return_value = MagicMock(
            texto="Tendencias ok", chunks_usados=[]
        )
        mock_eco.return_value.execute.return_value = MagicMock(
            texto="Ecosistema ok", chunks_usados=[]
        )
        mock_mercado.return_value.execute.return_value = MagicMock(
            texto="Mercado ok", chunks_usados=[]
        )

        run_n1_parallel(ctx)

    assert ctx.cap is not None
    assert ctx.cap_tend is not None
    assert ctx.cap_eco is not None
    assert ctx.cap_mercado is not None
