"""DT-064 T1/T2 — Anclaje de los sujetos de las fichas del Cap 2 (generación + self-review).

Verifica, sin LLM real (chains mockeadas), que:
- T1: `GenerateBenchmarking.execute` inyecta los globales anclados como sujetos obligatorios del
  prompt (y "" cuando no hay → invariante).
- T2: `review_web_cap` reinyecta esos sujetos en la re-síntesis del rescate (y no lo hace cuando el
  self-review está OFF → invariante).
Complementa el test del loop puro (`test_fase25_self_review.py`).
"""

from __future__ import annotations

from ic.domain.kb.relevance import format_referentes_globales
from ic.domain.use_cases import self_review_hooks
from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
from ic.shared.types import CapBenchmarking, ChunkResult

# --------------------------------------------------------------------------- T1: formateador puro


def test_format_referentes_globales_vacio_es_noop():
    assert format_referentes_globales([]) == ""
    assert format_referentes_globales(None) == ""
    assert format_referentes_globales(["  ", ""]) == ""


def test_format_referentes_globales_lista_dura_con_vinetas():
    bloque = format_referentes_globales(["Danone", "Fonterra"])
    assert "EXACTAMENTE" in bloque
    assert "- Danone" in bloque and "- Fonterra" in bloque
    assert "2.1.1" in bloque


# --------------------------------------------------------------------------- T1: cableado al prompt


class _FakeChain:
    """Runnable stub: captura los inputs del último invoke y devuelve texto fijo."""

    def __init__(self, salida: str = "Texto del capítulo en español.") -> None:
        self.salida = salida
        self.ultimo_input: dict | None = None

    def invoke(self, inputs: dict) -> str:
        self.ultimo_input = inputs
        return self.salida


class _FakeStore:
    def __init__(self, chunks: list[ChunkResult]) -> None:
        self._chunks = chunks

    def search(self, *a, **k) -> list[ChunkResult]:
        return self._chunks

    def ingest(self, *a, **k) -> None:  # no-op
        pass


class _FakeWeb:
    def search(self, *a, **k) -> list:
        return []  # sin resultados → sin ingesta (aísla el test del índice)


def _chunks(n: int = 6) -> list[ChunkResult]:
    return [
        ChunkResult(
            chunk_texto=f"Fragmento {i} del sector.",
            fuente_tipo="web",
            fuente_url=f"https://ej.com/{i}",
            score=0.9,
        )
        for i in range(n)
    ]


def test_execute_inyecta_globales_anclados_en_el_prompt():
    chain = _FakeChain()
    cap = GenerateBenchmarking(
        chain=chain,
        store=_FakeStore(_chunks()),
        web_connector=_FakeWeb(),
        kb_competidores=["Danone", "Fonterra"],
    ).execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea.",
        sector_gics="Alimentos, bebidas y tabaco",
    )
    assert isinstance(cap, CapBenchmarking)
    bloque = chain.ultimo_input["referentes_globales_anclados"]
    assert "Danone" in bloque and "Fonterra" in bloque and "EXACTAMENTE" in bloque


def test_execute_inyecta_fichas_conocidas_prefill():
    chain = _FakeChain()
    GenerateBenchmarking(
        chain=chain,
        store=_FakeStore(_chunks()),
        web_connector=_FakeWeb(),
        kb_competidores=["Danone"],
        fichas_conocidas_ctx="Datos ya conocidos del KB:\n- Danone:\n    pais_origen: Francia",
    ).execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea.",
        sector_gics="Alimentos, bebidas y tabaco",
    )
    assert "Francia" in chain.ultimo_input["fichas_conocidas"]


def test_execute_sin_kb_deja_el_slot_vacio_invariante():
    chain = _FakeChain()
    GenerateBenchmarking(
        chain=chain,
        store=_FakeStore(_chunks()),
        web_connector=_FakeWeb(),
        kb_competidores=[],
    ).execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea.",
        sector_gics="Alimentos, bebidas y tabaco",
    )
    assert chain.ultimo_input["referentes_globales_anclados"] == ""


# --------------------------------------------------------------------------- T2: self-review


class _Settings:
    def __init__(self, enabled: bool) -> None:
        self.selfreview_enabled = enabled
        self.selfreview_min_total = 11
        self.selfreview_max_iter = 3


class _JudgeChain:
    """Devuelve scores en cola: primero falla el gate, luego pasa (dispara 1 revisión)."""

    def __init__(self) -> None:
        self._cola = [
            '{"E":1,"P":1,"V":1,"F":1,"T":1,"faltantes":["falta cifra"]}',  # total 5 → no pasa
            '{"E":3,"P":3,"V":3,"F":2,"T":2}',  # total 13 → pasa
        ]

    def invoke(self, inputs: dict) -> str:
        return self._cola.pop(0)


class _ReviseCapture:
    """Captura el sujetos_anclados que recibe la re-síntesis."""

    def __init__(self) -> None:
        self.sujetos: str | None = None

    def invoke(self, inputs: dict) -> str:
        self.sujetos = inputs["sujetos_anclados"]
        return "Capítulo reescrito."


def _patch_chains(monkeypatch, revise):
    monkeypatch.setattr(self_review_hooks, "build_chain_judge", lambda llm: _JudgeChain())
    monkeypatch.setattr(self_review_hooks, "build_chain_revise", lambda llm: revise)
    # La persistencia toca BD; en unit test es un no-op (best-effort en producción).
    monkeypatch.setattr(self_review_hooks, "_persist_trace", lambda *a, **k: None)


def _cap() -> CapBenchmarking:
    return CapBenchmarking(
        texto="Borrador inicial del Cap 2.",
        n_chunks_usados=5,
        retrieval_suficiente=True,
        chunks_usados=_chunks(),
    )


def test_review_web_cap_reinyecta_sujetos_anclados(monkeypatch):
    revise = _ReviseCapture()
    _patch_chains(monkeypatch, revise)
    self_review_hooks.review_web_cap(
        settings=_Settings(enabled=True),
        llm=None,
        capitulo_nombre="Cap 2 — Análisis Competitivo",
        criterios="criterios",
        cap_obj=_cap(),
        run_key="rk",
        store=_FakeStore([]),
        web=_FakeWeb(),
        sector_gics="Alimentos, bebidas y tabaco",
        sector_gics_code="3020",
        retrieval_query="q",
        kb_competidores=["Danone", "Fonterra"],
        jugadores_locales_ctx="Referentes regionales (Colombia) del directorio:\n- Colanta",
    )
    assert revise.sujetos is not None
    assert "Danone" in revise.sujetos and "Fonterra" in revise.sujetos  # globales anclados
    assert "Colanta" in revise.sujetos  # locales del directorio


def test_review_web_cap_off_no_revisa_invariante(monkeypatch):
    revise = _ReviseCapture()
    _patch_chains(monkeypatch, revise)
    cap = _cap()
    out = self_review_hooks.review_web_cap(
        settings=_Settings(enabled=False),
        llm=None,
        capitulo_nombre="Cap 2 — Análisis Competitivo",
        criterios="criterios",
        cap_obj=cap,
        run_key="rk",
        store=_FakeStore([]),
        web=_FakeWeb(),
        sector_gics="X",
        sector_gics_code="3020",
        retrieval_query="q",
        kb_competidores=["Danone"],
    )
    assert out is cap  # capítulo intacto
    assert revise.sujetos is None  # la re-síntesis nunca se invocó
