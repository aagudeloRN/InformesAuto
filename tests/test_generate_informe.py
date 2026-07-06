"""Tests para el orchestrator GenerateInforme."""

import pytest

from ic.domain.use_cases.generate_informe import (
    GenerateInforme,
    InformeParams,
    InformeResult,
    StepCallback,
)


def test_informe_params_defaults():
    p = InformeParams(empresa="Test S.A.")
    assert p.empresa == "Test S.A."
    assert p.ciiu is None
    assert p.output_path is None


def test_informe_params_with_ciiu():
    p = InformeParams(empresa="Test S.A.", ciiu="1081", output_path="/tmp/test.docx")
    assert p.ciiu == "1081"
    assert p.output_path == "/tmp/test.docx"


def test_generate_informe_accepts_settings(monkeypatch):
    """GenerateInforme se instancia correctamente con un settings mock."""
    class FakeSettings:
        ollama_base_url = "http://127.0.0.1:11434"
        database_url = "postgresql://user:pass@localhost/db"
        llm_budget_limit_usd = 1.0
        openrouter_api_key = ""
        llm_api_free_alt_model = ""
        docx_template_path = ""
        llm_local_embed_model = "nomic-embed-text"
        llm_local_draft_model = "qwen3:8b"
        llm_local_analytic_model = "qwen3:8b"

    uc = GenerateInforme(FakeSettings())
    assert uc.TOTAL_PASOS == 10


def test_generate_informe_on_step_signature():
    """StepCallback tiene la firma correcta: (int, int, str) -> None."""
    calls: list[tuple] = []

    def my_callback(n: int, total: int, label: str) -> None:
        calls.append((n, total, label))

    cb: StepCallback = my_callback
    cb(1, 10, "paso uno")
    assert calls == [(1, 10, "paso uno")]


def test_informe_result_fields():
    """InformeResult tiene todos los campos esperados por la UI."""
    r = InformeResult(
        ruta_docx="/tmp/test.docx",
        n_referencias=5,
        costo_usd=0.01,
        tokens_in=1000,
        tokens_out=500,
        tiempo_total_s=120.0,
        cost_records=[],
    )
    assert r.ruta_docx == "/tmp/test.docx"
    assert r.n_referencias == 5
    assert r.costo_usd == 0.01


@pytest.mark.slow
def test_generate_informe_e2e_noel(tmp_path):
    """E2E completo con servicios reales: Noel S.A.S."""
    import socket

    def _port_open(host, port):
        try:
            s = socket.create_connection((host, port), timeout=3)
            s.close()
            return True
        except OSError:
            return False

    if not _port_open("127.0.0.1", 11434):
        pytest.skip("Ollama no disponible")
    if not _port_open("localhost", 5434):
        pytest.skip("PostgreSQL no disponible")

    from ic.shared.config import get_settings

    settings = get_settings()
    uc = GenerateInforme(settings)
    params = InformeParams(
        empresa="Noel S.A.S.",
        output_path=str(tmp_path / "noel_informe.docx"),
    )
    result = uc.run(params)

    assert result.ruta_docx.endswith(".docx")
    from pathlib import Path
    assert Path(result.ruta_docx).exists()
    assert result.tiempo_total_s > 0
