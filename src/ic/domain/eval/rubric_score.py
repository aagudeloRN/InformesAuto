"""Puntuación de un capítulo con la rúbrica de calidad v1.0 (DT-059/T1).

Puro, sin I/O ni dependencias externas (Dependency Agnosticism): el juez LLM
(`chain_judge`) produce el texto crudo; aquí se **parsea** a una estructura verificable
(`RubricScore`) y se aplica el gate de aceptación de la rúbrica (§1 de
`docs/eval/RUBRICA_CALIDAD.md`).

Rúbrica v1.0: 5 dimensiones (E/P/V/F/T), cada una de 0 a 3. Score del capítulo = suma
(0–15). Gate de aceptación: **total ≥ 11** (≈73%) **y ninguna dimensión en 0**.

RN-001 (no fabricar): si la salida del juez no es parseable, NO se inventa un score alto;
se devuelve el peor caso (total=0, no pasa) con un faltante explícito, para que el loop
trate el capítulo como no-conforme en vez de aceptarlo por accidente.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Dimensiones de la rúbrica v1.0 (orden canónico). Ver RUBRICA_CALIDAD.md §1.
DIMENSIONES = ("E", "P", "V", "F", "T")

# Gate de aceptación por capítulo (RUBRICA_CALIDAD.md §1). Sobrescribible por config.
MIN_TOTAL_DEFAULT = 11
MAX_DIMENSION = 3

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class RubricScore:
    """Resultado de puntuar un capítulo: 5 dimensiones + total + faltantes accionables.

    `dimensiones` mapea cada clave de `DIMENSIONES` a un entero 0–3. `total` es la suma
    (0–15). `faltantes` son las carencias accionables que el juez detectó (insumo del
    revisor). `parseable` distingue un score real de un fallback por salida corrupta.
    """

    dimensiones: dict[str, int]
    faltantes: list[str] = field(default_factory=list)
    parseable: bool = True

    @property
    def total(self) -> int:
        return sum(self.dimensiones.values())

    def pasa_gate(self, min_total: int = MIN_TOTAL_DEFAULT) -> bool:
        """True si total ≥ min_total y ninguna dimensión en 0 (regla de la rúbrica §1)."""
        if len(self.dimensiones) < len(DIMENSIONES):
            return False
        return self.total >= min_total and min(self.dimensiones.values()) > 0


def _clamp_dim(value: object) -> int:
    """Coacciona un valor a un entero 0..MAX_DIMENSION. No parseable → 0 (peor caso)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(MAX_DIMENSION, n))


def _fallback(motivo: str) -> RubricScore:
    """Peor caso (RN-001): no se acepta un capítulo por una salida del juez no parseable."""
    return RubricScore(
        dimensiones={d: 0 for d in DIMENSIONES},
        faltantes=[motivo],
        parseable=False,
    )


def parse_rubric_score(raw: str) -> RubricScore:
    """Parsea la salida JSON del juez a un `RubricScore`. Puro: solo depura, no fabrica.

    Tolera fences ```json / ``` y texto alrededor del objeto. Recorta cada dimensión a
    0..3; una dimensión ausente cuenta como 0 (no cumple). `faltantes` se normaliza a
    lista de strings no vacíos. Salida no parseable → fallback de peor caso (RN-001).
    """
    if not raw or not raw.strip():
        return _fallback("El juez no devolvió salida")

    texto = raw.strip()
    m = _FENCE_RE.search(texto)
    if m:
        texto = m.group(1).strip()
    m = _OBJECT_RE.search(texto)
    if not m:
        return _fallback("La salida del juez no contiene un objeto JSON")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return _fallback("La salida del juez no es JSON válido")
    if not isinstance(data, dict):
        return _fallback("La salida del juez no es un objeto JSON")

    dimensiones = {d: _clamp_dim(data.get(d)) for d in DIMENSIONES}

    faltantes: list[str] = []
    raw_faltantes = data.get("faltantes")
    if isinstance(raw_faltantes, list):
        for item in raw_faltantes:
            if isinstance(item, str) and item.strip():
                faltantes.append(item.strip())

    return RubricScore(dimensiones=dimensiones, faltantes=faltantes, parseable=True)
