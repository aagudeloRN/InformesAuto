"""MMR (Maximal Marginal Relevance) — reranking por diversidad de documento (Fase 14, T14.2).

Portado de `~/Test/RepositorioRN/app/backend/services/rag/mmr.py`, adaptado para penalizar
por `documento_id` (no por id de chunk): un informe sectorial grande (cientos de chunks) no
debe monopolizar los slots de contexto.

Algoritmo: para cada candidato (ordenado por similitud desc.) se aplica una penalización
proporcional a cuántos chunks del mismo documento ya se seleccionaron. λ controla el balance
similitud/diversidad:
  - λ = 1.0 → ranking por pura similitud (sin efecto de diversidad; se devuelve tal cual)
  - λ = 0.7 → 70% similitud / 30% penalización por diversidad (default)
  - λ = 0.0 → pura diversidad (maximiza variedad de documentos)

Función pura, sin dependencias externas. Reordena; NO elimina candidatos (el cap duro por
documento y el top_k se aplican después, en la capa que llama).
"""

from __future__ import annotations

from typing import Any


def apply_mmr_reranking(
    items: list[dict[str, Any]],
    mmr_lambda: float = 0.7,
    doc_key: str = "doc_id",
    score_key: str = "score",
) -> list[dict[str, Any]]:
    """Reordena `items` (dicts con `score_key` y `doc_key`) por score MMR.

    Los items sin documento asociado (`doc_key` es None, p.ej. chunks web) reciben una
    identidad de documento única por su posición, de modo que no se penalizan entre sí.
    """
    if not items or mmr_lambda >= 1.0:
        return items

    doc_representation: dict[Any, int] = {}
    reranked: list[dict[str, Any]] = []

    for pos, item in enumerate(sorted(items, key=lambda x: x[score_key], reverse=True)):
        # Chunks sin documento (web) no comparten identidad → no se penalizan mutuamente.
        doc_id = item.get(doc_key)
        key = doc_id if doc_id is not None else f"__nodoc_{pos}"
        doc_count = doc_representation.get(key, 0)
        penalty = doc_count * (1.0 - mmr_lambda)
        mmr_score = item[score_key] * mmr_lambda - penalty
        reranked.append({**item, "mmr_score": round(mmr_score, 4)})
        doc_representation[key] = doc_count + 1

    reranked.sort(key=lambda x: x["mmr_score"], reverse=True)
    return reranked
