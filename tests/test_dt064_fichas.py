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
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeSession:
    def __init__(self, row=None):
        self.sqls: list[str] = []
        self.params: list[dict] = []
        self._row = row

    def execute(self, sql, params=None):
        self.sqls.append(str(sql))
        self.params.append(params or {})
        return _FetchResult(self._row)


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
