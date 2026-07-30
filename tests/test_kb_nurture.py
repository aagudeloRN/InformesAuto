"""DT-056/T4 — base viva: cada corrida nutre el KB con la empresa principal.

Fast (repo fake): la empresa entra como entidad `verificado` (identidad pedida por el usuario) y
su descripción como atributo `candidato` con procedencia (gate RN-001). Idempotente.
"""

from __future__ import annotations

from ic.data.models.entidad import (
    ESTADO_CANDIDATO,
    ESTADO_VERIFICADO,
    FUENTE_WEB,
    TIPO_EMPRESA,
)
from ic.domain.use_cases.nurture_kb import NurtureKB


class _RepoFake:
    def __init__(self):
        self.entidades: list = []
        self.atributos: list = []
        self._next_id = 1

    def upsert_entidad(self, fila):
        # Idempotente: dedup por (nombre_normalizado, sector).
        for eid, f in self.entidades:
            if (f.nombre_normalizado, f.sector_gics) == (fila.nombre_normalizado, fila.sector_gics):
                return eid
        eid = self._next_id
        self._next_id += 1
        self.entidades.append((eid, fila))
        return eid

    def add_atributo(self, entidad_id, clave, valor, fuente, **kw):
        self.atributos.append((entidad_id, clave, valor, fuente, kw.get("estado")))


def test_nutre_empresa_verificada_y_descripcion_candidata():
    repo = _RepoFake()
    eid = NurtureKB(repo).execute(
        nombre="Alpina", sector_gics="3020", descripcion="Empresa láctea líder en Colombia."
    )
    assert eid == 1
    (_, fila) = repo.entidades[0]
    assert fila.tipo == TIPO_EMPRESA
    assert fila.estado == ESTADO_VERIFICADO  # identidad = sujeto pedido por el usuario
    assert fila.sector_gics == "3020"
    assert "Alpina" in fila.aliases
    # La descripción (web/LLM) es candidato con procedencia — nunca hecho verificado.
    (_, clave, _, fuente, estado) = repo.atributos[0]
    assert clave == "descripcion" and fuente == FUENTE_WEB and estado == ESTADO_CANDIDATO


def test_idempotente_en_segunda_corrida():
    repo = _RepoFake()
    uc = NurtureKB(repo)
    id1 = uc.execute(nombre="Alpina", sector_gics="3020", descripcion="x")
    id2 = uc.execute(nombre="Alpina", sector_gics="3020", descripcion="x")
    assert id1 == id2  # upsert, no duplica la entidad
    assert len(repo.entidades) == 1


def test_nombre_vacio_no_fabrica_entidad():
    repo = _RepoFake()
    assert NurtureKB(repo).execute(nombre="  ", sector_gics="3020") is None
    assert repo.entidades == []


def test_sin_descripcion_no_agrega_atributo():
    repo = _RepoFake()
    NurtureKB(repo).execute(nombre="Colanta", sector_gics="3020", descripcion=None)
    assert repo.atributos == []
