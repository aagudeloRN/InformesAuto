"""Loop de auto-revisión por-nodo (DT-059/T2) — Reflection/Reflexion, guardar-el-mejor.

Orquestación **pura** (Dependency Agnosticism): recibe callables inyectados
(`generate_fn`, `judge_fn`, `revise_fn`) y no toca BD, LLM ni red directamente. El caller
(self_review_hooks) construye esos callables con las cadenas y el store del pipeline.

Contrato (PROPUESTA_KNOWLEDGE_BASE.md §4, decisiones cerradas):
- Genera → juzga con la rúbrica → si no pasa el gate, revisa y re-juzga → repite.
- **Guardar el MEJOR por score** (no el último). Parada: score pasa el gate (`umbral`) O una
  iteración no mejora el mejor score (`sin_mejora`) O se alcanza `max_iter` (`max_iter`).
- **Selectivo** lo aplica el caller: solo invoca el loop para el capítulo cuyo score inicial no
  pasa el gate; los que pasan a la primera no se re-generan.

Genérico en el tipo del capítulo (`TypeVar Cap`): sirve a cualquier `Cap*` de `shared.types`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ic.domain.eval.rubric_score import MIN_TOTAL_DEFAULT, RubricScore

# Motivos de parada del loop (telemetría/trazabilidad T4).
PARADA_UMBRAL = "umbral"
PARADA_SIN_MEJORA = "sin_mejora"
PARADA_MAX_ITER = "max_iter"


@dataclass
class RevisionTrace:
    """Traza de una corrida del loop para un capítulo (trazabilidad TIER 4).

    `intentos` incluye el score de la generación inicial (índice 0) y de cada revisión.
    `iter_ganadora` es el índice del intento cuyo capítulo se devuelve (el de mejor score).
    """

    intentos: list[RubricScore] = field(default_factory=list)
    iter_ganadora: int = 0
    motivo_parada: str = PARADA_MAX_ITER

    @property
    def n_iteraciones(self) -> int:
        """Número de revisiones realizadas (intentos - 1; la generación inicial no cuenta)."""
        return max(0, len(self.intentos) - 1)

    @property
    def mejor(self) -> RubricScore:
        return self.intentos[self.iter_ganadora]

    @property
    def score_inicial(self) -> int:
        return self.intentos[0].total if self.intentos else 0

    @property
    def score_final(self) -> int:
        return self.mejor.total if self.intentos else 0


def run_self_review[Cap](
    *,
    generate_fn: Callable[[], Cap],
    judge_fn: Callable[[Cap], RubricScore],
    revise_fn: Callable[[Cap, list[str]], Cap],
    min_total: int = MIN_TOTAL_DEFAULT,
    max_iter: int = 3,
) -> tuple[Cap, RevisionTrace]:
    """Ejecuta generar→juez→revisar conservando la MEJOR versión por score.

    - `generate_fn()` produce el capítulo inicial.
    - `judge_fn(cap)` lo puntúa (RubricScore).
    - `revise_fn(cap, faltantes)` produce una versión revisada guiada por los faltantes.

    Devuelve `(mejor_cap, traza)`. Nunca lanza por lógica de parada; si un callable lanza,
    la excepción se propaga al caller (que decide el fallo suave, patrón checkpoint).
    """
    cap = generate_fn()
    score = judge_fn(cap)

    trace = RevisionTrace(intentos=[score], iter_ganadora=0)
    mejor_cap = cap
    mejor_total = score.total

    if score.pasa_gate(min_total):
        trace.motivo_parada = PARADA_UMBRAL
        return mejor_cap, trace

    cap_actual, score_actual = cap, score
    for _ in range(max_iter):
        cap_actual = revise_fn(cap_actual, score_actual.faltantes)
        score_actual = judge_fn(cap_actual)
        trace.intentos.append(score_actual)

        if score_actual.total > mejor_total:
            mejor_cap, mejor_total = cap_actual, score_actual.total
            trace.iter_ganadora = len(trace.intentos) - 1
            if score_actual.pasa_gate(min_total):
                trace.motivo_parada = PARADA_UMBRAL
                return mejor_cap, trace
        else:
            # La revisión no superó el mejor score conocido → sin sentido seguir (Reflexion:
            # las revisiones deberían mejorar; si no lo hacen, paramos y conservamos el mejor).
            trace.motivo_parada = PARADA_SIN_MEJORA
            return mejor_cap, trace

    trace.motivo_parada = PARADA_MAX_ITER
    return mejor_cap, trace
