"""Tests para Cap 5 — Convergencia Empresarial.

Todos los tests usan mocks — sin llamadas reales a OpenRouter ni Tavily.
"""

from unittest.mock import MagicMock, call

from ic.domain.chains.chain_06_convergencia import (
    build_chain_06,
    format_chunks_as_context,
)
from ic.domain.use_cases.generate_convergencia import GenerateConvergencia
from ic.shared.types import CapConvergencia, ChunkResult, WebResult


def _make_chunk(texto: str, url: str = "https://ejemplo.com", score: float = 0.85) -> ChunkResult:
    return ChunkResult(
        chunk_texto=texto,
        fuente_tipo="web",
        fuente_url=url,
        score=score,
        metadatos={"titulo": "Prueba", "año": "2025", "autor": None},
    )


def _make_web_result(title: str, content: str, url: str = "https://conv.org/W1") -> WebResult:
    return WebResult(
        url=url,
        title=title,
        content=content,
        snippet=content[:100],
        metadatos={"titulo": title, "fuente_nombre": "Web", "año": "2025", "autor": None},
    )


class TestChain06:
    def test_build_chain_06_returns_runnable(self):
        mock_llm = MagicMock()
        mock_llm.__or__ = MagicMock(return_value=MagicMock())
        chain = build_chain_06(mock_llm)
        assert chain is not None

    def test_format_chunks_numera_con_fuente(self):
        chunks = [
            _make_chunk("Sostenibilidad ambiental Medellín", "https://a.com"),
            _make_chunk("Transformación digital Colombia", "https://b.com"),
        ]
        result = format_chunks_as_context(chunks)
        assert "[1]" in result
        assert "[2]" in result
        assert "https://a.com" in result

    def test_format_chunks_vacio(self):
        assert format_chunks_as_context([]) == ""


class TestGenerateConvergencia:
    def _make_uc(
        self,
        texto_llm: str = "Cap 5 generado.",
        chunks_caps: list | None = None,
        chunks_territorial: list | None = None,
    ) -> GenerateConvergencia:
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = texto_llm

        mock_store = MagicMock()
        default_caps = [_make_chunk(f"Benchmark {i}", f"https://cap.com/{i}") for i in range(3)]
        default_territorial = [_make_chunk(f"Territorial {i}", f"https://terr.com/{i}") for i in range(3)]
        mock_store.search.side_effect = [
            chunks_caps if chunks_caps is not None else default_caps,
            chunks_territorial if chunks_territorial is not None else default_territorial,
        ]

        mock_web = MagicMock()
        mock_web.search.return_value = [
            _make_web_result("Sostenibilidad sector", "Regulaciones ambientales Colombia...")
        ]

        return GenerateConvergencia(chain=mock_chain, store=mock_store, web_connector=mock_web)

    def test_execute_retorna_cap_convergencia(self):
        uc = self._make_uc("Texto del capítulo 5.")
        result = uc.execute("Noel S.A.S.", "Empresa de galletas.", "Alimentos")
        assert isinstance(result, CapConvergencia)
        assert result.retrieval_suficiente
        assert result.texto == "Texto del capítulo 5."

    def test_execute_llama_chain_con_variables_correctas(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        caps_chunks = [_make_chunk(f"c{i}", f"https://caps.com/{i}") for i in range(3)]
        terr_chunks = [_make_chunk(f"t{i}", f"https://terr.com/{i}") for i in range(3)]
        mock_store.search.side_effect = [caps_chunks, terr_chunks]
        mock_web = MagicMock()
        mock_web.search.return_value = []

        uc = GenerateConvergencia(mock_chain, mock_store, mock_web)
        uc.execute("Noel", "Empresa galletas.", "Alimentos")

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "descripcion_empresa" in call_kwargs
        assert "sector_gics" in call_kwargs
        assert "retrieval_caps_anteriores" in call_kwargs
        assert "retrieval_convergencia_territorial" in call_kwargs

    def test_execute_parrafo_ausencia_si_retrieval_insuficiente(self):
        mock_chain = MagicMock()
        mock_store = MagicMock()
        mock_store.search.side_effect = [
            [_make_chunk("Solo uno", "https://a.com")],
            [],
        ]
        mock_web = MagicMock()
        mock_web.search.return_value = []

        uc = GenerateConvergencia(mock_chain, mock_store, mock_web)
        result = uc.execute("Empresa X", "Desc.", "Sector")
        assert not result.retrieval_suficiente
        assert result.n_chunks_usados == 0
        assert "Cap 5" in result.texto
        mock_chain.invoke.assert_not_called()

    def test_execute_realiza_dos_queries_rag(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        chunks = [_make_chunk(f"c{i}", f"https://x.com/{i}") for i in range(3)]
        mock_store.search.side_effect = [chunks, chunks]
        mock_web = MagicMock()
        mock_web.search.return_value = []

        uc = GenerateConvergencia(mock_chain, mock_store, mock_web)
        uc.execute("Empresa", "Desc.", "Sector")

        assert mock_store.search.call_count == 2

    def test_execute_deduplica_chunks_por_url(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        misma_url = "https://repetido.com"
        chunk_dup = [_make_chunk(f"c{i}", misma_url) for i in range(3)]
        chunk_nuevo = [_make_chunk(f"n{i}", f"https://nuevo.com/{i}") for i in range(3)]
        mock_store.search.side_effect = [chunk_dup, chunk_nuevo]
        mock_web = MagicMock()
        mock_web.search.return_value = []

        uc = GenerateConvergencia(mock_chain, mock_store, mock_web)
        result = uc.execute("Empresa", "Desc.", "Sector")

        assert result.n_chunks_usados < len(chunk_dup) + len(chunk_nuevo)

    def test_execute_ingesta_resultados_web(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        chunks = [_make_chunk(f"c{i}", f"https://x.com/{i}") for i in range(3)]
        mock_store.search.side_effect = [chunks, chunks]
        mock_web = MagicMock()
        mock_web.search.return_value = [
            WebResult(url="https://w.com", title="T", content="C", snippet="C", metadatos={})
        ]

        uc = GenerateConvergencia(mock_chain, mock_store, mock_web)
        uc.execute("Empresa", "Desc.", "Sector")
        assert mock_store.ingest.call_count >= 1
