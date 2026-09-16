"""US2/US3 — Verifica que generate_n1._fn_cap2 inyecta jugadores_use_case en GenerateBenchmarking.

Strategy:
- US2: inspección de fuente — verifica que el wiring code existe en generate_n1.py.
- US3: test de constructor — verifica que GenerateBenchmarking recibe engine y sub_gics
  correctamente cuando jugadores_use_case está inyectado, usando el test de integración
  directo de GenerateBenchmarking (complementa T042 de spec 002).
"""

from __future__ import annotations

import pathlib
from typing import Any
from unittest.mock import patch

from ic.shared.types import Cap21Globales, Cap21Jugadores, Cap21Regionales, Cap21Startups

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SRC = pathlib.Path("src/ic/domain/use_cases/generate_n1.py").read_text()


def _cap21_suficiente() -> Cap21Jugadores:
    g = Cap21Globales(
        texto="### 2.1.1. Referentes Globales\n\nNestlé.",
        candidatos=["Nestlé"],
        n_candidatos_con_web=1,
        retrieval_suficiente=True,
    )
    r = Cap21Regionales(
        texto="### 2.1.2. Referentes Regionales LatAm/Colombia\n\nNutressa.",
        empresas_emis=["Nutressa"],
        n_con_emis=1,
        retrieval_suficiente=True,
    )
    s = Cap21Startups(
        texto="### 2.1.3. Startups y Disruptores del sector\n\nStartup X.",
        locales=[],
        internacionales=["Startup X"],
        retrieval_suficiente=True,
    )
    return Cap21Jugadores(
        texto="## 2.1. Jugadores Clave\n\n" + g.texto,
        globales=g,
        regionales=r,
        startups=s,
        retrieval_suficiente=True,
    )


class _FakeJugadoresUseCase:
    def __init__(self) -> None:
        self.called = False
        self.last_kwargs: dict[str, Any] = {}

    def execute(self, **kwargs: Any) -> Cap21Jugadores:
        self.called = True
        self.last_kwargs = kwargs
        return _cap21_suficiente()


# ---------------------------------------------------------------------------
# US2: Tests de wiring en generate_n1.py (source inspection)
# ---------------------------------------------------------------------------


def test_generate_n1_instancia_generate21_jugadores() -> None:
    """generate_n1.py debe instanciar Generate21Jugadores y asignarlo a jugadores_use_case."""
    assert "Generate21Jugadores(" in _SRC, "Generate21Jugadores no se instancia en generate_n1.py"
    assert "jugadores_use_case = Generate21Jugadores(" in _SRC, (
        "jugadores_use_case no está asignado en generate_n1.py"
    )


def test_generate_n1_pasa_jugadores_a_generate_benchmarking() -> None:
    """generate_n1.py debe pasar jugadores_use_case= al constructor de GenerateBenchmarking."""
    assert "jugadores_use_case=jugadores_use_case," in _SRC, (
        "jugadores_use_case= no aparece en la llamada a GenerateBenchmarking"
    )


def test_generate_n1_pasa_engine_a_generate_benchmarking() -> None:
    """generate_n1.py debe pasar engine=db_engine al constructor de GenerateBenchmarking (US3)."""
    assert "engine=db_engine," in _SRC, (
        "engine=db_engine no aparece en la llamada a GenerateBenchmarking"
    )


def test_generate_n1_pasa_sub_gics_a_generate_benchmarking() -> None:
    """generate_n1.py debe pasar sub_gics=g_code al constructor de GenerateBenchmarking (US3)."""
    assert "sub_gics=g_code," in _SRC, (
        "sub_gics=g_code no aparece en la llamada a GenerateBenchmarking"
    )


def test_generate_n1_importa_generate21_jugadores() -> None:
    """generate_n1.py debe tener import de Generate21Jugadores, Generate21Globales, etc."""
    assert "from ic.domain.use_cases.generate_21_jugadores import Generate21Jugadores" in _SRC
    assert "from ic.domain.use_cases.generate_21_globales import Generate21Globales" in _SRC
    assert "from ic.domain.use_cases.generate_21_regionales import Generate21Regionales" in _SRC
    assert "from ic.domain.use_cases.generate_21_startups import Generate21Startups" in _SRC


# ---------------------------------------------------------------------------
# US3: Test de cache sectorial en GenerateBenchmarking
# ---------------------------------------------------------------------------


def test_sector_cache_hit_pipeline_pasa_cached_al_jugadores() -> None:
    """US3: cuando _load_sector_cache retorna globales cacheados, jugadores_use_case.execute()
    recibe cached_globales no-None. Verifica la integración GenerateBenchmarking ↔ jugadores."""
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking

    cached_g = Cap21Globales(
        texto="### 2.1.1. Referentes Globales\n\nNestlé (cache).",
        candidatos=["Nestlé"],
        n_candidatos_con_web=1,
        retrieval_suficiente=True,
    )
    jugadores = _FakeJugadoresUseCase()

    class _FakeChain:
        def invoke(self, _: Any) -> str:
            return "## 2. Análisis Competitivo\n\nContenido."

    class _FakeChunk:
        chunk_id = "c1"
        chunk_texto = "Nestlé es líder global de alimentos procesados."
        fuente_tipo = "web"
        fuente_url = "http://example.com"
        documento_id = None
        metadatos: dict = {}
        score = 0.9

    class _FakeStore:
        # GenerateBenchmarking necesita ≥ _MIN_CHUNKS=5 para no retornar ausente
        def search(self, *_: Any, **__: Any) -> list:
            return [_FakeChunk()] * 6

        def ingest(self, *_: Any, **__: Any) -> None:
            pass

    class _FakeWebConnector:
        def search(self, *_: Any, **__: Any) -> list:
            return []

    uc = GenerateBenchmarking(
        chain=_FakeChain(),
        store=_FakeStore(),
        web_connector=_FakeWebConnector(),
        jugadores_use_case=jugadores,
        engine=object(),
        sub_gics="3020",
    )

    with patch(
        "ic.domain.use_cases.generate_benchmarking._load_sector_cache",
        return_value=(cached_g, None, None),
    ):
        uc.execute(
            nombre_empresa="Alpina",
            descripcion_empresa="Empresa láctea colombiana",
            sector_gics="Alimentos",
            sector_gics_code="3020",
            empresa_id=None,
        )

    assert jugadores.called, "jugadores_use_case.execute() no fue invocado"
    assert jugadores.last_kwargs.get("cached_globales") is cached_g, (
        "cached_globales no llegó a jugadores_use_case.execute()"
    )
