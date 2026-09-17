"""Pruebas unitarias para Reconciliacion por NIT (Spec 007 / DT-050b)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ic.domain.use_cases.reconcile_entidades import (
    ReconcileEntidades,
    _select_canonical_entity,
)


def test_select_canonical_entity_prioritizes_verificado():
    miembros = [
        {"id": 1, "nombre": "Empresa A", "estado": "candidato", "n_atributos": 10},
        {"id": 2, "nombre": "Empresa A S.A.S.", "estado": "verificado", "n_atributos": 1},
    ]
    canonical, duplicates = _select_canonical_entity(miembros)
    assert canonical["id"] == 2
    assert len(duplicates) == 1
    assert duplicates[0]["id"] == 1


def test_select_canonical_entity_prioritizes_n_atributos_when_same_state():
    miembros = [
        {
            "id": 10,
            "nombre": "Alpha Corp",
            "estado": "candidato",
            "n_atributos": 2,
            "n_menciones": 100,
        },
        {
            "id": 20,
            "nombre": "Alpha Corp SA",
            "estado": "candidato",
            "n_atributos": 15,
            "n_menciones": 5,
        },
    ]
    canonical, duplicates = _select_canonical_entity(miembros)
    assert canonical["id"] == 20
    assert len(duplicates) == 1
    assert duplicates[0]["id"] == 10


def test_select_canonical_entity_prioritizes_longer_name_when_same_atributos():
    miembros = [
        {"id": 100, "nombre": "Beta", "estado": "candidato", "n_atributos": 5},
        {"id": 101, "nombre": "Beta Colombia S.A.S.", "estado": "candidato", "n_atributos": 5},
    ]
    canonical, duplicates = _select_canonical_entity(miembros)
    assert canonical["id"] == 101
    assert duplicates[0]["id"] == 100


def test_reconcile_use_case_dry_run():
    mock_repo = MagicMock()
    mock_repo.list_duplicados_por_nit.return_value = [
        {
            "nit": "900123456",
            "miembros": [
                {"id": 1, "nombre": "Erco", "estado": "candidato", "n_atributos": 2},
                {
                    "id": 2,
                    "nombre": "Erco Energia S.A.S.",
                    "estado": "verificado",
                    "n_atributos": 10,
                },
            ],
        }
    ]

    use_case = ReconcileEntidades(mock_repo)
    result = use_case.reconcile(dry_run=True)

    assert result["total_grupos"] == 1
    assert result["total_fusionadas"] == 1
    assert result["dry_run"] is True
    assert len(result["grupos"]) == 1
    assert result["grupos"][0]["canonica_id"] == 2
    assert result["grupos"][0]["duplicados_ids"] == [1]
    mock_repo.merge_entidades_por_nit.assert_not_called()


def test_reconcile_use_case_execute():
    mock_repo = MagicMock()
    mock_repo.list_duplicados_por_nit.return_value = [
        {
            "nit": "900123456",
            "miembros": [
                {"id": 1, "nombre": "Erco", "estado": "candidato", "n_atributos": 2},
                {
                    "id": 2,
                    "nombre": "Erco Energia S.A.S.",
                    "estado": "verificado",
                    "n_atributos": 10,
                },
            ],
        }
    ]

    use_case = ReconcileEntidades(mock_repo)
    result = use_case.reconcile(dry_run=False)

    assert result["total_grupos"] == 1
    assert result["total_fusionadas"] == 1
    assert result["dry_run"] is False
    mock_repo.merge_entidades_por_nit.assert_called_once_with(2, [1])
