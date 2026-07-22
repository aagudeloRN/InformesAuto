"""Mapeo CIIU → Sección CIIU Rev.4 → códigos GICS candidatos (Fase 14, T14.6, DT-023).

Sirve para (a) acotar la clasificación GICS del LLM cuando se conoce el CIIU de la empresa y
(b) validar/corregir el `sector_gics` resuelto antes del filtro sectorial (ADR-012).

La tabla origen es `documentos_sectoriales/Comparacion_GICS_CIIU.csv` (Sección CIIU → nombres
de Grupos Industriales GICS). El mapeo es grueso y multivaluado: una Sección puede
corresponder a varios grupos GICS.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from ic.shared.constants.gics_groups import _normalize, gics_options

# .../src/ic/shared/constants/ciiu_gics.py → parents[4] es la raíz del repo.
_CSV_PATH = (
    Path(__file__).resolve().parents[4]
    / "documentos_sectoriales"
    / "Comparacion_GICS_CIIU.csv"
)

# CIIU Rev.4: rango de divisiones (2 primeros dígitos) → letra de Sección.
# (01-03=A, 05-09=B, 10-33=C, 35=D, 36-39=E, 41-43=F, 45-47=G, 49-53=H, 55-56=I, 58-63=J,
#  64-66=K, 68=L, 69-75=M, 77-82=N, 84=O, 85=P, 86-88=Q, 90-93=R, 94-96=S, 97-98=T, 99=U)
_SECCION_RANGOS: list[tuple[int, int, str]] = [
    (1, 3, "A"), (5, 9, "B"), (10, 33, "C"), (35, 35, "D"), (36, 39, "E"),
    (41, 43, "F"), (45, 47, "G"), (49, 53, "H"), (55, 56, "I"), (58, 63, "J"),
    (64, 66, "K"), (68, 68, "L"), (69, 75, "M"), (77, 82, "N"), (84, 84, "O"),
    (85, 85, "P"), (86, 88, "Q"), (90, 93, "R"), (94, 96, "S"), (97, 98, "T"),
    (99, 99, "U"),
]


def ciiu_to_seccion(ciiu: str | int | None) -> str | None:
    """Devuelve la letra de Sección CIIU Rev.4 para un CIIU numérico, o None.

    Toma los 2 primeros dígitos (la división). Acepta str o int; ignora prefijos no
    numéricos. Devuelve None si no hay dígitos suficientes o la división está fuera de rango.
    """
    if ciiu is None:
        return None
    digitos = "".join(c for c in str(ciiu) if c.isdigit())
    if len(digitos) < 2:
        return None
    division = int(digitos[:2])
    for lo, hi, letra in _SECCION_RANGOS:
        if lo <= division <= hi:
            return letra
    return None


@lru_cache(maxsize=1)
def _seccion_to_gics_names() -> dict[str, list[str]]:
    """Carga el CSV una vez: {letra_seccion: [nombres de grupos GICS]}."""
    mapping: dict[str, list[str]] = {}
    with open(_CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)  # cabecera
        for fila in reader:
            if len(fila) < 3:
                continue
            letra = fila[0].strip()
            nombres = [n.strip() for n in fila[2].splitlines() if n.strip()]
            if letra:
                mapping[letra] = nombres
    return mapping


# Palabras vacías que no aportan a la desambiguación entre grupos.
_STOPWORDS = {"de", "y", "la", "el", "los", "las", "en", "al", "para", "-", "del"}


def _tokens(texto: str) -> set[str]:
    """Tokens significativos (normalizados, sin stopwords ni puntuación suelta)."""
    palabras = _normalize(texto).replace(",", " ").replace("—", " ").split()
    return {p for p in palabras if p and p not in _STOPWORDS}


def _resolve_name_to_code(nombre: str) -> str | None:
    """Resuelve un nombre de grupo del CSV a su código GICS (matching tolerante).

    1. Igualdad exacta normalizada (cubre la mayoría de los nombres del CSV).
    2. Máximo solapamiento de tokens significativos. Los nombres del CSV difieren a veces del
       canónico (p.ej. "Fideicomisos ... de capital" vs "... — REITs"), por lo que la
       contención literal falla; el solapamiento de tokens es robusto a esas variaciones.
    """
    objetivo = _normalize(nombre)
    if not objetivo:
        return None
    objetivo_tokens = _tokens(nombre)
    mejor: tuple[int, str] | None = None
    for code, canon in gics_options():
        if _normalize(canon) == objetivo:
            return code
        comunes = len(objetivo_tokens & _tokens(canon))
        if comunes > 0 and (mejor is None or comunes > mejor[0]):
            mejor = (comunes, code)
    return mejor[1] if mejor else None


def ciiu_to_gics_candidates(ciiu: str | int | None) -> list[str]:
    """Códigos GICS candidatos para un CIIU dado (vía su Sección CIIU). Multivaluado.

    Devuelve lista vacía si no hay CIIU, la Sección no mapea, o es "Sin correspondencia".
    Los códigos se devuelven sin duplicados, en orden estable.
    """
    seccion = ciiu_to_seccion(ciiu)
    if seccion is None:
        return []
    nombres = _seccion_to_gics_names().get(seccion, [])
    codigos: list[str] = []
    for nombre in nombres:
        code = _resolve_name_to_code(nombre)
        if code and code not in codigos:
            codigos.append(code)
    return codigos
