"""Métricas puras de calidad de retrieval (T14.1).

Funciones sin I/O ni dependencias externas (Dependency Agnosticism): operan sobre una lista
de `RetrievedChunk` ya recuperados. El harness (`scripts/eval_retrieval.py`) es quien habla
con la BD y adapta los `ChunkResult` a esta estructura.

Convención de sector:
- `sector_gics is None`  → fuente sin sector (web / académica). No cuenta como contaminación.
- `sector_gics == esperado` → evidencia sectorial correcta.
- cualquier otro valor    → contaminación cross-sector (ruido).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    """Un chunk recuperado, reducido a lo que las métricas necesitan."""

    sector_gics: str | None
    score: float = 0.0


def context_precision(retrieved: list[RetrievedChunk], expected_sector: str) -> float:
    """Fracción de chunks *con sector* que son del sector correcto.

    Ignora los chunks sin sector (web): mide qué tan limpio es el material sectorial.
    Devuelve 1.0 si no se recuperó ningún chunk con sector (no hay ruido sectorial).
    """
    con_sector = [r for r in retrieved if r.sector_gics is not None]
    if not con_sector:
        return 1.0
    correctos = sum(1 for r in con_sector if r.sector_gics == expected_sector)
    return correctos / len(con_sector)


def cross_sector_contamination(
    retrieved: list[RetrievedChunk], expected_sector: str
) -> float:
    """Fracción del top-k que pertenece a un sector distinto del esperado (y no NULL)."""
    if not retrieved:
        return 0.0
    malos = sum(
        1 for r in retrieved if r.sector_gics not in (None, expected_sector)
    )
    return malos / len(retrieved)


def sectoral_hit(retrieved: list[RetrievedChunk], expected_sector: str) -> float:
    """Recall proxy: 1.0 si aflora ≥1 chunk del sector correcto, si no 0.0.

    El corpus tiene 1 documento por sector, por lo que "recuperar el documento correcto"
    equivale a "recuperar ≥1 chunk del sector correcto".
    """
    return 1.0 if any(r.sector_gics == expected_sector for r in retrieved) else 0.0


def n_correct_chunks(retrieved: list[RetrievedChunk], expected_sector: str) -> int:
    """Cuántos chunks del sector correcto se recuperaron (diversidad de evidencia)."""
    return sum(1 for r in retrieved if r.sector_gics == expected_sector)


def mean_sector_score(retrieved: list[RetrievedChunk], expected_sector: str) -> float:
    """Score medio de los chunks del sector correcto (0.0 si no hay)."""
    scores = [r.score for r in retrieved if r.sector_gics == expected_sector]
    return sum(scores) / len(scores) if scores else 0.0


@dataclass(frozen=True)
class QueryMetrics:
    query: str
    expected_sector: str
    n_retrieved: int
    precision: float
    contamination: float
    hit: float
    n_correct: int
    mean_score: float


def evaluate_query(
    query: str, expected_sector: str, retrieved: list[RetrievedChunk]
) -> QueryMetrics:
    """Calcula todas las métricas para una consulta del gold set."""
    return QueryMetrics(
        query=query,
        expected_sector=expected_sector,
        n_retrieved=len(retrieved),
        precision=context_precision(retrieved, expected_sector),
        contamination=cross_sector_contamination(retrieved, expected_sector),
        hit=sectoral_hit(retrieved, expected_sector),
        n_correct=n_correct_chunks(retrieved, expected_sector),
        mean_score=mean_sector_score(retrieved, expected_sector),
    )


def aggregate(metrics: list[QueryMetrics]) -> dict[str, float]:
    """Promedia las métricas por consulta en un resumen agregado."""
    n = len(metrics)
    if n == 0:
        return {
            "n_queries": 0,
            "precision": 0.0,
            "contamination": 0.0,
            "hit_rate": 0.0,
            "avg_correct_chunks": 0.0,
            "mean_score": 0.0,
        }
    return {
        "n_queries": n,
        "precision": round(sum(m.precision for m in metrics) / n, 4),
        "contamination": round(sum(m.contamination for m in metrics) / n, 4),
        "hit_rate": round(sum(m.hit for m in metrics) / n, 4),
        "avg_correct_chunks": round(sum(m.n_correct for m in metrics) / n, 4),
        "mean_score": round(sum(m.mean_score for m in metrics) / n, 4),
    }
