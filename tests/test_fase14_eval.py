"""Tests Fase 14 — métricas de evaluación de retrieval (fast, puras)."""

import json
from pathlib import Path

from ic.domain.eval.retrieval_metrics import (
    QueryMetrics,
    RetrievedChunk,
    aggregate,
    context_precision,
    cross_sector_contamination,
    evaluate_query,
    mean_sector_score,
    n_correct_chunks,
    sectoral_hit,
)

_GOLD = Path(__file__).parent / "fixtures" / "gold_set.json"


def _c(sector, score=0.7):
    return RetrievedChunk(sector_gics=sector, score=score)


# --- context_precision ---


def test_precision_todos_correctos():
    r = [_c("2530"), _c("2530"), _c(None)]  # el None (web) no cuenta
    assert context_precision(r, "2530") == 1.0


def test_precision_con_contaminacion():
    r = [_c("2530"), _c("4010"), _c(None)]  # 1 de 2 con-sector es correcto
    assert context_precision(r, "2530") == 0.5


def test_precision_sin_chunks_con_sector_es_uno():
    # Solo web recuperada: no hay ruido sectorial → precision perfecta por convención
    assert context_precision([_c(None), _c(None)], "2530") == 1.0
    assert context_precision([], "2530") == 1.0


# --- cross_sector_contamination ---


def test_contaminacion_cuenta_solo_sector_equivocado():
    r = [_c("2530"), _c("4010"), _c(None), _c("1510")]  # 2 malos de 4
    assert cross_sector_contamination(r, "2530") == 0.5


def test_contaminacion_web_no_contamina():
    r = [_c("2530"), _c(None), _c(None)]
    assert cross_sector_contamination(r, "2530") == 0.0


def test_contaminacion_lista_vacia():
    assert cross_sector_contamination([], "2530") == 0.0


# --- hit / n_correct / score ---


def test_sectoral_hit():
    assert sectoral_hit([_c("2530"), _c(None)], "2530") == 1.0
    assert sectoral_hit([_c("4010"), _c(None)], "2530") == 0.0


def test_n_correct_chunks():
    assert n_correct_chunks([_c("2530"), _c("2530"), _c("4010")], "2530") == 2


def test_mean_sector_score():
    r = [_c("2530", 0.8), _c("2530", 0.6), _c("4010", 0.9)]
    assert mean_sector_score(r, "2530") == 0.7
    assert mean_sector_score([_c("4010", 0.9)], "2530") == 0.0


# --- evaluate_query + aggregate (determinismo) ---


def test_evaluate_query_deterministico():
    r = [_c("2530", 0.8), _c("4010", 0.7), _c(None, 0.9)]
    m1 = evaluate_query("q", "2530", r)
    m2 = evaluate_query("q", "2530", r)
    assert m1 == m2
    assert isinstance(m1, QueryMetrics)
    assert m1.precision == 0.5
    assert m1.contamination == round(1 / 3, 10) or abs(m1.contamination - 1 / 3) < 1e-9
    assert m1.hit == 1.0
    assert m1.n_correct == 1


def test_aggregate_promedia():
    ms = [
        evaluate_query("a", "2530", [_c("2530")]),
        evaluate_query("b", "4010", [_c("9999")]),  # todo contaminado
    ]
    agg = aggregate(ms)
    assert agg["n_queries"] == 2
    assert agg["hit_rate"] == 0.5
    assert agg["precision"] == 0.5  # (1.0 + 0.0) / 2


def test_aggregate_vacio():
    agg = aggregate([])
    assert agg["n_queries"] == 0
    assert agg["precision"] == 0.0


# --- Gold set bien formado ---


def test_gold_set_cubre_25_sectores_unicos():
    gold = json.loads(_GOLD.read_text(encoding="utf-8"))
    sectores = [q["sector_esperado"] for q in gold["queries"]]
    assert len(sectores) == 25
    assert len(set(sectores)) == 25  # sin duplicados
    for q in gold["queries"]:
        assert q["query"].strip()
        assert q["sector_esperado"].isdigit() and len(q["sector_esperado"]) == 4
