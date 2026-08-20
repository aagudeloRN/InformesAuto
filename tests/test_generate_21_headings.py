"""US1 — Verifica que los encabezados de los sub-módulos 2.1 tienen numeración jerárquica.

Tests mockeados (sin BD ni Ollama): cadenas y store falsos controlan el output mínimo.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from ic.domain.use_cases.generate_21_globales import Generate21Globales
from ic.domain.use_cases.generate_21_regionales import Generate21Regionales
from ic.domain.use_cases.generate_21_startups import Generate21Startups
from ic.shared.types import ChunkResult


class _FakeChain:
    def __init__(self, texto: str) -> None:
        self._texto = texto

    def invoke(self, _payload: dict[str, Any]) -> str:
        return self._texto


class _Hit:
    def __init__(self, n: int) -> None:
        self.chunk_id = f"c{n}"
        self.chunk_texto = f"texto {n}"
        self.fuente_tipo = "web"
        self.fuente_url = f"http://example.com/{n}"
        self.documento_id = None
        self.metadatos = {}
        self.score = 0.9


class _FakeStore:
    def __init__(self, n_chunks: int = 5) -> None:
        self._chunks = [_Hit(i) for i in range(n_chunks)]

    def search(self, *_args: Any, **_kwargs: Any) -> list[_Hit]:
        return self._chunks

    def ingest(self, *_args: Any, **_kwargs: Any) -> None:
        pass


class _FakeWeb:
    def search(self, *_args: Any, **_kwargs: Any) -> list[SimpleNamespace]:
        return [SimpleNamespace(content="contenido web", url="http://example.com", title="Empresa X")]


class _FakeEntidadRepo:
    def list_locales_by_sector(self, *_args: Any, **_kwargs: Any) -> list:
        return []


_EID = uuid.uuid4()


def test_globales_heading_tiene_numero() -> None:
    """Cap21Globales.texto debe empezar con '### 2.1.1. Referentes Globales'."""
    candidatos_texto = '["Nestlé", "Unilever", "Danone"]'
    perfil_texto = "### 2.1.1. Referentes Globales\n\nNestlé es líder mundial."

    uc = Generate21Globales(
        chain_candidatos=_FakeChain(candidatos_texto),
        chain_perfil=_FakeChain(perfil_texto),
        store=_FakeStore(),
        web_connector=_FakeWeb(),
    )
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea colombiana",
        sector_gics="Alimentos",
        sector_gics_code="3020",
        empresa_id=_EID,
    )

    assert result.retrieval_suficiente
    assert result.texto.startswith("### 2.1.1. Referentes Globales"), (
        f"Encabezado incorrecto: {result.texto[:60]!r}"
    )


def test_regionales_heading_tiene_numero() -> None:
    """Cap21Regionales.texto debe empezar con '### 2.1.2. Referentes Regionales LatAm/Colombia'."""
    perfil_texto = "### 2.1.2. Referentes Regionales LatAm/Colombia\n\nNutressa es líder regional."

    store = _FakeStore(n_chunks=5)
    for hit in store._chunks:
        hit.fuente_tipo = "emis"
        hit.metadatos = {"empresa": "Nutressa"}

    uc = Generate21Regionales(
        chain_perfil=_FakeChain(perfil_texto),
        store=store,
        web_connector=_FakeWeb(),
    )
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea colombiana",
        sector_gics="Alimentos",
        sector_gics_code="3020",
        empresa_id=_EID,
    )

    assert result.retrieval_suficiente
    assert result.texto.startswith("### 2.1.2. Referentes Regionales LatAm/Colombia"), (
        f"Encabezado incorrecto: {result.texto[:80]!r}"
    )


def test_startups_heading_tiene_numero() -> None:
    """Cap21Startups.texto debe empezar con '### 2.1.3. Startups y Disruptores del sector'."""
    perfil_texto = "### 2.1.3. Startups y Disruptores del sector\n\nStartup X innova."

    uc = Generate21Startups(
        chain_perfil=_FakeChain(perfil_texto),
        store=_FakeStore(),
        web_connector=_FakeWeb(),
        entidad_repo=_FakeEntidadRepo(),
    )
    result = uc.execute(
        nombre_empresa="Alpina",
        descripcion_empresa="Empresa láctea colombiana",
        sector_gics="Alimentos",
        sector_gics_code="3020",
        sectores_ancla=["3020"],
        empresa_id=_EID,
    )

    assert result.retrieval_suficiente
    assert result.texto.startswith("### 2.1.3. Startups y Disruptores del sector"), (
        f"Encabezado incorrecto: {result.texto[:80]!r}"
    )
