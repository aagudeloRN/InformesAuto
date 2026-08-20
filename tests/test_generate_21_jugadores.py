"""Tests UC-4 — Generate21Jugadores (orquestador).

Fast (sin DB ni red): inyecta stubs de gen_globales, gen_regionales, gen_startups.
4 casos del quickstart.md Escenario 4.
"""

from __future__ import annotations

from ic.domain.use_cases.generate_21_jugadores import Generate21Jugadores
from ic.shared.types import Cap21Globales, Cap21Jugadores, Cap21Regionales, Cap21Startups, ChunkResult


def _chunk() -> ChunkResult:
    return ChunkResult(chunk_texto="ctx", fuente_tipo="web", fuente_url="http://x", score=0.8)


def _globales(texto: str = "### Referentes Globales\n\nNestlé, Danone.") -> Cap21Globales:
    return Cap21Globales(
        texto=texto,
        candidatos=["Nestlé", "Danone"],
        n_candidatos_con_web=2,
        retrieval_suficiente=True,
        chunks_usados=[_chunk()],
    )


def _regionales(texto: str = "### Referentes Regionales LatAm/Colombia\n\nNutresa.") -> Cap21Regionales:
    return Cap21Regionales(
        texto=texto,
        empresas_emis=["Nutresa"],
        n_con_emis=1,
        retrieval_suficiente=True,
        chunks_usados=[_chunk()],
    )


def _startups(texto: str = "### Startups y Disruptores del sector\n\nStartupCo.") -> Cap21Startups:
    return Cap21Startups(
        texto=texto,
        locales=["StartupCo"],
        internacionales=[],
        retrieval_suficiente=True,
        chunks_usados=[],
    )


def _ausente_globales() -> Cap21Globales:
    return Cap21Globales(
        texto="Dato no disponible",
        candidatos=[],
        n_candidatos_con_web=0,
        retrieval_suficiente=False,
    )


def _ausente_regionales() -> Cap21Regionales:
    return Cap21Regionales(
        texto="Dato no disponible",
        empresas_emis=[],
        n_con_emis=0,
        retrieval_suficiente=False,
    )


def _ausente_startups() -> Cap21Startups:
    return Cap21Startups(
        texto="Dato no disponible",
        locales=[],
        internacionales=[],
        retrieval_suficiente=False,
    )


class _FakeSubModule:
    def __init__(self, result):
        self._result = result
        self.called = False

    def execute(self, **kwargs):
        self.called = True
        return self._result


def _make_orchestrator(
    globales_result=None,
    regionales_result=None,
    startups_result=None,
):
    glo = _FakeSubModule(globales_result or _globales())
    reg = _FakeSubModule(regionales_result or _regionales())
    sta = _FakeSubModule(startups_result or _startups())
    orch = Generate21Jugadores(gen_globales=glo, gen_regionales=reg, gen_startups=sta)
    return orch, glo, reg, sta


_EXECUTE_KWARGS = dict(
    nombre_empresa="Alpina",
    descripcion_empresa="Empresa láctea colombiana",
    sector_gics="3020",
    sector_gics_code="3020",
    sectores_ancla=["3020"],
    empresa_id=None,
    productos="Leche, yogurt",
)


def test_ensambla_tres_subsecciones_en_orden():
    orch, _, _, _ = _make_orchestrator()
    result = orch.execute(**_EXECUTE_KWARGS)
    assert isinstance(result, Cap21Jugadores)
    assert result.texto.startswith("## 2.1. Jugadores Clave")
    # Los tres bloques deben estar presentes y en orden
    pos_global = result.texto.find("### Referentes Globales")
    pos_regional = result.texto.find("### Referentes Regionales")
    pos_startup = result.texto.find("### Startups y Disruptores")
    assert pos_global < pos_regional < pos_startup
    assert result.retrieval_suficiente is True


def test_deduplicacion_cross_tier():
    # Nestlé aparece en globales Y en regionales → debe eliminarse de regionales
    glo = _globales()  # candidatos: ["Nestlé", "Danone"]
    reg_texto = "### Referentes Regionales LatAm/Colombia\n\nNestlé y Nutresa."
    reg = Cap21Regionales(
        texto=reg_texto,
        empresas_emis=["Nestlé", "Nutresa"],
        n_con_emis=2,
        retrieval_suficiente=True,
        chunks_usados=[],
    )
    orch, _, _, _ = _make_orchestrator(globales_result=glo, regionales_result=reg)
    result = orch.execute(**_EXECUTE_KWARGS)
    # Nutresa (solo en regionales) debe estar; el orquestador deduplica
    assert result.globales is not None
    assert result.regionales is not None
    # regionales.empresas_emis después de dedup: "Nestlé" eliminado
    assert "Nestlé" not in result.regionales.empresas_emis


def test_resume_desde_checkpoint_parcial():
    # Con globales ya calculados, el sub-módulo globales NO debe llamarse de nuevo
    orch, glo_stub, reg_stub, sta_stub = _make_orchestrator()
    cached_globales = _globales()
    result = orch.execute(cached_globales=cached_globales, **_EXECUTE_KWARGS)
    assert result.globales is cached_globales
    assert not glo_stub.called
    assert reg_stub.called
    assert sta_stub.called


def test_ausencia_total_si_todos_fallan():
    orch, _, _, _ = _make_orchestrator(
        globales_result=_ausente_globales(),
        regionales_result=_ausente_regionales(),
        startups_result=_ausente_startups(),
    )
    result = orch.execute(**_EXECUTE_KWARGS)
    assert result.retrieval_suficiente is False
    # Sin los tres sub-encabezados ###
    assert "### Referentes Globales" not in result.texto
    assert "Dato no disponible" in result.texto or "## 2.1." in result.texto


def test_subseccion_ausente_excluida_del_texto_ensamblado():
    """FR-006 / US1/AC2: sub-módulo con retrieval_suficiente=False no produce sub-encabezado."""
    # Caso A: Regionales ausentes — 2.1.2 no debe aparecer; 2.1.1 y 2.1.3 sí
    orch_a, _, _, _ = _make_orchestrator(
        globales_result=_globales("### 2.1.1. Referentes Globales\n\nNestlé."),
        regionales_result=_ausente_regionales(),
        startups_result=_startups("### 2.1.3. Startups y Disruptores del sector\n\nStartupCo."),
    )
    res_a = orch_a.execute(**_EXECUTE_KWARGS)
    assert res_a.retrieval_suficiente is True
    assert "### 2.1.1. Referentes Globales" in res_a.texto
    assert "### 2.1.2." not in res_a.texto, "Heading ausente no debe aparecer"
    assert "### 2.1.3. Startups y Disruptores del sector" in res_a.texto

    # Caso B: Startups ausentes — 2.1.3 no debe aparecer; 2.1.1 y 2.1.2 sí
    orch_b, _, _, _ = _make_orchestrator(
        globales_result=_globales("### 2.1.1. Referentes Globales\n\nNestlé."),
        regionales_result=_regionales("### 2.1.2. Referentes Regionales LatAm/Colombia\n\nNutresa."),
        startups_result=_ausente_startups(),
    )
    res_b = orch_b.execute(**_EXECUTE_KWARGS)
    assert res_b.retrieval_suficiente is True
    assert "### 2.1.1. Referentes Globales" in res_b.texto
    assert "### 2.1.2. Referentes Regionales LatAm/Colombia" in res_b.texto
    assert "### 2.1.3." not in res_b.texto, "Heading ausente no debe aparecer"
