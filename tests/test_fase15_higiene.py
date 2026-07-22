"""Tests T15.5 — Higiene: scoping de purge_unused_web_backlog (Fase 15)."""

from __future__ import annotations

from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# purge_unused_web_backlog — comportamiento con y sin limit_ids
# ---------------------------------------------------------------------------


def _make_repo(rowcount=0):
    from ic.data.repositories.embedding_repo import EmbeddingRepository

    db = MagicMock()
    db.execute.return_value.rowcount = rowcount
    return EmbeddingRepository(db)


def test_purge_sin_limit_ids_usa_query_global():
    """Sin limit_ids, la purga borra todos los legacy (comportamiento de producción)."""
    repo = _make_repo(rowcount=3)
    n = repo.purge_unused_web_backlog()

    assert n == 3
    sql_called = repo._db.execute.call_args_list[0][0][0].text
    # No debe tener cláusula de límite por IDs
    assert "ANY" not in sql_called


def test_purge_con_limit_ids_restringe_borrado():
    """Con limit_ids, la purga solo toca esos IDs concretos."""
    repo = _make_repo(rowcount=1)
    ids = ["aaaaaaaa-0000-0000-0000-000000000001"]
    n = repo.purge_unused_web_backlog(limit_ids=ids)

    assert n == 1
    # Debe haberse pasado el parámetro ids
    call_kwargs = repo._db.execute.call_args_list[0][0][1]
    assert call_kwargs["ids"] == ids


def test_purge_con_limit_ids_vacio_no_borra():
    """limit_ids=[] vacío no dispara la ruta de IDs (equivale a sin scope)."""
    repo = _make_repo(rowcount=0)
    repo.purge_unused_web_backlog(limit_ids=[])
    repo._db.execute.assert_called_once()


def test_purge_global_no_pasa_ids():
    """La llamada sin argumento (producción) no envía el parámetro ids al SQL."""
    repo = _make_repo(rowcount=0)
    repo.purge_unused_web_backlog()

    positional_params = repo._db.execute.call_args_list[0][0]
    # La llamada global pasa solo la query, sin dict de parámetros
    assert len(positional_params) == 1
