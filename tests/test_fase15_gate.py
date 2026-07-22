"""Tests T15.4 — Gate de latencia/costo/calidad (Fase 15)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_GATE_SCRIPT = _ROOT / "scripts" / "eval_gate.py"
_BUDGET = _ROOT / "docs" / "decisions" / "fase15_budget.json"


def _run_gate(snapshot_data: dict, budget_data: dict, tmp_path: Path) -> int:
    """Ejecuta el gate con snapshot y budget temporales; devuelve el exit code."""
    snap_file = tmp_path / "snapshot.json"
    budget_file = tmp_path / "budget.json"
    snap_file.write_text(json.dumps(snapshot_data), encoding="utf-8")
    budget_file.write_text(json.dumps(budget_data), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(_GATE_SCRIPT),
         "--snapshot", str(snap_file), "--budget", str(budget_file)],
        capture_output=True,
    )
    return result.returncode


def _baseline_snapshot() -> dict:
    return {
        "mode": "filtered",
        "aggregate": {
            "n_queries": 25,
            "precision": 1.0,
            "contamination": 0.0,
            "hit_rate": 1.0,
            "avg_correct_chunks": 3.68,
            "mean_score": 0.76,
        },
        "latency_sql_ms": {"mean": 15.0, "max": 22.0},
    }


def _baseline_budget() -> dict:
    return {
        "max_latency_sql_ms": 50.0,
        "min_precision": 0.95,
        "max_contamination": 0.05,
        "min_hit_rate": 0.95,
    }


# ---------------------------------------------------------------------------
# Gate pasa con la línea base
# ---------------------------------------------------------------------------


def test_gate_passes_on_baseline(tmp_path):
    """El gate devuelve 0 con las métricas de línea base de Fase 14."""
    rc = _run_gate(_baseline_snapshot(), _baseline_budget(), tmp_path)
    assert rc == 0, "El gate debería pasar en la línea base"


# ---------------------------------------------------------------------------
# Gate falla ante regresiones inyectadas
# ---------------------------------------------------------------------------


def test_gate_fails_on_sql_latency_regression(tmp_path):
    """SQL latency > max_latency_sql_ms → exit 1."""
    snap = _baseline_snapshot()
    snap["latency_sql_ms"] = {"mean": 80.0, "max": 100.0}  # regresión
    budget = _baseline_budget()
    budget["max_latency_sql_ms"] = 50.0
    rc = _run_gate(snap, budget, tmp_path)
    assert rc != 0, "El gate debería fallar con latencia SQL regresada"


def test_gate_fails_on_precision_regression(tmp_path):
    """Precision < min_precision → exit 1."""
    snap = _baseline_snapshot()
    snap["aggregate"]["precision"] = 0.60  # regresión grave
    rc = _run_gate(snap, _baseline_budget(), tmp_path)
    assert rc != 0


def test_gate_fails_on_contamination_regression(tmp_path):
    """Contamination > max_contamination → exit 1."""
    snap = _baseline_snapshot()
    snap["aggregate"]["contamination"] = 0.30  # cross-sector contaminado
    rc = _run_gate(snap, _baseline_budget(), tmp_path)
    assert rc != 0


def test_gate_fails_on_hit_rate_regression(tmp_path):
    """Hit-rate < min_hit_rate → exit 1."""
    snap = _baseline_snapshot()
    snap["aggregate"]["hit_rate"] = 0.60
    rc = _run_gate(snap, _baseline_budget(), tmp_path)
    assert rc != 0


def test_gate_fails_on_embed_latency_regression(tmp_path):
    """latency_ms.mean > max_latency_ms → exit 1."""
    snap = _baseline_snapshot()
    snap["latency_ms"] = {"mean": 4000.0}  # peor que el default frío
    budget = _baseline_budget()
    budget["max_latency_ms"] = 3000.0
    rc = _run_gate(snap, budget, tmp_path)
    assert rc != 0


# ---------------------------------------------------------------------------
# Gate pasa si la métrica mejoró
# ---------------------------------------------------------------------------


def test_gate_passes_on_improved_latency(tmp_path):
    """latency_ms.mean muy bajo (modo warm) → sigue pasando el gate."""
    snap = _baseline_snapshot()
    snap["latency_ms"] = {"mean": 300.0}  # modelo cargado en memoria
    budget = _baseline_budget()
    budget["max_latency_ms"] = 3000.0
    rc = _run_gate(snap, budget, tmp_path)
    assert rc == 0


# ---------------------------------------------------------------------------
# Budget de Fase 15 existe y es válido
# ---------------------------------------------------------------------------


def test_fase15_budget_file_exists_and_valid():
    assert _BUDGET.exists(), "docs/decisions/fase15_budget.json debe existir"
    data = json.loads(_BUDGET.read_text(encoding="utf-8"))
    assert "max_latency_ms" in data
    assert "max_latency_sql_ms" in data
    assert data["max_latency_sql_ms"] > 0


def test_gate_passes_against_fase14_snapshot(tmp_path):
    """El snapshot real de Fase 14 pasa el budget de Fase 15."""
    fase14_snap = _ROOT / "docs" / "decisions" / "fase14_final_filtered.json"
    if not fase14_snap.exists():
        pytest.skip("snapshot Fase 14 no disponible")
    rc = _run_gate(
        json.loads(fase14_snap.read_text(encoding="utf-8")),
        json.loads(_BUDGET.read_text(encoding="utf-8")),
        tmp_path,
    )
    assert rc == 0, "El snapshot de Fase 14 debe pasar el presupuesto de Fase 15"
