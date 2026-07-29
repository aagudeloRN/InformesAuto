"""T1a (DT-054) — La reserva sectorial estricta incluye EMIS individuales.

Antes, `sector_estricto=True` filtraba a `tipo_fuente='informe_compilado'`, dejando fuera de la
reserva garantizada a los EMIS individuales (tipo_fuente NULL pero con sector_gics seteado). Estos
tests capturan el SQL construido por `EmbeddingRepository.search_similar` (Session falsa, sin BD)
para verificar que la rama estricta ahora filtra solo por `sector_gics` y no por `tipo_fuente`.
"""

from __future__ import annotations

from ic.data.repositories.embedding_repo import EmbeddingRepository


class _FakeResult:
    def fetchall(self) -> list:
        return []


class _CapturingSession:
    """Session falsa que registra el SQL de cada execute() y devuelve 0 filas."""

    def __init__(self) -> None:
        self.sqls: list[str] = []

    def execute(self, sql, params=None):  # noqa: ANN001
        self.sqls.append(str(sql))
        return _FakeResult()

    def get(self, *_args, **_kwargs):  # no se llega a materializar objetos (0 filas)
        return None


def _run_search(**kwargs) -> str:
    db = _CapturingSession()
    repo = EmbeddingRepository(db)
    repo.search_similar([0.1, 0.2, 0.3], top_k=3, threshold=0.5, **kwargs)
    assert db.sqls, "search_similar debió ejecutar al menos una consulta"
    return db.sqls[-1]


def test_reserva_sectorial_estricta_incluye_emis_individuales() -> None:
    sql = _run_search(sector_gics="3020", sector_estricto=True)
    # Filtra por sector...
    assert "e.metadatos->>'sector_gics' = :sector" in sql
    # ...pero ya NO restringe a informe_compilado (así entran los EMIS individuales).
    assert "informe_compilado" not in sql


def test_busqueda_sectorial_no_estricta_sin_cambios() -> None:
    sql = _run_search(sector_gics="3020", sector_estricto=False)
    # La rama laxa mantiene su condición amplia (sector + multi-sector + fuentes sin sector).
    assert "jsonb_exists(e.metadatos->'sectores', :sector)" in sql
    assert "informe_compilado" not in sql


def test_reserva_global_estricta_no_afectada() -> None:
    sql = _run_search(global_estricto=True)
    assert "e.metadatos->>'es_global' = 'true'" in sql
