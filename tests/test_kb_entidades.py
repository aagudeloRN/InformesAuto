"""DT-056/T1 — KB de entidades: migración idempotente, upsert (dedup, alias, no-degrade), consulta.

Fast (sin BD real): la sesión/engine se falsifican; se verifica el contrato SQL (rutas de
conflicto, no-degradación de estado, unión de aliases) y la idempotencia. La idempotencia real
sobre la BD se comprueba en el merge (re-run = 0 nuevas).
"""

from __future__ import annotations

import json

from ic.data.models.entidad import (
    ESTADO_CANDIDATO,
    ESTADO_VERIFICADO,
    TIPO_EMPRESA,
)
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow

# --- Migración idempotente (fake engine) ---


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


def test_ensure_tablas_idempotente():
    from ic.data.models.entidad import ensure_entidades_tables

    eng = _FakeEngine()
    ensure_entidades_tables(eng)
    ensure_entidades_tables(eng)  # dos veces sin error

    unido = " ".join(eng.sqls)
    assert unido.count("CREATE TABLE IF NOT EXISTS") >= 4  # 2 tablas x 2 corridas
    assert "informes_ic.entidades" in unido
    assert "informes_ic.entidad_atributos" in unido
    # Dedup fuerte por NIT (parcial) y fallback por nombre+sector.
    assert "ux_entidad_nit" in unido and "WHERE nit IS NOT NULL" in unido
    assert "ux_entidad_nombre_sector" in unido
    # Idempotencia de atributos por (entidad, clave, fuente).
    assert "ux_entidad_atributo_clave_fuente" in unido
    # DT-061: sub_gics añadido idempotente a tablas existentes + índice de anclaje fino.
    assert "ADD COLUMN IF NOT EXISTS sub_gics TEXT" in unido
    assert "ix_entidad_sub_gics" in unido


# --- Upsert de entidad ---


class _FakeUpsertResult:
    def __init__(self, id_):
        self._id = id_

    def scalar_one(self):
        return self._id


class _FakeSession:
    """Sesión falsa: captura SQL+params, devuelve id fijo en upsert y filas canned en select."""

    def __init__(self, select_rows=None):
        self.sqls: list[str] = []
        self.params: list[dict] = []
        self.commits = 0
        self._select_rows = select_rows or []

    def execute(self, sql, params=None):
        self.sqls.append(str(sql))
        self.params.append(params or {})
        s = str(sql)
        if "RETURNING id" in s:
            return _FakeUpsertResult(42)
        if "SELECT nombre FROM" in s:
            return _FakeSelectResult(self._select_rows)
        return _FakeScalarResult(0)

    def commit(self):
        self.commits += 1


class _FakeSelectResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeScalarResult:
    def __init__(self, v):
        self._v = v

    def scalar(self):
        return self._v


def test_upsert_por_nit_usa_conflicto_nit():
    sess = _FakeSession()
    eid = EntidadRepository(sess).upsert_entidad(
        EntidadRow(nombre="Alpina S.A.", nombre_normalizado="alpina", nit="860025900",
                   sector_gics="3020", aliases=["Alpina", "ALPINA"])
    )
    assert eid == 42
    sql = sess.sqls[-1]
    assert "ON CONFLICT (nit) WHERE nit IS NOT NULL DO UPDATE" in sql
    # Aliases se serializan ordenados y sin duplicados.
    assert json.loads(sess.params[-1]["aliases"]) == ["ALPINA", "Alpina"]
    assert sess.commits == 1


def test_upsert_sin_nit_usa_conflicto_nombre_sector():
    sess = _FakeSession()
    EntidadRepository(sess).upsert_entidad(
        EntidadRow(nombre="Colanta", nombre_normalizado="colanta", sector_gics="3020")
    )
    sql = sess.sqls[-1]
    assert "ON CONFLICT (nombre_normalizado, COALESCE(sector_gics, '')) DO UPDATE" in sql


def test_upsert_no_degrada_estado_y_fusiona_aliases():
    # El contrato de no-degradación y unión vive en el SQL (CASE + jsonb_agg).
    sess = _FakeSession()
    EntidadRepository(sess).upsert_entidad(
        EntidadRow(nombre="Nutresa", nombre_normalizado="nutresa", estado=ESTADO_VERIFICADO)
    )
    sql = sess.sqls[-1]
    assert "CASE WHEN" in sql and "'verificado'" in sql  # no baja de verificado
    assert "jsonb_agg(DISTINCT a" in sql  # unión de aliases


def test_upsert_incluye_sub_gics_sin_degradar():
    # DT-061: el sub_gics viaja en el INSERT y se conserva con COALESCE (no lo pisa un NULL).
    sess = _FakeSession()
    EntidadRepository(sess).upsert_entidad(
        EntidadRow(nombre="Colanta", nombre_normalizado="colanta",
                   sector_gics="3020", sub_gics="302020")
    )
    sql = sess.sqls[-1]
    assert "sub_gics = COALESCE(EXCLUDED.sub_gics" in sql
    assert sess.params[-1]["sub_gics"] == "302020"


def test_add_atributo_idempotente_por_clave_fuente():
    sess = _FakeSession()
    EntidadRepository(sess).add_atributo(
        42, "descripcion", "líder lácteo", "web", estado=ESTADO_CANDIDATO
    )
    sql = sess.sqls[-1]
    assert "ON CONFLICT (entidad_id, clave, fuente) DO UPDATE" in sql
    assert sess.params[-1]["fuente"] == "web"
    assert sess.params[-1]["estado"] == ESTADO_CANDIDATO


# --- Consulta de anclaje ---


def test_list_competidores_ordena_por_senal_y_excluye_descartado():
    sess = _FakeSession(select_rows=[("Alpina",), ("Colanta",), ("Nestlé",)])
    nombres = EntidadRepository(sess).list_competidores_by_sector("3020", limit=8)
    assert nombres == ["Alpina", "Colanta", "Nestlé"]
    sql = sess.sqls[-1]
    assert "estado <> :descartado" in sql
    assert "COALESCE(n_chunks, 0) DESC" in sql
    assert sess.params[-1]["limit"] == 8
    # Sin sub_gics resuelto → se pasa NULL (invariante DT-061: comportamiento de grupo).
    assert sess.params[-1]["sub"] is None


def test_list_competidores_con_sub_gics_prioriza_verificado_y_subsector():
    # DT-061: cuando la empresa analizada resuelve un sub-código, el orden lo prioriza.
    sess = _FakeSession(select_rows=[("Colanta",), ("Alquería",)])
    EntidadRepository(sess).list_competidores_by_sector("3020", sub_gics="302020")
    sql = sess.sqls[-1]
    assert "(estado = :verificado) DESC" in sql
    assert "(:sub IS NOT NULL AND sub_gics = :sub) DESC" in sql
    assert sess.params[-1]["sub"] == "302020"
    assert sess.params[-1]["verificado"] == ESTADO_VERIFICADO


def test_list_competidores_sector_vacio_no_consulta():
    sess = _FakeSession()
    assert EntidadRepository(sess).list_competidores_by_sector("") == []
    assert sess.sqls == []  # corto-circuito, sin tocar BD


def test_entidad_row_defaults():
    fila = EntidadRow(nombre="X Corp", nombre_normalizado="x")
    assert fila.tipo == "competidor" and fila.estado == ESTADO_CANDIDATO
    assert fila.aliases == []
    # Empresa principal (T4) entra como verificado por elección del use case, no por default.
    assert TIPO_EMPRESA == "empresa"
