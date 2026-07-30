"""DT-059/T4 — Trazabilidad de auto-revisión: migración idempotente + mapeo del repo.

Fast (sin BD real): engine/sesión falsos verifican el contrato SQL (IF NOT EXISTS, esquema
propio) y que el repo mapea los campos de la RevisionTrace a la fila.
"""

from __future__ import annotations

from ic.data.models.revision_capitulo import ensure_revisiones_tables


class _FakeConn:
    def __init__(self, sqls):
        self._sqls = sqls

    def execute(self, sql):
        self._sqls.append(str(sql))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeEngine:
    def __init__(self):
        self.sqls: list[str] = []

    def begin(self):
        return _FakeConn(self.sqls)


def test_ensure_revisiones_idempotente():
    eng = _FakeEngine()
    ensure_revisiones_tables(eng)
    ensure_revisiones_tables(eng)  # dos veces sin error

    unido = " ".join(eng.sqls)
    assert unido.count("CREATE TABLE IF NOT EXISTS") >= 2  # tabla x 2 corridas
    assert "informes_ic.revisiones_capitulo" in unido  # esquema propio
    assert "CREATE INDEX IF NOT EXISTS ix_revision_runkey" in unido


class _FakeSession:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def test_save_revision_mapea_campos():
    from ic.data.repositories.revision_repo import RevisionRepository

    db = _FakeSession()
    RevisionRepository(db).save_revision(
        run_key="rk", capitulo="Cap 2 — Análisis Competitivo", sabor="web",
        n_iteraciones=2, iter_ganadora=2, score_inicial=8, score_final=13,
        motivo_parada="umbral", dimensiones={"E": 3, "P": 2, "V": 3, "F": 2, "T": 3},
        faltantes=[],
    )
    assert db.commits == 1
    row = db.added[0]
    assert row.run_key == "rk"
    assert row.capitulo == "Cap 2 — Análisis Competitivo"
    assert row.sabor == "web"
    assert row.score_inicial == 8 and row.score_final == 13
    assert row.motivo_parada == "umbral"
    assert row.dimensiones["E"] == 3


def test_persist_trace_desde_hook_es_best_effort(monkeypatch):
    """El hook nunca aborta si la BD falla (patrón checkpoint)."""
    from ic.domain.eval.rubric_score import RubricScore
    from ic.domain.eval.self_review import RevisionTrace
    from ic.domain.use_cases import self_review_hooks as hooks

    trace = RevisionTrace(
        intentos=[RubricScore(dimensiones={"E": 1, "P": 1, "V": 1, "F": 1, "T": 1})],
        iter_ganadora=0, motivo_parada="max_iter",
    )
    # Simula fallo de BD: ensure_revisiones_tables inaccesible → no debe propagar.

    def _boom(*_a, **_k):
        raise RuntimeError("BD caída")

    monkeypatch.setattr("ic.data.database.engine", object(), raising=False)
    monkeypatch.setattr(
        "ic.data.models.revision_capitulo.ensure_revisiones_tables", _boom, raising=True
    )
    # No lanza:
    hooks._persist_trace("rk", "Cap 5", "integracion", trace)
