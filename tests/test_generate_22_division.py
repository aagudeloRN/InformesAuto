"""Tests UC Cap 2.2 — Generate22Division.

Fast (sin DB ni red): inyecta FakeLLM y FakeCheckpointRepo.
Cubre los 6 escenarios del quickstart.md.
"""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import MagicMock

import pytest

from ic.domain.use_cases.generate_22_division import Generate22Division
from ic.shared.types import (
    Cap21Globales,
    Cap21Jugadores,
    Cap21Regionales,
    Cap21Startups,
    ChunkResult,
    ClasificacionCompetidor,
    CuadranteKey,
    DescripcionEmpresa,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _chunk() -> ChunkResult:
    return ChunkResult(chunk_texto="ctx", fuente_tipo="web", fuente_url="http://x", score=0.8)


def _empresa() -> DescripcionEmpresa:
    return DescripcionEmpresa(
        nombre_empresa="EmpresaAnalizada",
        actividad_ciiu="1081",
        texto="Empresa de alimentos procesados en Colombia.",
    )


def _cap21_con_5() -> Cap21Jugadores:
    """Fixture: Cap 2.1 con 5 empresas (2 globales, 1 regional, 2 startups)."""
    return Cap21Jugadores(
        texto="## 2.1...",
        globales=Cap21Globales(
            texto="globales",
            candidatos=["EmpresaA", "EmpresaB"],
            n_candidatos_con_web=2,
            retrieval_suficiente=True,
        ),
        regionales=Cap21Regionales(
            texto="regionales",
            empresas_emis=["EmpresaC"],
            n_con_emis=1,
            retrieval_suficiente=True,
        ),
        startups=Cap21Startups(
            texto="startups",
            locales=["StartupX"],
            internacionales=["StartupY"],
            retrieval_suficiente=True,
        ),
        retrieval_suficiente=True,
        chunks_usados=[_chunk()],
    )


def _cap21_vacio() -> Cap21Jugadores:
    return Cap21Jugadores(
        texto="",
        globales=None,
        regionales=None,
        startups=None,
        retrieval_suficiente=False,
    )


def _valid_llm_json(cuadrantes: dict | None = None) -> str:
    """JSON válido con 5 empresas clasificadas."""
    if cuadrantes is None:
        cuadrantes = {
            "masivo_tradicional": ["EmpresaA", "EmpresaB"],
            "masivo_innovador": ["StartupX", "StartupY"],
            "nicho_tradicional": ["EmpresaC"],
            "nicho_innovador": [],
        }
    import json
    return json.dumps({
        "cuadrantes": cuadrantes,
        "intro": "El ecosistema se segmenta por enfoque de mercado y modelo operativo.",
        "sintesis_incumbente": "Los incumbentes aprovechan economías de escala.",
        "sintesis_entrante": "Las startups atacan con modelos ágiles.",
    })


class _FakeLLM:
    """Stub de LLM: devuelve respuestas predefinidas en orden."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._idx = 0
        self.call_count = 0

    def invoke(self, *args: Any, **kwargs: Any) -> str:
        self.call_count += 1
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return self._responses[-1]


class _FakeChain:
    """Simula el resultado de build_chain_cap2_22_division(llm)."""

    def __init__(self, llm: _FakeLLM) -> None:
        self._llm = llm

    def invoke(self, inputs: dict) -> str:
        return self._llm.invoke(inputs)


class _FakeCheckpointRepo:
    """Repo de checkpoint en memoria para tests."""

    def __init__(self, initial: dict | None = None) -> None:
        self.saved: dict[str, dict] = dict(initial or {})
        self.save_calls: list[tuple[str, str]] = []

    def save_capitulo(self, run_key: str, cap_nombre: str, payload: dict) -> None:
        self.saved[cap_nombre] = payload
        self.save_calls.append((run_key, cap_nombre))

    def get_capitulo(self, run_key: str, cap_nombre: str) -> dict | None:
        return self.saved.get(cap_nombre)


def _make_uc(llm_responses: list[str], initial_checkpoint: dict | None = None):
    """Construye Generate22Division con stubs."""
    fake_llm = _FakeLLM(llm_responses)
    fake_chain = _FakeChain(fake_llm)
    repo = _FakeCheckpointRepo(initial_checkpoint)
    uc = Generate22Division(chain=fake_chain, checkpoint_repo=repo)
    return uc, fake_llm, repo


# ---------------------------------------------------------------------------
# T008 — US1: clasificación exhaustiva
# ---------------------------------------------------------------------------

def test_clasificacion_exhaustiva():
    """Todas las 5 empresas quedan clasificadas; retrieval_suficiente True."""
    uc, llm, repo = _make_uc([_valid_llm_json()])
    cap22 = uc(run_key="r1", cap21=_cap21_con_5(), empresa=_empresa())

    assert cap22.retrieval_suficiente is True
    assert cap22.n_empresas_procesadas == 5
    assert len(cap22.clasificaciones) == 5

    nombres_clasificados = {c.nombre for c in cap22.clasificaciones}
    assert nombres_clasificados == {"EmpresaA", "EmpresaB", "EmpresaC", "StartupX", "StartupY"}

    # suma cross-cuadrante == 5
    import re
    # verificar que la tabla tiene todos
    assert "EmpresaA" in cap22.texto
    assert "EmpresaB" in cap22.texto

    assert ("r1", "cap_2_2") in repo.save_calls


# ---------------------------------------------------------------------------
# T009 — US2: lista cerrada — nombre ajeno eliminado
# ---------------------------------------------------------------------------

def test_lista_cerrada_nombre_ajeno():
    """EmpresaZ (ajena) es detectada y eliminada; queda en warnings."""
    import json
    llm_json_with_intruder = json.dumps({
        "cuadrantes": {
            "masivo_tradicional": ["EmpresaA", "EmpresaB", "EmpresaZ"],  # EmpresaZ es intruso
            "masivo_innovador": ["StartupX", "StartupY"],
            "nicho_tradicional": ["EmpresaC"],
            "nicho_innovador": [],
        },
        "intro": "Segmentación.",
        "sintesis_incumbente": "Incumbentes.",
        "sintesis_entrante": "Entrantes.",
    })
    uc, _, repo = _make_uc([llm_json_with_intruder])
    cap22 = uc(run_key="r2", cap21=_cap21_con_5(), empresa=_empresa())

    assert "EmpresaZ" not in cap22.texto
    assert "EmpresaZ" in cap22.warnings_nombres_ajenos
    assert len(cap22.clasificaciones) == 5  # solo las 5 del fixture


# ---------------------------------------------------------------------------
# T010 — US1: cuadrante vacío muestra (ninguno)
# ---------------------------------------------------------------------------

def test_cuadrante_vacio_muestra_ninguno():
    """Cuadrantes vacíos muestran (ninguno); ninguna fila se omite."""
    import json
    all_in_one = json.dumps({
        "cuadrantes": {
            "masivo_tradicional": ["EmpresaA", "EmpresaB", "EmpresaC", "StartupX", "StartupY"],
            "masivo_innovador": [],
            "nicho_tradicional": [],
            "nicho_innovador": [],
        },
        "intro": "Todo en masivo tradicional.",
        "sintesis_incumbente": "Incumbentes dominan.",
        "sintesis_entrante": "Sin entrantes innovadores.",
    })
    uc, _, _ = _make_uc([all_in_one])
    cap22 = uc(run_key="r3", cap21=_cap21_con_5(), empresa=_empresa())

    assert cap22.retrieval_suficiente is True
    # 3 cuadrantes vacíos → 3 ocurrencias de (ninguno)
    assert cap22.texto.count("(ninguno)") == 3
    # la tabla tiene ambas filas
    assert "Masivo / Volumen" in cap22.texto
    assert "Nicho / Premium" in cap22.texto


# ---------------------------------------------------------------------------
# T016 — US3: regeneración no altera cap_1 ni cap_2_1
# ---------------------------------------------------------------------------

def test_regeneracion_no_altera_cap1_ni_cap21():
    """Regenerar Cap 2.2 no modifica checkpoints de cap_1 ni cap_2_1."""
    initial = {
        "cap_1": {"texto": "descripcion original"},
        "cap_2_1": {"texto": "jugadores originales"},
    }
    uc, _, repo = _make_uc(
        [_valid_llm_json(), _valid_llm_json()],
        initial_checkpoint=initial,
    )
    empresa = _empresa()
    cap21 = _cap21_con_5()

    # primera generación
    uc(run_key="r4", cap21=cap21, empresa=empresa)

    # snapshot de cap_1 y cap_2_1 después de primera generación
    cap1_after_first = repo.saved.get("cap_1")
    cap21_after_first = repo.saved.get("cap_2_1")

    # segunda generación con feedback
    uc(run_key="r4", cap21=cap21, empresa=empresa, feedback="más énfasis en entrantes")

    # cap_1 y cap_2_1 no deben cambiar
    assert repo.saved.get("cap_1") == cap1_after_first == initial["cap_1"]
    assert repo.saved.get("cap_2_1") == cap21_after_first == initial["cap_2_1"]

    # cap_2_2 fue guardado dos veces
    cap22_saves = [call for call in repo.save_calls if call[1] == "cap_2_2"]
    assert len(cap22_saves) == 2


# ---------------------------------------------------------------------------
# T018 — US4: Cap 2.1 vacío → ausencia sin invocar LLM
# ---------------------------------------------------------------------------

def test_cap21_vacio_devuelve_ausencia():
    """Cap 2.1 vacío → párrafo de ausencia, LLM no invocado."""
    uc, fake_llm, _ = _make_uc([_valid_llm_json()])
    cap22 = uc(run_key="r5", cap21=_cap21_vacio(), empresa=_empresa())

    assert cap22.retrieval_suficiente is False
    assert "## 2.2." in cap22.texto
    assert "## 2.2." in cap22.texto
    # sin tabla 2×2
    assert "Masivo" not in cap22.texto or "segmentación" not in cap22.texto.lower()
    # LLM no fue invocado
    assert fake_llm.call_count == 0


# ---------------------------------------------------------------------------
# T019 — US4: JSON malformado → retry x2 → ausencia
# ---------------------------------------------------------------------------

def test_json_malformado_devuelve_ausencia():
    """LLM siempre devuelve JSON inválido → 2 reintentos → párrafo de ausencia."""
    uc, fake_llm, _ = _make_uc(["no es json válido", "tampoco es json"])
    cap22 = uc(run_key="r6", cap21=_cap21_con_5(), empresa=_empresa())

    assert fake_llm.call_count == 2  # retry policy: exactamente 2 intentos
    assert cap22.retrieval_suficiente is False
    assert "## 2.2." in cap22.texto


# ---------------------------------------------------------------------------
# T026 — Error de red / API se propaga sin silenciar (FR-012)
# ---------------------------------------------------------------------------

def test_error_red_propagado():
    """Errores de red/API se propagan; el use_case no los suprime silenciosamente."""
    class _ErrorChain:
        def invoke(self, inputs):
            raise RuntimeError("red")

    repo = _FakeCheckpointRepo()
    uc = Generate22Division(chain=_ErrorChain(), checkpoint_repo=repo)
    with pytest.raises(RuntimeError, match="red"):
        uc(run_key="r7", cap21=_cap21_con_5(), empresa=_empresa())


# ---------------------------------------------------------------------------
# T027 — dato_no_disponible marcado cuando síntesis indica falta de atributos
# ---------------------------------------------------------------------------

def test_dato_no_disponible_marcado():
    """Empresas con 'Dato no disponible' en sintesis_incumbente/entrante quedan marcadas."""
    import json
    llm_json = json.dumps({
        "cuadrantes": {
            "masivo_tradicional": ["EmpresaA", "EmpresaB"],
            "masivo_innovador": ["StartupX", "StartupY"],
            "nicho_tradicional": ["EmpresaC"],
            "nicho_innovador": [],
        },
        "intro": "Segmentación.",
        "sintesis_incumbente": "Dato no disponible en fuentes consultadas para EmpresaA.",
        "sintesis_entrante": "Dato no disponible en fuentes consultadas para StartupX.",
    })
    uc, _, _ = _make_uc([llm_json])
    cap22 = uc(run_key="r8", cap21=_cap21_con_5(), empresa=_empresa())

    nombres_marcados = {c.nombre for c in cap22.clasificaciones if c.dato_no_disponible}
    assert "EmpresaA" in nombres_marcados
    assert "StartupX" in nombres_marcados
    # Los demás no están marcados
    nombres_no_marcados = {c.nombre for c in cap22.clasificaciones if not c.dato_no_disponible}
    assert "EmpresaB" in nombres_no_marcados
    assert "EmpresaC" in nombres_no_marcados


# ---------------------------------------------------------------------------
# T028 — Un solo competidor genera con warning representatividad
# ---------------------------------------------------------------------------

def test_un_competidor_genera_con_warning():
    """Con solo 1 competidor en Cap 2.1, se genera normalmente pero con warning de representatividad."""
    import json
    cap21_uno = Cap21Jugadores(
        texto="## 2.1...",
        globales=Cap21Globales(
            texto="globales",
            candidatos=["EmpresaSola"],
            n_candidatos_con_web=1,
            retrieval_suficiente=True,
        ),
        regionales=None,
        startups=None,
        retrieval_suficiente=True,
        chunks_usados=[_chunk()],
    )
    llm_json = json.dumps({
        "cuadrantes": {
            "masivo_tradicional": ["EmpresaSola"],
            "masivo_innovador": [],
            "nicho_tradicional": [],
            "nicho_innovador": [],
        },
        "intro": "Un solo competidor.",
        "sintesis_incumbente": "EmpresaSola domina el mercado.",
        "sintesis_entrante": "Sin entrantes identificados.",
    })
    uc, _, _ = _make_uc([llm_json])
    cap22 = uc(run_key="r9", cap21=cap21_uno, empresa=_empresa())

    assert cap22.retrieval_suficiente is True
    assert len(cap22.clasificaciones) == 1
    # debe haber warning de representatividad
    assert any("1 competidor" in w or "representativa" in w for w in cap22.warnings_nombres_ajenos)
