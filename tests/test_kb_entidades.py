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
from ic.data.repositories.entidad_repo import (
    EntidadRepository,
    EntidadRow,
    _clave_exclusion,
)

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
    # DT-061b: alcance global/local añadido idempotente.
    assert "ADD COLUMN IF NOT EXISTS alcance TEXT" in unido


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
        if (
            s.startswith("SELECT nombre")
            or s.startswith("SELECT e.nombre")
            or s.startswith("SELECT id")
        ):
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
        EntidadRow(
            nombre="Alpina S.A.",
            nombre_normalizado="alpina",
            nit="860025900",
            sector_gics="3020",
            aliases=["Alpina", "ALPINA"],
        )
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
    # DT-050: índice nombre+sector PARCIAL (WHERE nit IS NULL) → el arbitro incluye el predicado.
    assert (
        "ON CONFLICT (nombre_normalizado, COALESCE(sector_gics, '')) WHERE nit IS NULL DO UPDATE"
        in sql
    )


def test_upsert_no_degrada_estado_y_fusiona_aliases():
    # El contrato de no-degradación y unión vive en el SQL (CASE + jsonb_agg).
    sess = _FakeSession()
    EntidadRepository(sess).upsert_entidad(
        EntidadRow(
            nombre="Nutresa", nombre_normalizado="nutresa", estado=ESTADO_VERIFICADO
        )
    )
    sql = sess.sqls[-1]
    assert "CASE WHEN" in sql and "'verificado'" in sql  # no baja de verificado
    assert "jsonb_agg(DISTINCT a" in sql  # unión de aliases


def test_upsert_incluye_sub_gics_sin_degradar():
    # DT-061: el sub_gics viaja en el INSERT y se conserva con COALESCE (no lo pisa un NULL).
    sess = _FakeSession()
    EntidadRepository(sess).upsert_entidad(
        EntidadRow(
            nombre="Colanta",
            nombre_normalizado="colanta",
            sector_gics="3020",
            sub_gics="302020",
        )
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


def _row(
    nombre, nombre_norm, estado, n_chunks, alcance=None, descriptor="", aliases=None
):
    """Tupla en el orden del SELECT del repo (DT-063/DT-UI04f):
    (nombre, norm, alcance, estado, n_chunks, productos_perfil, aliases)."""
    return (nombre, nombre_norm, alcance, estado, n_chunks, descriptor, aliases)


def _local_row(
    nombre, desc="", tam=0, ciudad=None, vertical=None, segmento=None, verificado=True
):
    """Tupla en el orden del SELECT de list_locales_by_sector:
    (nombre, ciudad, vertical, ingreso, segmento, verificado, tam, descripcion, prod_perfil).
    """
    return (nombre, ciudad, vertical, None, segmento, verificado, tam, None, desc)


def test_list_competidores_sin_productos_ordena_por_evidencia():
    # DT-063: sin productos → comportamiento de grupo (solo ruido excluido), orden por evidencia.
    sess = _FakeSession(
        select_rows=[
            _row("Colanta", "colanta", ESTADO_CANDIDATO, 5),
            _row("Alpina", "alpina", ESTADO_CANDIDATO, 9),
        ]
    )
    nombres = EntidadRepository(sess).list_competidores_by_sector("3020", limit=8)
    assert nombres == ["Alpina", "Colanta"]  # más chunks primero (tiebreak)
    sql = sess.sqls[-1]
    assert "estado <> :descartado" in sql
    assert "productos_perfil" in sql  # trae el descriptor para el solape puro


def test_list_competidores_filtra_por_solape_de_producto():
    # DT-063 end-to-end (repo → ranker puro): con productos lácteos, cae la bebida (sin solape) y el
    # medio (ruido); solo queda el de perfil de producto lácteo.
    sess = _FakeSession(
        select_rows=[
            _row(
                "Colanta",
                "colanta",
                ESTADO_VERIFICADO,
                4,
                descriptor="lácteos, leche, yogurt",
            ),
            _row(
                "Postobón SA",
                "postobon sa",
                ESTADO_CANDIDATO,
                20,
                descriptor="bebidas gaseosas",
            ),
            _row(
                "Beverage Industry News",
                "beverage industry news",
                ESTADO_CANDIDATO,
                8,
                descriptor="lácteos noticias",
            ),
        ]
    )
    nombres = EntidadRepository(sess).list_competidores_by_sector(
        "3020", productos_terms={"lacteos", "leche", "yogurt"}
    )
    assert nombres == [
        "Colanta"
    ]  # solape lácteo; bebida (sin solape) y medio (ruido) fuera


def test_list_competidores_alcance_global_excluye_locales():
    # DT-061b: la sección de clase mundial (alcance=global) deja fuera a los locales grandes.
    sess = _FakeSession(
        select_rows=[
            _row(
                "Nestlé",
                "nestlé",
                ESTADO_VERIFICADO,
                3,
                alcance="global",
                descriptor="lácteos yogurt",
            ),
            _row(
                "Colanta",
                "colanta",
                ESTADO_VERIFICADO,
                9,
                alcance="local",
                descriptor="lácteos leche",
            ),
        ]
    )
    nombres = EntidadRepository(sess).list_competidores_by_sector(
        "3020", productos_terms={"lacteos"}, alcance="global"
    )
    assert nombres == ["Nestlé"]  # Colanta (local) no entra al componente global


def test_list_competidores_excluye_empresa_analizada():
    # DT-UI04a: la empresa analizada no aparece en su propia lista de competidores. El match es
    # robusto a sufijos societarios y acentos ("ERCO ENERGÍA S.A.S." ≡ "ERCO ENERGIA").
    sess = _FakeSession(
        select_rows=[
            _row(
                "ERCO ENERGIA",
                "erco energia",
                ESTADO_VERIFICADO,
                5,
                alcance="global",
                descriptor="energía solar fotovoltaica",
            ),
            _row(
                "Celsia",
                "celsia",
                ESTADO_VERIFICADO,
                8,
                alcance="global",
                descriptor="energía solar",
            ),
        ]
    )
    nombres = EntidadRepository(sess).list_competidores_by_sector(
        "3510",
        productos_terms={"energia", "solar"},
        exclude_nombre="ERCO ENERGÍA S.A.S.",
    )
    assert "ERCO ENERGIA" not in nombres
    assert nombres == ["Celsia"]


def test_list_locales_excluye_empresa_analizada():
    # DT-UI04a: mismo para el tier local (2.1.2/2.1.3). Fila local = orden del SELECT del repo.
    sess = _FakeSession(
        select_rows=[
            _local_row("ERCO ENERGIA", desc="energía solar", tam=900),
            _local_row("Ecoflux", desc="energía solar", tam=300),
        ]
    )
    locales = EntidadRepository(sess).list_locales_by_sector(
        "3510",
        productos_terms={"energia", "solar"},
        exclude_nombre="ERCO ENERGÍA S.A.S.",
    )
    nombres = [r.nombre for r in locales]
    assert "ERCO ENERGIA" not in nombres
    assert nombres == ["Ecoflux"]


def test_list_locales_multisector_usa_any_y_pasa_lista():
    # DT-UI04b: con varios sectores el JOIN usa ANY(:sectores) y recibe la lista (grupo del LLM +
    # grupo canónico del CIIU); así una eléctrica en 1010 alcanza a sus pares curados en 5510.
    sess = _FakeSession(
        select_rows=[_local_row("Celsia", desc="energía solar", tam=800)]
    )
    locales = EntidadRepository(sess).list_locales_by_sector(
        ["1010", "5510"], productos_terms={"energia", "solar"}
    )
    assert [r.nombre for r in locales] == ["Celsia"]
    sql = sess.sqls[-1]
    assert "es.sector_gics = ANY(:sectores)" in sql
    assert sess.params[-1]["sectores"] == ["1010", "5510"]
    # Prefetch escala con el nº de sectores (que un sector grande no desplace al otro del window).
    assert sess.params[-1]["prefetch"] == 60 * 2


def test_list_locales_acepta_str_una_lista():
    # Backward-compat: un str se normaliza a lista de un elemento (comportamiento previo intacto).
    sess = _FakeSession(select_rows=[_local_row("Colanta", desc="lácteos", tam=500)])
    locales = EntidadRepository(sess).list_locales_by_sector(
        "3020", productos_terms={"lacteos"}
    )
    assert [r.nombre for r in locales] == ["Colanta"]
    assert sess.params[-1]["sectores"] == ["3020"]


def test_list_locales_deduplica_por_nombre_normalizado():
    # DT-UI04b: una entidad multi-sector (o duplicados cross-sector como "ERCO ENERGIA"×2) aparece
    # una sola vez; el match es robusto a sufijos societarios y acentos.
    sess = _FakeSession(
        select_rows=[
            _local_row("ERCO ENERGIA", desc="energía solar", tam=900),
            _local_row("Erco Energía S.A.S.", desc="energía solar", tam=800),
            _local_row("Celsia", desc="energía solar", tam=700),
        ]
    )
    locales = EntidadRepository(sess).list_locales_by_sector(
        ["1010", "5510"], productos_terms={"energia", "solar"}
    )
    nombres = [r.nombre for r in locales]
    # Las dos variantes de ERCO colapsan en una; Celsia queda. Sin claves normalizadas repetidas.
    claves = [_clave_exclusion(n) for n in nombres]
    assert len(claves) == len(set(claves))
    assert sum(1 for c in claves if c == _clave_exclusion("ERCO ENERGIA")) == 1
    assert "Celsia" in nombres


def test_list_locales_sectores_vacio_no_consulta():
    sess = _FakeSession()
    assert EntidadRepository(sess).list_locales_by_sector([]) == []
    assert EntidadRepository(sess).list_locales_by_sector("") == []
    assert sess.sqls == []  # corto-circuito, sin tocar BD


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


# --- DT-UI04f: multi-sector + exclusión por alias ---


def test_list_competidores_multisector_une_candidatos():
    # DT-UI04f: con dos sectores se retornan competidores de ambos, sin duplicados.
    sess = _FakeSession(
        select_rows=[
            _row(
                "Nestlé",
                "nestle",
                ESTADO_VERIFICADO,
                8,
                alcance="global",
                descriptor="lácteos leche yogurt",
            ),
            _row(
                "Danone",
                "danone",
                ESTADO_VERIFICADO,
                6,
                alcance="global",
                descriptor="lácteos yogurt",
            ),
        ]
    )
    nombres = EntidadRepository(sess).list_competidores_by_sector(
        ["1040", "1050"], productos_terms={"lacteos", "yogurt"}, alcance="global"
    )
    assert "Nestlé" in nombres
    assert "Danone" in nombres
    sql = sess.sqls[-1]
    assert "ANY(:sectores)" in sql
    assert sess.params[-1]["sectores"] == ["1040", "1050"]


def test_list_competidores_multisector_sector_vacio_no_consulta():
    # DT-UI04f: lista vacía (o str vacío) → retorna [] sin tocar BD.
    sess = _FakeSession()
    assert EntidadRepository(sess).list_competidores_by_sector([]) == []
    assert EntidadRepository(sess).list_competidores_by_sector("") == []
    assert sess.sqls == []  # corto-circuito siempre


def test_list_competidores_excluye_por_alias():
    # DT-UI04f: empresa focal registrada con nombre distinto al de búsqueda; alias la identifica.
    sess = _FakeSession(
        select_rows=[
            _row(
                "Compañía de Galletas NOEL",
                "compania galletas noel",
                ESTADO_VERIFICADO,
                5,
                alcance="global",
                descriptor="galletas confitería",
                aliases=["NOEL SAS", "Noel"],
            ),
            _row(
                "Pozuelo",
                "pozuelo",
                ESTADO_VERIFICADO,
                4,
                alcance="global",
                descriptor="galletas confitería",
            ),
        ]
    )
    nombres = EntidadRepository(sess).list_competidores_by_sector(
        ["1040", "1050"],
        productos_terms={"galletas", "confiteria"},
        alcance="global",
        exclude_nombre="NOEL SAS",
    )
    assert "Compañía de Galletas NOEL" not in nombres
    assert "Pozuelo" in nombres
