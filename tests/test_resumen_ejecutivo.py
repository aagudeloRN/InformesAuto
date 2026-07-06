"""Tests para Resumen Ejecutivo (N3 — síntesis directa, sin retrieval).

Todos los tests usan mocks — sin llamadas reales a OpenRouter.
"""

from unittest.mock import MagicMock

from ic.domain.chains.chain_08_resumen_ejecutivo import build_chain_08
from ic.domain.use_cases.generate_resumen_ejecutivo import GenerateResumenEjecutivo
from ic.shared.types import ResumenEjecutivo


class TestChain08:
    def test_build_chain_08_returns_runnable(self):
        mock_llm = MagicMock()
        mock_llm.__or__ = MagicMock(return_value=MagicMock())
        chain = build_chain_08(mock_llm)
        assert chain is not None


class TestGenerateResumenEjecutivo:
    def _make_uc(self, texto_llm: str = "Resumen ejecutivo generado.") -> GenerateResumenEjecutivo:
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = texto_llm
        return GenerateResumenEjecutivo(chain=mock_chain)

    def test_execute_retorna_resumen_ejecutivo(self):
        uc = self._make_uc("Resumen C-Level de Noel.")
        cap_textos = {
            "Cap 1": "Descripción empresa.",
            "Cap 2": "Benchmarking sector.",
            "Cap 5": "Convergencia territorial.",
        }
        result = uc.execute("Noel S.A.S.", "Empresa de galletas.", "Alimentos", cap_textos)
        assert isinstance(result, ResumenEjecutivo)
        assert result.texto == "Resumen C-Level de Noel."

    def test_execute_siempre_retrieval_suficiente(self):
        uc = self._make_uc()
        result = uc.execute("Empresa", "Desc.", "Sector", {"Cap 1": "Texto."})
        assert result.retrieval_suficiente is True
        assert result.n_chunks_usados == 0

    def test_execute_llama_chain_con_variables_correctas(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        uc = GenerateResumenEjecutivo(chain=mock_chain)

        uc.execute(
            "Empresa X",
            "Descripción detallada.",
            "Tecnología",
            {"Cap 1": "Cap 1 texto.", "Cap 2": "Cap 2 texto."},
        )

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "descripcion_empresa" in call_kwargs
        assert "sector_gics" in call_kwargs
        assert "textos_capitulos" in call_kwargs

    def test_execute_omite_caps_con_texto_vacio(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        uc = GenerateResumenEjecutivo(chain=mock_chain)

        uc.execute(
            "Empresa",
            "Desc.",
            "Sector",
            {"Cap 1": "Texto válido.", "Cap 3": "", "Cap 5": "   "},
        )

        textos_arg = mock_chain.invoke.call_args[0][0]["textos_capitulos"]
        assert "Cap 1" in textos_arg
        assert "Cap 3" not in textos_arg
        assert "Cap 5" not in textos_arg

    def test_execute_sin_store_ni_web(self):
        """GenerateResumenEjecutivo no tiene store ni web_connector."""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "OK"
        uc = GenerateResumenEjecutivo(chain=mock_chain)
        assert not hasattr(uc, "_store")
        assert not hasattr(uc, "_web")
