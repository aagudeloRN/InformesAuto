"""T008 — Regression tests for fuente_tipo_filter in EmbeddingRepository.search_similar.

Fast (no DB): verifica que el WHERE incluye/excluye la cláusula fuente_tipo según el valor
del parámetro. Usa _CapturingSession (misma clase que test_fase22_reserva_emis.py).
"""

from __future__ import annotations

from ic.data.repositories.embedding_repo import EmbeddingRepository


class _FakeResult:
    def fetchall(self) -> list:
        return []


class _CapturingSession:
    def __init__(self) -> None:
        self.sqls: list[str] = []

    def execute(self, sql, params=None):
        self.sqls.append(str(sql))
        return _FakeResult()

    def get(self, *_args, **_kwargs):
        return None


def _run_search(**kwargs) -> str:
    db = _CapturingSession()
    repo = EmbeddingRepository(db)
    repo.search_similar([0.1, 0.2, 0.3], top_k=5, threshold=0.5, **kwargs)
    assert db.sqls, "search_similar debió ejecutar al menos una consulta"
    return db.sqls[-1]


def test_fuente_tipo_filter_none_preserva_comportamiento() -> None:
    sql = _run_search(fuente_tipo_filter=None)
    assert "fuente_tipo" not in sql


def test_fuente_tipo_filter_emis_aplica_clausula() -> None:
    sql = _run_search(fuente_tipo_filter="emis")
    assert "e.fuente_tipo = :fuente_tipo" in sql
