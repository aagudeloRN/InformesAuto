"""T2 (DT-058) — Cap 4 Ecosistema adaptativo: gating por-subsección.

Cada subsección 4.x se gatea por su propio retrieval; solo se solicitan al modelo las que
superan el umbral. Si ninguna lo supera, el capítulo se omite con párrafo de ausencia (ADR-002).
Tests mockeados (sin Ollama/Tavily/BD).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ic.domain.chains.chain_05_ecosistema import SUBSECCIONES, build_secciones_solicitadas
from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
from ic.shared.types import ChunkResult


def _chunk(i: int) -> ChunkResult:
    return ChunkResult(
        chunk_texto=f"evidencia {i}",
        fuente_tipo="pdf",
        fuente_url=f"https://d/{i}",
        score=0.9,
        metadatos={"titulo": "Doc", "año": "2025"},
        chunk_id=f"id-{i}",
    )


def _uc_con_gating(suficientes_keywords: set[str]):
    """UC cuyo store devuelve ≥3 chunks solo para las queries que contienen un keyword dado."""
    chain = MagicMock()
    chain.invoke.return_value = "## 4.x contenido"
    store = MagicMock()

    def _search(query, **_kwargs):
        if any(kw in query for kw in suficientes_keywords):
            return [_chunk(i) for i in range(4)]  # suficiente
        return [_chunk(99)]  # 1 chunk → insuficiente

    store.search.side_effect = _search
    web = MagicMock()
    web.search.return_value = []
    return GenerateEcosistema(chain, store, web), chain


class TestCap4Gating:
    def test_solo_subsecciones_con_evidencia_se_solicitan(self):
        # 4.1 (inversiones) y 4.3 (fusiones) tienen evidencia; el resto no.
        uc, chain = _uc_con_gating({"inversiones", "fusiones"})
        result = uc.execute("Alpina", "Láctea", "Alimentos", sector_gics_code="3020")

        assert result.retrieval_suficiente
        pedido = chain.invoke.call_args[0][0]["secciones_solicitadas"]
        assert "## 4.1. Inversiones" in pedido
        assert "## 4.3. Fusiones y Adquisiciones (M&A)" in pedido
        # Subsecciones sin evidencia omitidas por completo (sin filler).
        assert "## 4.2." not in pedido
        assert "## 4.4." not in pedido
        assert "## 4.5." not in pedido

    def test_cap_omitido_si_ninguna_subseccion_suficiente(self):
        uc, chain = _uc_con_gating(set())  # nada supera el umbral
        result = uc.execute("Empresa X", "Desc", "Sector", sector_gics_code="9999")

        assert not result.retrieval_suficiente
        assert result.n_chunks_usados == 0
        assert "Cap 4" in result.texto
        chain.invoke.assert_not_called()  # ADR-002: no se llama al modelo sin evidencia

    def test_todas_suficientes_emite_las_cinco(self):
        # "Sector" está en sector_query → presente en TODAS las queries de subsección.
        uc, chain = _uc_con_gating({"Sector"})
        uc.execute("Empresa", "Desc", "Sector", sector_gics_code="3020")
        pedido = chain.invoke.call_args[0][0]["secciones_solicitadas"]
        for sid, _t, _d, _q in SUBSECCIONES:
            assert f"## {sid}." in pedido


class TestBuildSeccionesSolicitadas:
    def test_ensambla_solo_activas_en_orden(self):
        activas = [SUBSECCIONES[0], SUBSECCIONES[2]]
        out = build_secciones_solicitadas(activas)
        assert out.index("## 4.1.") < out.index("## 4.3.")
        assert "## 4.2." not in out

    def test_vacio(self):
        assert build_secciones_solicitadas([]) == ""
