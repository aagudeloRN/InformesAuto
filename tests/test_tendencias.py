"""Tests para Cap 3 — Análisis Tendencial.

Todos los tests usan mocks — sin llamadas reales a OpenRouter, OpenAlex ni Tavily.
"""

from unittest.mock import MagicMock

from ic.domain.chains.chain_04_tendencias import (
    SYSTEM_PROMPT_04,
    build_chain_04,
    format_academic_sources,
    format_chunks_as_context,
)
from ic.domain.use_cases.generate_tendencias import GenerateTendencias
from ic.shared.types import CapTendencias, ChunkResult, WebResult


def _make_chunk(texto: str, url: str = "https://ejemplo.com", score: float = 0.85) -> ChunkResult:
    return ChunkResult(
        chunk_texto=texto,
        fuente_tipo="web",
        fuente_url=url,
        score=score,
        metadatos={"titulo": "Prueba", "año": "2025", "autor": None},
    )


def _make_web_result(title: str, content: str, url: str = "https://oa.org/W1") -> WebResult:
    return WebResult(
        url=url,
        title=title,
        content=content,
        snippet=content[:100],
        metadatos={
            "titulo": title,
            "fuente_nombre": "OpenAlex",
            "año": "2024",
            "autor": "García, J.",
            "doi": url,
        },
    )


class TestChain04:
    def test_build_chain_returns_runnable(self):
        """build_chain_04 debe retornar un Runnable encadenable."""
        mock_llm = MagicMock()
        mock_llm.__or__ = MagicMock(return_value=MagicMock())
        # La cadena se construye sin error
        chain = build_chain_04(mock_llm)
        assert chain is not None

    def test_format_chunks_numera_con_fuente(self):
        chunks = [
            _make_chunk("Texto uno", "https://a.com"),
            _make_chunk("Texto dos", "https://b.com"),
        ]
        result = format_chunks_as_context(chunks)
        assert "[1]" in result
        assert "[2]" in result
        assert "https://a.com" in result
        assert "Texto dos" in result

    def test_format_chunks_vacio(self):
        assert format_chunks_as_context([]) == ""

    def test_format_academic_sin_resultados(self):
        texto = format_academic_sources([])
        assert "No se encontraron" in texto

    def test_format_academic_con_resultados(self):
        results = [_make_web_result("Tendencias alimentarias", "El sector de alimentos...")]
        texto = format_academic_sources(results)
        assert "Tendencias alimentarias" in texto
        assert "[A1]" in texto
        assert "García, J." in texto

    def test_system_prompt_04_prohibe_bloques_codigo(self):
        # DT-UI04c: el prompt prohíbe explícitamente emitir bloques de código/cercas ``` (prevención
        # del preámbulo espurio que contaminaba el Cap 3).
        assert "No emitas bloques de código" in SYSTEM_PROMPT_04
        assert "```" in SYSTEM_PROMPT_04


class TestGenerateTendencias:
    def _make_uc(self, texto_llm: str = "Cap 3 generado.", chunks: list | None = None):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = texto_llm

        mock_store = MagicMock()
        mock_store.search.return_value = chunks or [_make_chunk(f"Chunk {i}") for i in range(5)]

        mock_web = MagicMock()
        mock_web.search.return_value = [
            WebResult(
                url="https://web.com/1",
                title="Tendencias 2025",
                content="El sector alimentario...",
                snippet="El sector...",
                metadatos={},
            )
        ]

        mock_openalex = MagicMock()
        mock_openalex.search.return_value = [_make_web_result("Food trends", "Research shows...")]

        return GenerateTendencias(
            chain=mock_chain,
            store=mock_store,
            web_connector=mock_web,
            openalex_connector=mock_openalex,
        )

    def test_execute_retorna_cap_tendencias(self):
        uc = self._make_uc("Texto del capítulo 3.")
        result = uc.execute("Noel S.A.S.", "Empresa de galletas.", "Alimentos")
        assert isinstance(result, CapTendencias)
        assert result.retrieval_suficiente
        assert result.texto == "Texto del capítulo 3."

    def test_execute_llama_al_chain_con_inputs_correctos(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk(f"c{i}") for i in range(5)]
        mock_web = MagicMock()
        mock_web.search.return_value = []
        mock_oa = MagicMock()
        mock_oa.search.return_value = []

        uc = GenerateTendencias(mock_chain, mock_store, mock_web, mock_oa)
        uc.execute("Noel", "Empresa galletas.", "Alimentos")

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "descripcion_empresa" in call_kwargs
        assert "sector_gics" in call_kwargs
        assert "retrieval_sector" in call_kwargs
        assert "fuentes_academicas" in call_kwargs

    def test_execute_strip_preamble_antes_de_heading(self):
        # DT-UI04c: si el LLM antepone un bloque de código/JSON, el post-procesamiento lo poda y el
        # texto queda empezando en el encabezado real.
        crudo = '```json\n{"seccion": "3.1"}\n```\n\n## 3.1. Tendencias\n\nTexto del capítulo.'
        uc = self._make_uc(crudo)
        result = uc.execute("ERCO", "Empresa de energía.", "Servicios de Energía")
        primera = next(ln for ln in result.texto.splitlines() if ln.strip())
        assert primera.startswith("## 3.")
        assert "```" not in result.texto

    def test_execute_parrafo_ausencia_si_retrieval_insuficiente(self):
        uc = self._make_uc(chunks=[_make_chunk("Solo un chunk")])
        # Solo 1 chunk → por debajo del mínimo de 3
        result = uc.execute("Empresa X", "Desc.", "Sector")
        assert not result.retrieval_suficiente
        assert result.n_chunks_usados == 0

    def test_execute_ingesta_resultados_web(self):
        uc = self._make_uc()
        uc.execute("Noel", "Desc.", "Alimentos")
        # store.ingest debe haberse llamado para resultados web y OpenAlex
        assert uc._store.ingest.call_count >= 1

    def test_execute_openalex_silencioso_si_lista_vacia(self):
        """Si OpenAlex retorna vacío, no falla — solo omite la ingesta académica."""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        mock_store = MagicMock()
        mock_store.search.return_value = [_make_chunk(f"c{i}") for i in range(5)]
        mock_web = MagicMock()
        mock_web.search.return_value = []
        mock_oa = MagicMock()
        mock_oa.search.return_value = []  # OpenAlex silencioso

        uc = GenerateTendencias(mock_chain, mock_store, mock_web, mock_oa)
        result = uc.execute("Empresa", "Desc.", "Sector")
        assert result.retrieval_suficiente  # el capítulo sigue generándose
