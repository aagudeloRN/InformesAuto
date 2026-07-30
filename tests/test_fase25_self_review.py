"""DT-059/T2 — Loop de auto-revisión puro: guardar-el-mejor, parada, selectivo.

Fixtures deterministas (sin LLM): los callables devuelven scores programados. Se verifica
que se conserva la MEJOR versión (no la última) y que las tres condiciones de parada operan.
"""

from __future__ import annotations

from ic.domain.eval.rubric_score import RubricScore
from ic.domain.eval.self_review import (
    PARADA_MAX_ITER,
    PARADA_SIN_MEJORA,
    PARADA_UMBRAL,
    run_self_review,
)


def _score(total: int, sin_ceros: bool = True) -> RubricScore:
    """RubricScore con un total dado, repartido en 5 dimensiones (todas >0 por defecto)."""
    base = 1 if sin_ceros else 0
    dims = {"E": base, "P": base, "V": base, "F": base, "T": base}
    # sube dimensiones hasta alcanzar el total pedido (máx 3 c/u)
    resto = total - sum(dims.values())
    for k in ("E", "P", "V", "F", "T"):
        add = min(3 - dims[k], resto)
        dims[k] += add
        resto -= add
    return RubricScore(dimensiones=dims, faltantes=["mejorar"])


class _CapStub:
    def __init__(self, tag: str) -> None:
        self.tag = tag


def _make_fns(scores: list[int]):
    """Callables cuyo juez devuelve `scores` en orden. Cada revisión produce un cap etiquetado."""
    caps = [_CapStub(f"v{i}") for i in range(len(scores))]
    state = {"i": 0, "revise_calls": 0}

    def generate_fn():
        return caps[0]

    def judge_fn(cap):
        idx = caps.index(cap)
        return _score(scores[idx])

    def revise_fn(_cap, _faltantes):
        state["revise_calls"] += 1
        return caps[state["revise_calls"]]

    return generate_fn, judge_fn, revise_fn, state, caps


def test_keep_best_scores_crecientes_gana_la_ultima():
    gen, judge, rev, state, caps = _make_fns([8, 10, 13])  # 13 pasa el gate
    cap, trace = run_self_review(
        generate_fn=gen, judge_fn=judge, revise_fn=rev, min_total=11, max_iter=3
    )
    assert cap is caps[2]
    assert trace.iter_ganadora == 2
    assert trace.score_inicial == 8 and trace.score_final == 13
    assert trace.motivo_parada == PARADA_UMBRAL
    assert trace.n_iteraciones == 2


def test_keep_best_scores_decrecientes_gana_la_primera():
    # 9 (no pasa) → 8 (empeora) → para por sin_mejora, conserva la primera revisión evaluada.
    gen, judge, rev, state, caps = _make_fns([9, 8, 7])
    cap, trace = run_self_review(
        generate_fn=gen, judge_fn=judge, revise_fn=rev, min_total=11, max_iter=3
    )
    assert cap is caps[0]  # el mejor sigue siendo la generación inicial
    assert trace.iter_ganadora == 0
    assert trace.motivo_parada == PARADA_SIN_MEJORA
    assert state["revise_calls"] == 1  # revisó una vez, no mejoró, paró


def test_parada_por_umbral_sin_revisiones():
    gen, judge, rev, state, caps = _make_fns([12])  # ya pasa a la primera
    cap, trace = run_self_review(
        generate_fn=gen, judge_fn=judge, revise_fn=rev, min_total=11, max_iter=3
    )
    assert cap is caps[0]
    assert trace.motivo_parada == PARADA_UMBRAL
    assert trace.n_iteraciones == 0
    assert state["revise_calls"] == 0  # selectivo: no revisa lo que ya pasa


def test_parada_por_max_iter_mejorando_sin_alcanzar_umbral():
    # sube siempre pero nunca llega a 11: agota max_iter y conserva el mejor (el último, 10).
    gen, judge, rev, state, caps = _make_fns([6, 7, 8, 9, 10])
    cap, trace = run_self_review(
        generate_fn=gen, judge_fn=judge, revise_fn=rev, min_total=11, max_iter=3
    )
    assert state["revise_calls"] == 3  # exactamente max_iter revisiones
    assert trace.motivo_parada == PARADA_MAX_ITER
    assert cap is caps[3]  # mejor de los evaluados (score 9, tras 3 revisiones)
    assert trace.score_final == 9


def test_gate_respeta_dimension_en_cero():
    # total 12 pero una dimensión en 0 → no pasa el gate → intenta revisar.
    caps = [_CapStub("v0"), _CapStub("v1")]
    state = {"revise_calls": 0}

    def gen():
        return caps[0]

    def judge(cap):
        if cap is caps[0]:
            return RubricScore(dimensiones={"E": 3, "P": 3, "V": 3, "F": 3, "T": 0})  # 12, un 0
        return RubricScore(dimensiones={"E": 3, "P": 3, "V": 3, "F": 2, "T": 2})  # 13 pasa

    def rev(_c, _f):
        state["revise_calls"] += 1
        return caps[1]

    cap, trace = run_self_review(
        generate_fn=gen, judge_fn=judge, revise_fn=rev, min_total=11, max_iter=3
    )
    assert state["revise_calls"] == 1
    assert cap is caps[1]
    assert trace.motivo_parada == PARADA_UMBRAL
