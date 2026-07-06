"""Tests para Cap 4 — Ecosistema Empresarial.

Todos los tests usan mocks — sin llamadas reales a OpenRouter ni Tavily.
"""

from unittest.mock import MagicMock

from ic.domain.chains.chain_05_ecosistema import (
    build_chain_05,
    format_academic_sources,
    format_chunks_as_context,
)
from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
from ic.shared.types import CapEcosistema, ChunkResult, WebResult


def _make_chunk(texto: str, url: str = "https://ejemplo.com", score: float = 0.85) -> ChunkResult:
    return ChunkResult(
        chunk_texto=texto,
        fuente_tipo="web",
        fuente_url=url,
        score=score,
        metadatos={"titulo": "Prueba", "año": "2025", "autor": None},
    )


def _make_web_result(title: str, content: str, url: str = "https://eco.org/W1") -> WebResult:
    return WebResult(
        url=url,
        title=title,
        content=content,
        snippet=content[:100],
        metadatos={
            "titulo": title,
            "fuente_nombre": "Web",
            "año": "2025",
            "autor": "López, M.",
            "doi": url,
        },
    )


class TestChain05:
    def test_build_chain_returns_runnable(self):
        mock_llm = MagicMock()
        mock_llm.__or__ = MagicMock(return_value=MagicMock())
        chain = build_chain_05(mock_llm)
        assert chain is not None

    def test_format_chunks_numera_con_fuente(self):
        chunks = [
            _make_chunk("Proveedor A", "https://a.com"),
            _make_chunk("Proveedor B", "https://b.com"),
        ]
        result = format_chunks_as_context(chunks)
        assert "[1]" in result
        assert "[2]" in result
        assert "https://a.com" in result

    def test_format_chunks_vacio(self):
        assert format_chunks_as_context([]) == ""

    def test_format_academic_sin_resultados(self):
        texto = format_academic_sources([])
        assert "No se encontraron" in texto


class TestGenerateEcosistema:
    def _make_uc(self, texto_llm: str = "Cap 4 generado.", chunks: list | None = None):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = texto_llm

        mock_store = MagicMock()
        mock_store.search.return_value = chunks or [_make_chunk(f"Chunk {i}") for i in range(5)]

        mock_web = MagicMock()
        mock_web.search.return_value = [
            WebResult(
                url="https://web.com/eco",
                title="Ecosistema sector 2025",
                content="Los proveedores del sector alimentario...",
                snippet="Los proveedores...",
                metadatos={},
            )
        ]

        return GenerateEcosistema(
            chain=mock_chain,
            store=mock_store,
            web_connector=mock_web,
        )

    def test_execute_retorna_cap_ecosistema(self):
        uc = self._make_uc("Texto del capítulo 4.")
        result = uc.execute("Noel S.A.S.", "Empresa de galletas.", "Alimentos")
        assert isinstance(result, CapEcosistema)
        assert result.retrieval_suficiente
        assert result.texto == "Texto del capítulo 4."

    def test_execute_llama_al_chain_con_inputs_correctos(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk(f"c{i}") for i in range(5)]
        mock_web = MagicMock()
        mock_web.search.return_value = []

        uc = GenerateEcosistema(mock_chain, mock_store, mock_web)
        uc.execute("Noel", "Empresa galletas.", "Alimentos")

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "descripcion_empresa" in call_kwargs
        assert "sector_gics" in call_kwargs
        assert "retrieval_sector" in call_kwargs
        assert "fuentes_web" in call_kwargs

    def test_execute_parrafo_ausencia_si_retrieval_insuficiente(self):
        uc = self._make_uc(chunks=[_make_chunk("Solo un chunk")])
        result = uc.execute("Empresa X", "Desc.", "Sector")
        assert not result.retrieval_suficiente
        assert result.n_chunks_usados == 0
        assert "Cap 4" in result.texto

    def test_execute_web_sin_resultados_no_falla(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk(f"c{i}") for i in range(5)]
        mock_web = MagicMock()
        mock_web.search.return_value = []

        uc = GenerateEcosistema(mock_chain, mock_store, mock_web)
        result = uc.execute("Empresa", "Desc.", "Sector")
        assert result.retrieval_suficiente

    def test_execute_ingest_llamado(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk(f"c{i}") for i in range(5)]
        mock_web = MagicMock()
        mock_web.search.return_value = [
            WebResult(url="https://x.com", title="T", content="C", snippet="C", metadatos={})
        ]

        uc = GenerateEcosistema(mock_chain, mock_store, mock_web)
        uc.execute("Empresa", "Desc.", "Sector")
        assert uc._store.ingest.call_count >= 1
