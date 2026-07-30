"""DT-059/T1 — Juez con rúbrica: parser puro + gate + cadena con LLM mockeado.

Fast (sin LLM real): el parser es puro; la cadena se ejercita con un LLM stub que
devuelve JSON canned. RN-001: salida corrupta → peor caso (no acepta el capítulo).
"""

from __future__ import annotations

from ic.domain.chains.chain_judge import CRITERIOS_CAPITULO, build_chain_judge
from ic.domain.eval.rubric_score import (
    DIMENSIONES,
    RubricScore,
    parse_rubric_score,
)

# --- Parser puro ---


def test_parse_json_limpio():
    s = parse_rubric_score('{"E":3,"P":2,"V":3,"F":2,"T":3,"faltantes":["x"]}')
    assert s.parseable
    assert s.dimensiones == {"E": 3, "P": 2, "V": 3, "F": 2, "T": 3}
    assert s.total == 13
    assert s.faltantes == ["x"]


def test_parse_con_fence_y_texto_alrededor():
    raw = 'Aquí está mi evaluación:\n```json\n{"E":2,"P":2,"V":2,"F":2,"T":2}\n```\nFin.'
    s = parse_rubric_score(raw)
    assert s.parseable
    assert s.total == 10
    assert s.faltantes == []


def test_parse_clamp_fuera_de_rango():
    s = parse_rubric_score('{"E":9,"P":-4,"V":3,"F":"2","T":3}')
    assert s.dimensiones["E"] == 3  # recortado a 3
    assert s.dimensiones["P"] == 0  # recortado a 0
    assert s.dimensiones["F"] == 2  # "2" coaccionado a int


def test_parse_dimension_faltante_cuenta_cero():
    s = parse_rubric_score('{"E":3,"P":3,"V":3}')  # sin F ni T
    assert s.dimensiones["F"] == 0
    assert s.dimensiones["T"] == 0
    assert s.total == 9


def test_parse_faltantes_normaliza_no_strings():
    s = parse_rubric_score('{"E":1,"P":1,"V":1,"F":1,"T":1,"faltantes":["ok","",3,null]}')
    assert s.faltantes == ["ok"]


def test_parse_malformado_es_peor_caso():
    for raw in ["", "   ", "no json aquí", "{roto", "[1,2,3]"]:
        s = parse_rubric_score(raw)
        assert not s.parseable
        assert s.total == 0
        assert not s.pasa_gate()
        assert s.faltantes  # motivo explícito


# --- Gate de la rúbrica ---


def test_gate_pasa_con_11_y_sin_ceros():
    s = RubricScore(dimensiones={"E": 3, "P": 2, "V": 2, "F": 2, "T": 2})  # total 11
    assert s.pasa_gate()


def test_gate_falla_por_total_bajo():
    s = RubricScore(dimensiones={"E": 2, "P": 2, "V": 2, "F": 2, "T": 2})  # total 10
    assert not s.pasa_gate()


def test_gate_falla_por_dimension_en_cero_aunque_total_alto():
    s = RubricScore(dimensiones={"E": 3, "P": 3, "V": 3, "F": 3, "T": 0})  # total 12 pero un 0
    assert s.total == 12
    assert not s.pasa_gate()


def test_gate_umbral_configurable():
    s = RubricScore(dimensiones={"E": 3, "P": 3, "V": 3, "F": 2, "T": 2})  # total 13
    assert s.pasa_gate(min_total=13)
    assert not s.pasa_gate(min_total=14)


# --- Cadena del juez con LLM stub ---


def _stub_llm(respuesta: str):
    """LLM mínimo compatible con LCEL: Runnable que devuelve un AIMessage fijo."""
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import RunnableLambda

    return RunnableLambda(lambda _prompt: AIMessage(content=respuesta))


def test_chain_judge_produce_score_parseable():
    llm = _stub_llm('{"E":3,"P":2,"V":3,"F":2,"T":3,"faltantes":[]}')
    chain = build_chain_judge(llm)
    raw = chain.invoke({
        "capitulo_nombre": "Cap 2 — Análisis Competitivo",
        "criterios_capitulo": CRITERIOS_CAPITULO["Cap 2 — Análisis Competitivo"],
        "texto_capitulo": "Texto de prueba del capítulo.",
    })
    score = parse_rubric_score(raw)
    assert score.parseable
    assert score.total == 13
    assert score.pasa_gate()


def test_criterios_cubren_los_caps_looped():
    # Los 5 capítulos que el loop puede revisar (web: 2/3/4; integración: 5/6).
    esperados = {
        "Cap 2 — Análisis Competitivo",
        "Cap 3 — Análisis Sectorial Tendencial",
        "Cap 4 — Panorama Ecosistema",
        "Cap 5 — Convergencia Empresarial",
        "Cap 6 — Accionables Estratégicos",
    }
    assert esperados <= set(CRITERIOS_CAPITULO)
    assert DIMENSIONES == ("E", "P", "V", "F", "T")
