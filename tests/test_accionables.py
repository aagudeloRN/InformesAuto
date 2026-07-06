"""Tests para Cap 6 — Accionables Estratégicos.

Todos los tests usan mocks — sin llamadas reales a OpenRouter ni pgvector.
"""

from unittest.mock import MagicMock

from ic.domain.chains.chain_07_accionables import build_chain_07, format_chunks_as_context
from ic.domain.use_cases.generate_accionables import GenerateAccionables
from ic.shared.types import CapAccionables, ChunkResult


def _make_chunk(texto: str, url: str = "https://ejemplo.com", score: float = 0.85) -> ChunkResult:
    return ChunkResult(
        chunk_texto=texto,
        fuente_tipo="web",
        fuente_url=url,
        score=score,
        metadatos={"titulo": "Prueba", "año": "2025", "autor": None},
    )


class TestChain07:
    def test_build_chain_07_returns_runnable(self):
        mock_llm = MagicMock()
        mock_llm.__or__ = MagicMock(return_value=MagicMock())
        chain = build_chain_07(mock_llm)
        assert chain is not None

    def test_format_chunks_numera_correctamente(self):
        chunks = [_make_chunk(f"Hallazgo {i}", f"https://x.com/{i}") for i in range(3)]
        result = format_chunks_as_context(chunks)
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result


class TestGenerateAccionables:
    def _make_uc(
        self, texto_llm: str = "Cap 6 generado.", chunks: list | None = None
    ) -> GenerateAccionables:
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = texto_llm

        mock_store = MagicMock()
        mock_store.search.return_value = chunks or [
            _make_chunk(f"Chunk {i}", f"https://x.com/{i}") for i in range(7)
        ]

        return GenerateAccionables(chain=mock_chain, store=mock_store)

    def test_execute_retorna_cap_accionables(self):
        uc = self._make_uc("Texto de los 6 accionables.")
        result = uc.execute("Noel S.A.S.", "Empresa de galletas.", "Alimentos")
        assert isinstance(result, CapAccionables)
        assert result.retrieval_suficiente
        assert result.texto == "Texto de los 6 accionables."

    def test_execute_llama_chain_con_retrieval_cruzado(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk(f"c{i}") for i in range(7)]

        uc = GenerateAccionables(mock_chain, mock_store)
        uc.execute("Noel", "Empresa.", "Alimentos")

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "descripcion_empresa" in call_kwargs
        assert "sector_gics" in call_kwargs
        assert "retrieval_cruzado" in call_kwargs

    def test_execute_parrafo_ausencia_si_retrieval_insuficiente(self):
        uc = self._make_uc(chunks=[_make_chunk(f"c{i}") for i in range(3)])
        result = uc.execute("Empresa X", "Desc.", "Sector")
        assert not result.retrieval_suficiente
        assert result.n_chunks_usados == 0
        assert "Cap 6" in result.texto

    def test_execute_no_invoca_chain_si_retrieval_insuficiente(self):
        mock_chain = MagicMock()
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk("solo uno")]

        uc = GenerateAccionables(mock_chain, mock_store)
        uc.execute("Empresa", "Desc.", "Sector")
        mock_chain.invoke.assert_not_called()

    def test_execute_sin_web_connector(self):
        """GenerateAccionables no tiene web_connector — instancia sin ese argumento."""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk(f"c{i}") for i in range(7)]

        uc = GenerateAccionables(chain=mock_chain, store=mock_store)
        result = uc.execute("Empresa", "Desc.", "Sector")
        assert isinstance(result, CapAccionables)
        assert not hasattr(uc, "_web")
