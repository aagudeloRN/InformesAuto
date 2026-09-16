"""Orchestrator use case: genera el informe completo de IC (Caps 1-6 + Resumen) (DT-039).

El progreso se reporta v?a callback `on_step(n, total, label)` para desacoplar la
ejecuci?n del concern de presentaci?n (CLI, Streamlit, tests).
"""

from __future__ import annotations

import logging
import time

from ic.domain.use_cases import checkpoint_hooks
from ic.domain.use_cases._informe_context import (
    InformeParams,
    InformeResult,
    StepCallback,
    _PipelineContext,
    setup_pipeline_infra,
    sweep_stale_web,
)
from ic.domain.use_cases._informe_nodes_n0 import run_n0, run_n1
from ic.domain.use_cases._informe_nodes_n2 import run_n2
from ic.domain.use_cases._informe_nodes_n3 import run_n3
from ic.shared.config import Settings

logger = logging.getLogger(__name__)

__all__ = [
    "GenerateInforme",
    "InformeParams",
    "InformeResult",
    "StepCallback",
    "_PipelineContext",
]


class GenerateInforme:
    """Orquesta el pipeline completo: Cap 1 ? GICS ? N1 paralelo ? N2 ? N3 ? .docx."""

    TOTAL_PASOS = 10

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run(
        self,
        params: InformeParams,
        on_step: StepCallback | None = None,
    ) -> InformeResult:
        import logging as _logging

        _logging.getLogger("sqlalchemy.engine").setLevel(_logging.WARNING)
        _logging.getLogger("httpx").setLevel(_logging.WARNING)
        _logging.getLogger("httpcore").setLevel(_logging.WARNING)

        def _step(n: int, label: str) -> None:
            if on_step:
                on_step(n, self.TOTAL_PASOS, label)

        ctx = setup_pipeline_infra(self._settings, params, _step, time.time())
        # Fase 1: --refresh invalida el cach? durable al arrancar ? regenera todo desde cero.
        if params.refresh:
            checkpoint_hooks.clear(ctx)
        checkpoint_hooks.load(ctx)
        sweep_stale_web(ctx)
        run_n0(ctx)
        run_n1(ctx)
        run_n2(ctx)
        return run_n3(ctx)

    def _sweep_stale_web(self, ctx: _PipelineContext) -> None:
        sweep_stale_web(ctx)

    def _promote_cited_web(self, ctx: _PipelineContext, chunks_usados: list) -> None:
        from ic.domain.use_cases._informe_context import promote_cited_web

        promote_cited_web(ctx, chunks_usados)
