"""Gate de costo/latencia/calidad sobre snapshots del harness (Fase 15, T15.4).

Compara un snapshot JSON del harness de evaluación (eval_retrieval.py --save)
contra un presupuesto configurable (docs/decisions/fase15_budget.json). Exit ≠ 0
si alguna métrica supera el umbral definido.

Uso:
    uv run python scripts/eval_gate.py --snapshot docs/decisions/fase14_final_filtered.json
    uv run python scripts/eval_gate.py --snapshot fase15_warm.json --budget custom_budget.json

El gate verifica (según las claves disponibles en el snapshot):
  - latency_ms.mean      ≤ max_latency_ms
  - latency_sql_ms.mean  ≤ max_latency_sql_ms
  - aggregate.precision  ≥ min_precision
  - aggregate.contamination ≤ max_contamination
  - aggregate.hit_rate   ≥ min_hit_rate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_BUDGET = _ROOT / "docs" / "decisions" / "fase15_budget.json"


def _check(label: str, value: float, limit: float, direction: str) -> bool:
    """Comprueba un umbral. direction='max' → value ≤ limit; 'min' → value ≥ limit."""
    if direction == "max":
        ok = value <= limit
        symbol = "≤"
    else:
        ok = value >= limit
        symbol = "≥"
    status = "✅" if ok else "❌"
    print(f"  {status} {label}: {value:.4f} {symbol} {limit}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate de latencia/costo/calidad (T15.4)")
    parser.add_argument("--snapshot", required=True, help="Ruta al snapshot JSON del harness")
    parser.add_argument(
        "--budget", default=str(_DEFAULT_BUDGET), help="Ruta al presupuesto JSON"
    )
    args = parser.parse_args()

    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    budget = json.loads(Path(args.budget).read_text(encoding="utf-8"))

    print(f"\n=== Gate de calidad/latencia/costo ===")
    print(f"  Snapshot : {args.snapshot}")
    print(f"  Presupuesto: {args.budget}\n")

    failures: list[str] = []

    # Latencia embed+SQL (solo si el snapshot tiene --bench)
    if "latency_ms" in snapshot:
        lat = snapshot["latency_ms"]["mean"]
        limit = budget.get("max_latency_ms", float("inf"))
        if not _check("latency_ms.mean", lat, limit, "max"):
            failures.append(f"latency_ms.mean={lat:.1f} > max={limit}")

    # Latencia SQL pura (--bench-sql)
    if "latency_sql_ms" in snapshot:
        sql_lat = snapshot["latency_sql_ms"]["mean"]
        limit = budget.get("max_latency_sql_ms", float("inf"))
        if not _check("latency_sql_ms.mean", sql_lat, limit, "max"):
            failures.append(f"latency_sql_ms.mean={sql_lat:.3f} > max={limit}")

    # Métricas de calidad del retrieval
    agg = snapshot.get("aggregate", {})
    if "precision" in agg:
        v = agg["precision"]
        limit = budget.get("min_precision", 0.0)
        if not _check("precision", v, limit, "min"):
            failures.append(f"precision={v:.4f} < min={limit}")

    if "contamination" in agg:
        v = agg["contamination"]
        limit = budget.get("max_contamination", 1.0)
        if not _check("contamination", v, limit, "max"):
            failures.append(f"contamination={v:.4f} > max={limit}")

    if "hit_rate" in agg:
        v = agg["hit_rate"]
        limit = budget.get("min_hit_rate", 0.0)
        if not _check("hit_rate", v, limit, "min"):
            failures.append(f"hit_rate={v:.4f} < min={limit}")

    print()
    if failures:
        print(f"❌ GATE FALLÓ — {len(failures)} violación(es):")
        for f in failures:
            print(f"   • {f}")
        return 1

    print("✅ Gate verde — todas las métricas dentro del presupuesto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
