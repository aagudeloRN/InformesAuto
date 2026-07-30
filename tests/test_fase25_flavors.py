"""DT-059/T3 — Dos sabores + invariante flag OFF.

Fast (sin LLM/red real): store y web mockeados; el juez/revisor se inyectan como stubs
LCEL. Verifica: (1) flag OFF = cap intacto y loop no invocado (invariante); (2) sabor web
re-busca (llama al conector web) cuando el juez pide faltantes; (3) sabor integración NO
hace retrieval nuevo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock

from ic.domain.use_cases import self_review_hooks as hooks


@dataclass
class _Cap:
    texto: str
    retrieval_suficiente: bool = True
    n_chunks_usados: int = 3
    chunks_usados: list = field(default_factory=list)


class _Settings:
    def __init__(self, enabled: bool, min_total: int = 11, max_iter: int = 3) -> None:
        self.selfreview_enabled = enabled
        self.selfreview_min_total = min_total
        self.selfreview_max_iter = max_iter


def _patch_judge(monkeypatch, salidas: list[str]) -> dict:
    """Sustituye build_chain_judge/build_chain_revise por stubs que devuelven textos programados."""
    state = {"judge_calls": 0, "revise_calls": 0}

    class _JudgeChain:
        def invoke(self, _inputs):
            i = min(state["judge_calls"], len(salidas) - 1)
            state["judge_calls"] += 1
            return salidas[i]

    class _ReviseChain:
        def invoke(self, _inputs):
            state["revise_calls"] += 1
            return f"texto revisado {state['revise_calls']}"

    monkeypatch.setattr(hooks, "build_chain_judge", lambda _llm: _JudgeChain())
    monkeypatch.setattr(hooks, "build_chain_revise", lambda _llm: _ReviseChain())
    monkeypatch.setattr(hooks, "format_chunks_as_context", lambda chunks: "EVIDENCIA")
    return state


# --- Invariante: flag OFF ---


def test_flag_off_web_devuelve_cap_intacto(monkeypatch):
    state = _patch_judge(monkeypatch, ['{"E":0,"P":0,"V":0,"F":0,"T":0}'])
    cap = _Cap(texto="original")
    store, web = MagicMock(), MagicMock()
    out = hooks.review_web_cap(
        settings=_Settings(enabled=False), llm=object(),
        capitulo_nombre="Cap 2 — Análisis Competitivo", criterios="c",
        cap_obj=cap, run_key="rk", store=store, web=web,
        sector_gics="Alimentos", sector_gics_code="3020", retrieval_query="q",
    )
    assert out is cap  # cap intacto, mismo objeto
    assert state["judge_calls"] == 0  # el loop nunca se invocó
    web.search.assert_not_called()


def test_flag_off_integracion_devuelve_cap_intacto(monkeypatch):
    state = _patch_judge(monkeypatch, ['{"E":0,"P":0,"V":0,"F":0,"T":0}'])
    cap = _Cap(texto="original")
    out = hooks.review_integration_cap(
        settings=_Settings(enabled=False), llm=object(),
        capitulo_nombre="Cap 5 — Convergencia Empresarial", criterios="c",
        cap_obj=cap, run_key="rk",
    )
    assert out is cap
    assert state["judge_calls"] == 0


def test_cap_ausente_no_se_revisa(monkeypatch):
    state = _patch_judge(monkeypatch, ['{"E":3,"P":3,"V":3,"F":3,"T":3}'])
    cap = _Cap(texto="ausente", retrieval_suficiente=False)
    out = hooks.review_integration_cap(
        settings=_Settings(enabled=True), llm=object(),
        capitulo_nombre="Cap 6 — Accionables Estratégicos", criterios="c",
        cap_obj=cap, run_key="rk",
    )
    assert out is cap
    assert state["judge_calls"] == 0  # retrieval insuficiente → no entra al loop


# --- Selectivo: pasa el gate a la primera → no revisa ---


def test_pasa_gate_no_revisa(monkeypatch):
    state = _patch_judge(monkeypatch, ['{"E":3,"P":3,"V":3,"F":2,"T":2}'])  # total 13, pasa
    cap = _Cap(texto="bueno")
    out = hooks.review_integration_cap(
        settings=_Settings(enabled=True), llm=object(),
        capitulo_nombre="Cap 5 — Convergencia Empresarial", criterios="c",
        cap_obj=cap, run_key="rk",
    )
    assert out is cap
    assert state["judge_calls"] == 1  # juzgó una vez
    assert state["revise_calls"] == 0  # no revisó (ya pasaba)


# --- Sabor web: re-busca cuando el juez pide faltantes ---


def test_web_rebusca_y_resintetiza(monkeypatch):
    # 1ª evaluación no pasa (con faltante) → revisa; 2ª pasa.
    _patch_judge(monkeypatch, [
        '{"E":1,"P":1,"V":1,"F":1,"T":1,"faltantes":["incluir cuota de mercado"]}',
        '{"E":3,"P":3,"V":3,"F":2,"T":2}',
    ])
    cap = _Cap(texto="flojo")
    store, web = MagicMock(), MagicMock()
    web.search.return_value = [type("R", (), {"content": "c", "url": "u"})()]
    store.search.return_value = ["chunk1", "chunk2"]

    out = hooks.review_web_cap(
        settings=_Settings(enabled=True), llm=object(),
        capitulo_nombre="Cap 2 — Análisis Competitivo", criterios="c",
        cap_obj=cap, run_key="rk", store=store, web=web,
        sector_gics="Alimentos", sector_gics_code="3020", retrieval_query="q",
        kb_competidores=["Nestlé"],
    )
    assert web.search.called  # Reflexion con herramientas: re-buscó
    assert store.ingest.called  # ingirió lo encontrado
    assert store.search.called  # re-recuperó
    assert out.texto.startswith("texto revisado")  # se re-sintetizó
    assert out.chunks_usados == ["chunk1", "chunk2"]  # evidencia enriquecida


# --- Sabor integración: NO hace retrieval nuevo ---


def test_integracion_no_hace_retrieval(monkeypatch):
    state = _patch_judge(monkeypatch, [
        '{"E":1,"P":1,"V":1,"F":1,"T":1,"faltantes":["profundizar áreas"]}',
        '{"E":3,"P":3,"V":3,"F":2,"T":2}',
    ])
    cap = _Cap(texto="flojo", chunks_usados=["c1"])
    out = hooks.review_integration_cap(
        settings=_Settings(enabled=True), llm=object(),
        capitulo_nombre="Cap 5 — Convergencia Empresarial", criterios="c",
        cap_obj=cap, run_key="rk",
    )
    assert out.texto.startswith("texto revisado")
    assert out.chunks_usados == ["c1"]  # sin nuevo retrieval; evidencia previa intacta
    assert state["revise_calls"] == 1
