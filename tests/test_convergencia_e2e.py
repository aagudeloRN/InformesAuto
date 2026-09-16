"""Test E2E para Cap5 Convergencia con chain_eje (3 ejes paralelos).

Valida DT-005: el path paralelo (ThreadPoolExecutor) genera texto coherente
y termina en < 30 min vs los ~79 min del camino monolítico legacy.

Requiere Ollama (11434) + PostgreSQL (5434) activos. Se omite automáticamente
si alguno no está disponible.
"""

import socket
import time

import pytest


def _port_open(host: str, port: int) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=3)
        s.close()
        return True
    except OSError:
        return False


@pytest.mark.slow
def test_cap5_paralelo_e2e():
    """Cap5 con 3 ejes paralelos produce texto coherente en < 30 min (DT-005)."""
    if not _port_open("127.0.0.1", 11434):
        pytest.skip("Ollama no disponible")
    if not _port_open("localhost", 5434):
        pytest.skip("PostgreSQL no disponible")

    from ic.data.database import SessionLocal
    from ic.data.repositories.embedding_repo import EmbeddingRepository
    from ic.domain.chains.chain_06_convergencia import build_chain_06_synth
    from ic.domain.chains.chain_06a_convergencia_eje import build_chain_06a
    from ic.domain.use_cases.generate_convergencia import GenerateConvergencia
    from ic.infrastructure.llm.gateway import CostTracker, build_api_llm
    from ic.infrastructure.retrieval.embedder import Embedder
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.web_connector import WebConnector
    from ic.shared.config import get_settings

    settings = get_settings()
    tracker = CostTracker(budget_limit=settings.llm_budget_limit_usd)
    api_llm = build_api_llm(settings, tier="free", cost_tracker=tracker)
    embedder = Embedder(settings)

    with SessionLocal() as db:
        repo = EmbeddingRepository(db)
        store = PGVectorStore(embedder, repo, settings)
        web = WebConnector(settings)

        uc = GenerateConvergencia(
            chain=build_chain_06_synth(api_llm),
            chain_eje=build_chain_06a(api_llm),
            store=store,
            web_connector=web,
        )

        t0 = time.time()
        result = uc.execute(
            nombre_empresa="Noel S.A.S.",
            descripcion_empresa=(
                "Empresa colombiana de alimentos procesados líder en snacks, "
                "galletas y confitería. Opera en Colombia y exporta a países "
                "de América Latina."
            ),
            sector_gics="Consumer Staples — Food Products",
        )
        elapsed = time.time() - t0

    assert result.texto, "Cap 5 debe tener texto no vacío"
    assert len(result.texto) >= 500, (
        f"Texto demasiado corto: {len(result.texto)} chars — "
        "esperado ≥500 para un capítulo completo"
    )
    secciones = [s for s in result.texto.split("\n\n") if s.strip()]
    assert len(secciones) >= 3, f"Se esperan ≥3 secciones (una por eje), hay {len(secciones)}"
    assert elapsed < 30 * 60, f"Cap5 paralelo tardó {elapsed:.0f}s — límite 30 min (1800s)"
