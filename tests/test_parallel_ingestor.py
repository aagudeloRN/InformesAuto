"""Tests unitarios para ParallelIngestor (Spec 008 / US1)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from ic.infrastructure.sources.parallel_ingestor import (
    ParallelIngestor,
    TareaIngesta,
)


@pytest.fixture
def tareas_ejemplo():
    return [
        TareaIngesta(
            pdf_path="/tmp/test1.pdf",
            titulo="Doc 1",
            autor="Autor 1",
            año=2023,
            sector_gics="2530",
            tipo="PDF_SECTORIAL",
        ),
        TareaIngesta(
            pdf_path="/tmp/test2.pdf",
            titulo="Doc 2",
            autor="Autor 2",
            año=2024,
            sector_gics="2530",
            tipo="PDF_SECTORIAL",
        ),
    ]


def test_run_batch_success(tareas_ejemplo):
    settings = MagicMock()
    with patch("ic.infrastructure.sources.parallel_ingestor.PdfIngestor") as mock_ingestor_cls:
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_batched.return_value = 5
        mock_ingestor_cls.return_value = mock_ingestor

        ingestor = ParallelIngestor(settings=settings, max_workers=2)
        resultados = ingestor.run_batch(tareas_ejemplo)

        assert len(resultados) == 2
        assert all(r.estado == "ok" for r in resultados)
        assert all(r.n_chunks_creados == 5 for r in resultados)


def test_run_batch_isolated_failure(tareas_ejemplo):
    settings = MagicMock()

    def mock_ingest_batched(pdf_path, **kwargs):
        if "test1.pdf" in pdf_path:
            raise RuntimeError("Error al leer PDF corrupto")
        return 8

    with patch("ic.infrastructure.sources.parallel_ingestor.PdfIngestor") as mock_ingestor_cls:
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_batched.side_effect = mock_ingest_batched
        mock_ingestor_cls.return_value = mock_ingestor

        ingestor = ParallelIngestor(settings=settings, max_workers=2)
        resultados = ingestor.run_batch(tareas_ejemplo)

        assert len(resultados) == 2
        res_by_file = {r.archivo: r for r in resultados}
        assert res_by_file["test1.pdf"].estado == "error"
        assert "PDF corrupto" in res_by_file["test1.pdf"].error_msg
        assert res_by_file["test2.pdf"].estado == "ok"
        assert res_by_file["test2.pdf"].n_chunks_creados == 8


def test_run_batch_json_stdout(tareas_ejemplo, capsys):
    settings = MagicMock()
    with patch("ic.infrastructure.sources.parallel_ingestor.PdfIngestor") as mock_ingestor_cls:
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_batched.return_value = 3
        mock_ingestor_cls.return_value = mock_ingestor

        ingestor = ParallelIngestor(settings=settings, max_workers=1)
        ingestor.run_batch(tareas_ejemplo)

        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line]
        assert len(lines) == 2
        data = json.loads(lines[0])
        assert "archivo" in data
        assert "estado" in data
        assert "procesados" in data
