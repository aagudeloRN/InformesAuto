"""DT-064 T5 — Detector de negativas del LLM + retry + escalada a tier de API superior.

Fast: el detector es puro; la escalada se prueba con cadenas mockeadas (sin LLM real).
"""

from __future__ import annotations

from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
from ic.shared.text_utils import is_llm_refusal
from ic.shared.types import ChunkResult

# --------------------------------------------------------------------------- Detector puro


def test_refusal_frases_tipicas():
    assert is_llm_refusal("Lo siento, no es posible generar las fichas con las fuentes provistas.")
    assert is_llm_refusal("Con las fuentes proporcionadas no se puede determinar el portafolio.")
    assert is_llm_refusal("I'm sorry, I cannot complete this with the sources provided.")
    assert is_llm_refusal("")  # vacío = fallo


def test_refusal_capitulo_corto_dominado_por_ausencia():
    texto = (
        "Dato no disponible en fuentes consultadas.\n"
        "Dato no disponible en fuentes consultadas.\n"
        "Dato no disponible en fuentes consultadas."
    )
    assert is_llm_refusal(texto)


def test_no_refusal_capitulo_legitimo_con_una_ausencia():
    # Capítulo largo y real con UNA ausencia puntual: no es negativa.
    lineas = [f"Párrafo {i} con análisis competitivo real y cifras concretas." for i in range(20)]
    lineas.append("Dato no disponible en fuentes consultadas.")
    assert not is_llm_refusal("\n".join(lineas))


# --------------------------------------------------------------------------- Escalada


class _SeqChain:
    """Cadena que devuelve respuestas en orden y cuenta invocaciones."""

    def __init__(self, salidas: list[str], etiqueta: str) -> None:
        self._salidas = salidas
        self.etiqueta = etiqueta
        self.calls = 0

    def invoke(self, _inputs: dict) -> str:
        i = min(self.calls, len(self._salidas) - 1)
        self.calls += 1
        return self._salidas[i]


class _FakeStore:
    def search(self, *a, **k) -> list[ChunkResult]:
        return [
            ChunkResult(chunk_texto=f"F{i}", fuente_tipo="web", fuente_url=f"u{i}", score=0.9)
            for i in range(6)
        ]

    def ingest(self, *a, **k) -> None:
        pass


class _FakeWeb:
    def search(self, *a, **k) -> list:
        return []


_REFUSAL = "Lo siento, no es posible generar las fichas con las fuentes proporcionadas."
_OK = "## 2.1\n\n| Campo | Valor |\n|--|--|\n| Nombre + País | Danone — Francia |\n\nAnálisis real."


def _run(primary: _SeqChain, escalation: _SeqChain | None):
    return GenerateBenchmarking(
        chain=primary, store=_FakeStore(), web_connector=_FakeWeb(),
        escalation_chain=escalation,
    ).execute(nombre_empresa="Alpina", descripcion_empresa="Láctea.", sector_gics="Alimentos")


def test_primaria_ok_no_reintenta_ni_escala():
    primary = _SeqChain([_OK], "primary")
    escalation = _SeqChain([_OK], "escalation")
    cap = _run(primary, escalation)
    assert primary.calls == 1  # una sola llamada
    assert escalation.calls == 0  # no escaló
    assert cap.retrieval_suficiente is True


def test_negativa_persistente_escala_y_usa_el_texto_bueno():
    primary = _SeqChain([_REFUSAL, _REFUSAL], "primary")  # falla y re-falla
    escalation = _SeqChain([_OK], "escalation")
    cap = _run(primary, escalation)
    assert primary.calls == 2  # invoke inicial + retry
    assert escalation.calls == 1  # escaló una vez
    assert cap.retrieval_suficiente is True
    assert "Danone" in cap.texto


def test_retry_primario_basta_no_escala():
    primary = _SeqChain([_REFUSAL, _OK], "primary")  # el retry ya funciona
    escalation = _SeqChain([_OK], "escalation")
    cap = _run(primary, escalation)
    assert primary.calls == 2
    assert escalation.calls == 0  # el retry bastó
    assert cap.retrieval_suficiente is True


def test_negativa_sin_escalada_emite_ausencia():
    primary = _SeqChain([_REFUSAL, _REFUSAL], "primary")
    cap = _run(primary, escalation=None)
    assert primary.calls == 2
    assert cap.retrieval_suficiente is False  # párrafo de ausencia, no la negativa
    assert "Dato no disponible" in cap.texto
