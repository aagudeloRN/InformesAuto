"""DT-066/B2 — Cableado de la sección 2.1 determinista en GenerateBenchmarking.execute.

Fast: sin LLM real (chains stub). Verifica que con B2 ON la 2.1 se ANTEPONE ensamblada desde el KB
(no la escribe el LLM) y que la prosa del LLM recibe la 2.1 como contexto; y que OFF es invariante.
También que el prompt "sin 2.1" se deriva correctamente del canónico.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from ic.domain.chains.chain_03_benchmarking import (
    SYSTEM_PROMPT_03,
    USER_PROMPT_03,
    USER_PROMPT_03_SIN_21,
)
from ic.domain.kb.ficha_parser import TIER_GLOBAL, TIER_REGIONAL
from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
from ic.shared.types import CapBenchmarking, ChunkResult

_PROSA = "## 2.2. División de Competidores\n\nSíntesis en español."


class _FakeChain:
    def __init__(self, salida: str = _PROSA) -> None:
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

    def ingest(self, *a, **k) -> None:
        pass


class _FakeWeb:
    def search(self, *a, **k) -> list:
        return []


def _chunks(n: int = 6) -> list[ChunkResult]:
    return [
        ChunkResult(
            chunk_texto=f"Fragmento {i}.", fuente_tipo="web",
            fuente_url=f"https://ej.com/{i}", score=0.9,
        )
        for i in range(n)
    ]


_TIERS = {TIER_GLOBAL: ["Nestlé"], TIER_REGIONAL: ["Colombina"]}
_FICHAS = {
    "Nestlé": {"pais_origen": "Suiza", "portafolio": "Galletas y café."},
    "Colombina": {"pais_origen": "Colombia"},
}


def _execute(chain, **kw):
    return GenerateBenchmarking(
        chain=chain, store=_FakeStore(_chunks()), web_connector=_FakeWeb(), **kw
    ).execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea.",
        sector_gics="Alimentos, bebidas y tabaco",
    )


def test_prompt_sin_21_derivado_del_canonico():
    # Conserva el spec de 2.2+ (sin drift) pero quita la autoría de 2.1 y añade el contexto.
    assert "## 2.2. División de Competidores" in USER_PROMPT_03_SIN_21
    assert "RADAR DE POSICIONAMIENTO" in USER_PROMPT_03_SIN_21
    assert "{seccion_21_context}" in USER_PROMPT_03_SIN_21
    assert "Identifica y analiza 14 actores" not in USER_PROMPT_03_SIN_21  # ya no redacta 2.1
    assert "Identifica y analiza 14 actores" in USER_PROMPT_03  # el canónico sí


def test_prompt_sin_21_formatea_sin_variables_faltantes():
    # Riesgo real que el FakeChain no cubre: el ChatPromptTemplate debe resolver TODAS las variables
    # (incl. {seccion_21_context}) y respetar las llaves escapadas {{...}} del bloque radar. Un
    # payload completo debe formatear sin KeyError ni variables sobrantes.
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_03),
        ("human", USER_PROMPT_03_SIN_21),
    ])
    payload = {
        "descripcion_empresa": "Empresa láctea.",
        "sector_gics": "Alimentos, bebidas y tabaco",
        "retrieval_competidores": "evidencia",
        "jugadores_locales": "",
        "referentes_globales_anclados": "",
        "fichas_conocidas": "",
        "seccion_21_context": "## 2.1. Jugadores Clave\n\n### Referentes Globales\n\n| C | V |",
    }
    msgs = prompt.format_messages(**payload)
    texto = "\n".join(m.content for m in msgs)
    assert "## 2.1. Jugadores Clave" in texto  # el contexto ensamblado se inyectó
    assert "radar_json" in texto  # el bloque radar (llaves {{}}) sobrevive el formateo
    assert "{seccion_21_context}" not in texto  # el placeholder se resolvió


def test_b2_antepone_21_ensamblada_y_pasa_contexto():
    chain = _FakeChain()
    cap = _execute(
        chain, seccion21_enabled=True, tiers=_TIERS, fichas_kb=_FICHAS, holes_chain=None,
    )
    assert isinstance(cap, CapBenchmarking)
    # La 2.1 ensamblada (determinista, desde el KB) abre el capítulo…
    assert cap.texto.startswith("## 2.1. Jugadores Clave")
    assert "Nestlé — Suiza" in cap.texto
    assert "Galletas y café." in cap.texto
    # …seguida de la prosa del LLM (2.2).
    assert "## 2.2. División de Competidores" in cap.texto
    # El LLM recibió la 2.1 como contexto y NO el pre-fill redundante.
    assert "## 2.1" in chain.ultimo_input["seccion_21_context"]
    assert chain.ultimo_input["fichas_conocidas"] == ""
    # Sin spam de "no disponible" en la tabla ensamblada.
    assert "no disponible" not in cap.texto.lower()


def test_b2_off_es_invariante_el_llm_autora_todo():
    chain = _FakeChain(salida="## 2.1 ... texto completo del LLM en español.")
    cap = _execute(chain, seccion21_enabled=False, tiers=_TIERS, fichas_kb=_FICHAS)
    # OFF: no se antepone nada; el texto es el del LLM tal cual, y no hay slot de contexto 2.1.
    assert cap.texto == "## 2.1 ... texto completo del LLM en español."
    assert "seccion_21_context" not in chain.ultimo_input


def test_b2_on_pero_sin_anclas_cae_a_invariante():
    # Flag "ON" desde el llamador pero tiers vacío → self._seccion21_enabled=False (no ensambla).
    chain = _FakeChain(salida="texto del LLM")
    cap = _execute(chain, seccion21_enabled=True, tiers={}, fichas_kb={})
    assert cap.texto == "texto del LLM"
    assert "seccion_21_context" not in chain.ultimo_input
