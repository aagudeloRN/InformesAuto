"""Tests Fase 14 — MMR reranking por diversidad de documento (fast, puro)."""

from ic.infrastructure.retrieval.mmr import apply_mmr_reranking


def _item(doc_id, score):
    return {"doc_id": doc_id, "score": score}


def test_lambda_uno_es_noop():
    items = [_item("A", 0.9), _item("A", 0.8)]
    assert apply_mmr_reranking(items, mmr_lambda=1.0) is items


def test_lista_vacia():
    assert apply_mmr_reranking([], mmr_lambda=0.7) == []


def test_penaliza_documento_repetido():
    # Doc A monopoliza los tops; un chunk de B con score menor debe subir por diversidad.
    items = [
        _item("A", 0.90),
        _item("A", 0.88),
        _item("A", 0.86),
        _item("B", 0.80),
    ]
    out = apply_mmr_reranking(items, mmr_lambda=0.7)
    docs = [it["doc_id"] for it in out]
    # El primero sigue siendo el mejor de A (sin penalización).
    assert docs[0] == "A"
    # B (0.80, sin penalización) supera al 2º chunk de A (0.88 penalizado 0.3).
    assert docs[1] == "B"


def test_mmr_score_calculo_exacto():
    items = [_item("A", 0.9), _item("A", 0.8)]
    out = apply_mmr_reranking(items, mmr_lambda=0.7)
    by_score = {it["score"]: it["mmr_score"] for it in out}
    # 1er chunk de A: 0.9*0.7 - 0*0.3 = 0.63
    assert by_score[0.9] == 0.63
    # 2º chunk de A: 0.8*0.7 - 1*0.3 = 0.26
    assert by_score[0.8] == 0.26


def test_chunks_sin_documento_no_se_penalizan():
    # Dos chunks web (doc_id None) no deben penalizarse entre sí.
    items = [_item(None, 0.90), _item(None, 0.85)]
    out = apply_mmr_reranking(items, mmr_lambda=0.7)
    # Sin penalización cruzada: el orden por score se mantiene y mmr = score*lambda.
    assert [it["score"] for it in out] == [0.90, 0.85]
    assert out[0]["mmr_score"] == round(0.90 * 0.7, 4)
    assert out[1]["mmr_score"] == round(0.85 * 0.7, 4)


def test_preserva_payload():
    items = [{"doc_id": "A", "score": 0.9, "id": "chunk-1", "extra": "x"}]
    out = apply_mmr_reranking(items, mmr_lambda=0.7)
    assert out[0]["id"] == "chunk-1"
    assert out[0]["extra"] == "x"
