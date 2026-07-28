"""Harness de evaluación de retrieval (Fase 14, T14.1).

Corre el gold set (`tests/fixtures/gold_set.json`) contra el índice pgvector real y reporta,
por consulta y agregado: context precision, cross-sector contamination, hit-rate sectorial,
nº de chunks correctos y score medio sectorial. Fija la LÍNEA BASE reproducible.

Uso:
    uv run python scripts/eval_retrieval.py                 # modo filtrado (produccion, ADR-012)
    uv run python scripts/eval_retrieval.py --mode raw      # sin filtro sectorial (contraste)
    uv run python scripts/eval_retrieval.py --save docs/decisions/fase14_baseline.json
    uv run python scripts/eval_retrieval.py --bench         # ademas cronometra latencia de search

Requiere: Ollama vivo (nomic-embed-text) + PostgreSQL/pgvector con el corpus ingestado.
Determinista: nomic-embed-text es estable para el mismo input; el gold set y el scoring son
fijos. La única variable es el estado del corpus en BD (se congela en el snapshot guardado).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

for _noisy in ("sqlalchemy.engine", "httpx", "httpcore"):
    _lg = logging.getLogger(_noisy)
    _lg.setLevel(logging.WARNING)
    _lg.disabled = True  # silencia el echo=True del engine sin depender de APP_ENV

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ic.data.database import SessionLocal  # noqa: E402
from ic.data.repositories.embedding_repo import EmbeddingRepository  # noqa: E402
from ic.domain.eval.retrieval_metrics import (  # noqa: E402
    RetrievedChunk,
    aggregate,
    evaluate_query,
)
from ic.infrastructure.retrieval.embedder import Embedder  # noqa: E402
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore  # noqa: E402
from ic.shared.config import get_settings  # noqa: E402

_GOLD_SET = _ROOT / "tests" / "fixtures" / "gold_set.json"


def _to_retrieved(chunks) -> list[RetrievedChunk]:
    """Adapta ChunkResult (infra) a RetrievedChunk (domain puro)."""
    out: list[RetrievedChunk] = []
    for c in chunks:
        meta = c.metadatos or {}
        sector = meta.get("sector_gics")
        sectores = tuple(meta.get("sectores") or ())  # DT-053: array multi-sector
        out.append(
            RetrievedChunk(
                sector_gics=sector,
                score=round(float(c.score), 4),
                sectores=sectores,
            )
        )
    return out


def _time_sql(repo, query_vec, settings, sector_arg) -> float:
    """Cronometra una sola llamada a search_similar (SQL puro, sin embedding)."""
    t0 = time.perf_counter()
    repo.search_similar(
        query_vec, settings.rag_top_k, settings.rag_similarity_threshold,
        sector_gics=sector_arg,
        max_chunks_per_doc=settings.rag_max_chunks_per_doc,
        mmr_lambda=getattr(settings, "rag_mmr_lambda", 0.7),
    )
    return time.perf_counter() - t0


def _fmt_row(m) -> str:
    return (
        f"  {m.expected_sector:>5}  prec={m.precision:.2f}  "
        f"cont={m.contamination:.2f}  hit={m.hit:.0f}  "
        f"n_ok={m.n_correct:<2}  score={m.mean_score:.3f}  | {m.query[:52]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness de evaluación de retrieval (T14.1)")
    parser.add_argument(
        "--mode", choices=["filtered", "raw"], default="filtered",
        help="filtered = con filtro sectorial (ADR-012); raw = sin filtro (contraste)",
    )
    parser.add_argument("--save", default=None, help="Ruta para guardar el snapshot JSON")
    parser.add_argument("--bench", action="store_true", help="Cronometrar latencia de search()")
    parser.add_argument(
        "--bench-sql", action="store_true",
        help="Cronometrar SOLO el SQL (embebe una vez por consulta; aísla el efecto del índice)",
    )
    parser.add_argument("--gold", default=str(_GOLD_SET), help="Ruta del gold set")
    parser.add_argument(
        "--mmr-lambda", type=float, default=None,
        help="Override de rag_mmr_lambda (1.0 = sin MMR; 0.7 = MMR). Para A/B antes/después.",
    )
    parser.add_argument(
        "--warm", action="store_true",
        help="Ejecutar en batch_mode (keep_alive positivo). Mide colapso de latencia en lotes.",
    )
    args = parser.parse_args()

    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    queries = gold["queries"]

    settings = get_settings()
    embedder = Embedder(settings)

    per_query = []
    latencies: list[float] = []
    sql_latencies: list[float] = []

    def _run_queries(db):
        repo = EmbeddingRepository(db)
        store = PGVectorStore(embedder, repo, settings)
        if args.mmr_lambda is not None:
            store._mmr_lambda = args.mmr_lambda
        for item in queries:
            sector = item["sector_esperado"]
            query = item["query"]
            sector_arg = sector if args.mode == "filtered" else None
            t0 = time.perf_counter()
            chunks = store.search(query, sector_gics=sector_arg)
            latencies.append(time.perf_counter() - t0)
            per_query.append(evaluate_query(query, sector, _to_retrieved(chunks)))

            if args.bench_sql:
                qv = embedder.embed(query)
                best = min(
                    _time_sql(repo, qv, settings, sector_arg) for _ in range(3)
                )
                sql_latencies.append(best)

    with SessionLocal() as db:
        if args.warm:
            with embedder.batch_mode():
                _run_queries(db)
        else:
            _run_queries(db)

    agg = aggregate(per_query)

    print(f"\n=== Retrieval eval — modo={args.mode} — {agg['n_queries']} consultas ===")
    for m in per_query:
        print(_fmt_row(m))
    print("\n--- Agregado ---")
    print(f"  context precision      : {agg['precision']:.4f}")
    print(f"  cross-sector contam.   : {agg['contamination']:.4f}")
    print(f"  hit-rate sectorial     : {agg['hit_rate']:.4f}")
    print(f"  chunks correctos (avg) : {agg['avg_correct_chunks']:.4f}")
    print(f"  score medio sectorial  : {agg['mean_score']:.4f}")
    if args.bench:
        lat_sorted = sorted(latencies)
        p50 = lat_sorted[len(lat_sorted) // 2]
        p95 = lat_sorted[min(len(lat_sorted) - 1, int(len(lat_sorted) * 0.95))]
        warm_tag = " [warm/batch]" if args.warm else " [cold/default]"
        print(f"\n--- Latencia search() (embed + SQL){warm_tag} ---")
        print(f"  media={sum(latencies) / len(latencies) * 1000:.1f}ms  "
              f"p50={p50 * 1000:.1f}ms  p95={p95 * 1000:.1f}ms")
    if args.bench_sql and sql_latencies:
        sl = sorted(sql_latencies)
        print("\n--- Latencia SQL-only (search_similar, sin embed) ---")
        print(f"  media={sum(sql_latencies) / len(sql_latencies) * 1000:.2f}ms  "
              f"p50={sl[len(sl) // 2] * 1000:.2f}ms  "
              f"max={sl[-1] * 1000:.2f}ms")

    if args.save:
        import inspect

        from ic.infrastructure.retrieval import chunker as _chunker
        _sig = inspect.signature(_chunker.chunk_text)
        snapshot = {
            "mode": args.mode,
            "warm": args.warm,
            "chunk_size": _sig.parameters["chunk_size"].default,
            "overlap": _sig.parameters["overlap"].default,
            "config": {
                "rag_top_k": settings.rag_top_k,
                "rag_similarity_threshold": settings.rag_similarity_threshold,
                "rag_max_chunks_per_doc": settings.rag_max_chunks_per_doc,
                "rag_sector_reserve": settings.rag_sector_reserve,
                "rag_sector_reserve_threshold": settings.rag_sector_reserve_threshold,
                "rag_mmr_lambda": (
                    args.mmr_lambda if args.mmr_lambda is not None
                    else getattr(settings, "rag_mmr_lambda", None)
                ),
            },
            "aggregate": agg,
            "per_query": [
                {
                    "sector": m.expected_sector, "query": m.query,
                    "precision": round(m.precision, 4),
                    "contamination": round(m.contamination, 4),
                    "hit": m.hit, "n_correct": m.n_correct,
                    "mean_score": round(m.mean_score, 4),
                }
                for m in per_query
            ],
        }
        if args.bench:
            snapshot["latency_ms"] = {
                "mean": round(sum(latencies) / len(latencies) * 1000, 2),
            }
        if args.bench_sql and sql_latencies:
            snapshot["latency_sql_ms"] = {
                "mean": round(sum(sql_latencies) / len(sql_latencies) * 1000, 3),
                "max": round(max(sql_latencies) * 1000, 3),
            }
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSnapshot guardado en {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
