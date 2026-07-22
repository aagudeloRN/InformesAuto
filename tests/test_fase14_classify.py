"""Tests Fase 14 — ClassifyGICS con acotado/validación por CIIU (fast, mocked)."""

from unittest.mock import MagicMock

from ic.domain.use_cases.classify_gics import ClassifyGICS


def _uc(respuesta: str):
    chain = MagicMock()
    chain.invoke.return_value = respuesta
    return ClassifyGICS(chain), chain


def test_sin_ciiu_no_inyecta_pistas_ni_corrige():
    uc, chain = _uc("Grupo Industrial: Bancos (GICS 4010)\nJustificación: banca.")
    res = uc.execute("Banco X", "Un banco.")
    assert chain.invoke.call_args.args[0]["pistas"] == ""
    assert res.grupo_gics == "Bancos (GICS 4010)"


def test_con_ciiu_inyecta_pistas():
    uc, chain = _uc("Grupo Industrial: Servicios comerciales y profesionales (GICS 2020)\nJ: x")
    uc.execute("Comfama", "Caja de compensación.", ciiu="8430")
    pistas = chain.invoke.call_args.args[0]["pistas"]
    assert "GICS 2020" in pistas  # candidato del CIIU 8430 (Sección O)


def test_codigo_explicito_dentro_de_candidatos_se_conserva():
    uc, _ = _uc("Grupo Industrial: Servicios comerciales y profesionales (GICS 2020)\nJ: x")
    res = uc.execute("Comfama", "Caja de compensación.", ciiu="8430")
    assert res.grupo_gics == "Servicios comerciales y profesionales (GICS 2020)"


def test_codigo_explicito_fuera_de_candidatos_se_respeta():
    # El LLM emite código explícito fuera de los candidatos → se respeta (solo se registra).
    uc, _ = _uc("Grupo Industrial: Bancos (GICS 4010)\nJustificación: x")
    res = uc.execute("Empresa rara", "desc", ciiu="8430")  # candidato = 2020
    assert res.grupo_gics == "Bancos (GICS 4010)"


def test_sin_codigo_explicito_fuera_de_candidatos_se_corrige():
    # Sin "(GICS XXXX)": el fallback por nombre resuelve 'Bancos'→4010, fuera de candidatos.
    # Se corrige al primer candidato del CIIU (2020).
    uc, _ = _uc("Grupo Industrial: Bancos\nJustificación: x")
    res = uc.execute("Comfama", "Caja de compensación.", ciiu="8430")
    assert "(GICS 2020)" in res.grupo_gics
    assert "Servicios comerciales y profesionales" in res.grupo_gics


def test_ciiu_desconocido_no_corrige():
    # CIIU Sección U (sin correspondencia) → sin candidatos → no se toca la clasificación.
    uc, _ = _uc("Grupo Industrial: Bancos\nJustificación: x")
    res = uc.execute("Org", "desc", ciiu="9900")
    assert res.grupo_gics == "Bancos"
