"""DT-064 T3 — Parser puro de fichas de competidor + lookup de entidad para persistir.

Fast: el parser es puro (sin BD); el repo se prueba con una sesión falsa (contrato SQL + mapeo).
"""

from __future__ import annotations

from ic.data.repositories.entidad_repo import EntidadRepository
from ic.domain.kb.ficha_parser import (
    TIER_GLOBAL,
    TIER_REGIONAL,
    TIER_STARTUP,
    parse_fichas_competidores,
)
from ic.domain.kb.relevance import format_fichas_conocidas

# --------------------------------------------------------------------------- Parser puro

_VERTICAL = """
## 2.1. Jugadores Clave

### Referentes Globales

| Campo | Valor |
|-------|-------|
| Nombre + País | Nestlé — Suiza |
| Resumen estratégico | Líder mundial en alimentos y bebidas. |
| Portafolio clave | Galletas, snacks y confitería. |
| Propuesta de valor | Nutrición y calidad constante. |
| Canales y precios | Masivo, retail B2C. |
| Presencia geográfica | 189 países. |
| Mayor fortaleza | Escala industrial e I+D. |
| Factor innovador diferencial | Nutrición personalizada. |

### Referentes Regionales LatAm/Colombia

| Campo | Valor |
|-------|-------|
| Nombre + País | Colombina — Colombia |
| Portafolio clave | Confitería y galletas. |
| Presencia geográfica | Dato no disponible. |
"""


def test_parse_vertical_extrae_campos_y_tier():
    fichas = parse_fichas_competidores(_VERTICAL)
    assert len(fichas) == 2
    nestle = fichas[0]
    assert nestle.nombre == "Nestlé"
    assert nestle.tier == TIER_GLOBAL
    assert nestle.campos["pais_origen"] == "Suiza"
    assert nestle.campos["resumen_estrategico"].startswith("Líder mundial")
    assert nestle.campos["portafolio"].startswith("Galletas")
    assert nestle.campos["propuesta_valor"].startswith("Nutrición")
    assert nestle.campos["canales_precios"].startswith("Masivo")
    assert nestle.campos["presencia_geografica"] == "189 países."
    assert nestle.campos["mayor_fortaleza"].startswith("Escala")
    assert nestle.campos["factor_diferencial"].startswith("Nutrición personalizada")


def test_parse_ignora_dato_no_disponible_y_hereda_tier():
    fichas = parse_fichas_competidores(_VERTICAL)
    colombina = fichas[1]
    assert colombina.nombre == "Colombina"
    assert colombina.tier == TIER_REGIONAL
    assert colombina.campos["pais_origen"] == "Colombia"
    assert colombina.campos["portafolio"].startswith("Confitería")
    # "Dato no disponible" no se persiste como hecho (RN-001).
    assert "presencia_geografica" not in colombina.campos


_ANCHA = """
### Startups / FoodTech

| Empresa | País de Origen | Portafolio / Productos Clave | Factor Diferencial |
|---|---|---|---|
| NotCo | Chile | Sucedáneos plant-based. | IA para formular recetas. |
| Planet A Foods | Alemania | Chocolate libre de cacao. | Fermentación de precisión. |
"""


def test_parse_tabla_ancha_una_ficha_por_fila():
    fichas = parse_fichas_competidores(_ANCHA)
    assert [f.nombre for f in fichas] == ["NotCo", "Planet A Foods"]
    assert all(f.tier == TIER_STARTUP for f in fichas)
    assert fichas[0].campos["pais_origen"] == "Chile"
    assert fichas[0].campos["portafolio"].startswith("Sucedáneos")
    assert fichas[0].campos["factor_diferencial"].startswith("IA")


def test_parse_texto_sin_tablas_devuelve_vacio():
    assert parse_fichas_competidores("## 2.1\n\nTexto corrido sin fichas.") == []


# --------------------------------------------------------------------------- Repo: lookup


class _Row:
    def __init__(self, v):
        self._v = (v,)

    def __getitem__(self, i):
        return self._v[i]


class _FetchResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _FakeSession:
    def __init__(self, row=None, rows=None):
        self.sqls: list[str] = []
        self.params: list[dict] = []
        self._row = row
        self._rows = rows

    def execute(self, sql, params=None):
        self.sqls.append(str(sql))
        self.params.append(params or {})
        return _FetchResult(self._row, self._rows)


def test_get_id_con_sector_restringe_y_devuelve_id():
    sess = _FakeSession(row=_Row(7))
    eid = EntidadRepository(sess).get_id_by_nombre_sector("nestle", "3020")
    assert eid == 7
    sql = sess.sqls[-1]
    assert "nombre_normalizado = :norm" in sql
    assert "sector_gics = :sector" in sql  # restringe por sector
    assert sess.params[-1]["sector"] == "3020"


def test_get_id_sin_row_devuelve_none():
    sess = _FakeSession(row=None)
    assert EntidadRepository(sess).get_id_by_nombre_sector("inexistente", None) is None
    # Sin sector no se añade la condición.
    assert "sector_gics = :sector" not in sess.sqls[-1]


def test_get_id_nombre_vacio_no_consulta():
    sess = _FakeSession(row=_Row(1))
    assert EntidadRepository(sess).get_id_by_nombre_sector("", "3020") is None
    assert sess.sqls == []


# --------------------------------------------------------------------------- T4: pre-fill


def test_format_fichas_conocidas_vacio_es_noop():
    assert format_fichas_conocidas({}) == ""
    assert format_fichas_conocidas({"Nestlé": {}}) == ""  # sin campos → nada


def test_format_fichas_conocidas_lista_hechos():
    bloque = format_fichas_conocidas({
        "Nestlé": {"pais_origen": "Suiza", "portafolio": "Galletas."},
        "Danone": {"pais_origen": "Francia"},
    })
    assert "Nestlé" in bloque and "Danone" in bloque
    assert "pais_origen: Suiza" in bloque
    assert "no los contradigas" in bloque  # instrucción de uso


def test_list_ficha_atributos_mapea_filas_a_dict():
    # Filas (nombre, ciudad, clave, valor) — la forma que devuelve la query DT-065.
    rows = [
        ("Nestlé", None, "pais_origen", "Suiza"),
        ("Nestlé", None, "portafolio", "Galletas."),
        ("Danone", None, "pais_origen", "Francia"),
    ]
    sess = _FakeSession(rows=rows)
    fichas = EntidadRepository(sess).list_ficha_atributos_by_sector("3020", ["Nestlé", "Danone"])
    assert fichas["Nestlé"] == {"pais_origen": "Suiza", "portafolio": "Galletas."}
    assert fichas["Danone"] == {"pais_origen": "Francia"}
    # restringe por sector/nombres y consulta claves de ficha + alias de fuentes locales
    assert "clave = ANY(:claves)" in sess.sqls[-1]
    assert sess.params[-1]["sector"] == "3020"
    assert "descripcion" in sess.params[-1]["claves"]  # incluye alias (DT-065)


def test_list_ficha_atributos_alias_local_y_ciudad():
    # Entidad local (StartIA/EmpresasColombia): data bajo claves de fuente + columna ciudad.
    rows = [
        ("StartCo", "Medellín", "descripcion", "Plataforma SaaS de logística."),
        ("StartCo", "Medellín", "verticales", "LOGTECH"),
        ("StartCo", "Medellín", "tecnologias", "IA, cloud"),
    ]
    f = EntidadRepository(_FakeSession(rows=rows)).list_ficha_atributos_by_sector(
        "4510", ["StartCo"]
    )["StartCo"]
    assert f["resumen_estrategico"] == "Plataforma SaaS de logística."  # descripcion → resumen
    assert f["portafolio"] == "LOGTECH"  # verticales → portafolio
    assert f["factor_diferencial"] == "IA, cloud"  # tecnologias → factor_diferencial
    assert f["presencia_geografica"] == "Medellín"  # columna ciudad → presencia_geografica
    assert "pais_origen" not in f  # la columna región NO alimenta pais_origen


def test_list_ficha_atributos_native_gana_sobre_alias():
    # El ORDER BY del SQL entrega el nativo primero; el fake respeta ese orden → nativo gana.
    rows = [
        ("X", "Bogotá", "resumen_estrategico", "NATIVO"),  # native (clave de ficha)
        ("X", "Bogotá", "descripcion", "ALIAS"),  # alias → resumen_estrategico
        ("X", "Bogotá", "presencia_geografica", "Global"),  # native
    ]
    repo = EntidadRepository(_FakeSession(rows=rows))
    f = repo.list_ficha_atributos_by_sector("3020", ["X"])["X"]
    assert f["resumen_estrategico"] == "NATIVO"  # no lo pisa el alias
    assert f["presencia_geografica"] == "Global"  # native gana sobre columna ciudad


def test_list_ficha_atributos_sin_nombres_devuelve_vacio():
    sess = _FakeSession(rows=[])
    assert EntidadRepository(sess).list_ficha_atributos_by_sector("3020", []) == {}
    assert sess.sqls == []  # no consulta
