"""Mapeo CIIU -> Seccion CIIU Rev.4 -> codigos GICS candidatos (Fase 14, T14.6, DT-023).

Sirve para (a) acotar la clasificacion GICS del LLM cuando se conoce el CIIU de la empresa y
(b) validar/corregir el `sector_gics` resuelto antes del filtro sectorial (ADR-012).
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from ic.shared.constants._ciiu_tables import (
    _CIIU_CLASE_OVERRIDES,
    _CIIU_DIVISION_GICS,
    _SECCION_RANGOS,
)
from ic.shared.constants.gics_groups import _normalize, gics_options

_CSV_PATH = (
    Path(__file__).resolve().parents[4] / "documentos_sectoriales" / "Comparacion_GICS_CIIU.csv"
)


def ciiu_to_seccion(ciiu: str | int | None) -> str | None:
    """Devuelve la letra de Seccion CIIU Rev.4 para un CIIU numerico, o None."""
    if ciiu is None:
        return None
    digitos = "".join(c for c in str(ciiu) if c.isdigit())
    if len(digitos) < 2:
        return None
    try:
        division = int(digitos[:2])
    except ValueError:
        return None
    for d_min, d_max, letra in _SECCION_RANGOS:
        if d_min <= division <= d_max:
            return letra
    return None


@lru_cache(maxsize=1)
def _seccion_to_gics_names() -> dict[str, list[str]]:
    """Carga el CSV una vez: {letra_seccion: [nombres de grupos GICS]}."""
    mapping: dict[str, list[str]] = {}
    if not _CSV_PATH.exists():
        return mapping
    with open(_CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)
        for fila in reader:
            if len(fila) < 3:
                continue
            letra = fila[0].strip()
            nombres = [n.strip() for n in fila[2].splitlines() if n.strip()]
            if letra:
                mapping[letra] = nombres
    return mapping


_STOPWORDS = {"de", "y", "la", "el", "los", "las", "en", "al", "para", "-", "del"}


def _tokens(texto: str) -> set[str]:
    """Tokens significativos (normalizados, sin stopwords ni puntuacion suelta)."""
    palabras = _normalize(texto).replace(",", " ").replace("?", " ").split()
    return {p for p in palabras if p and p not in _STOPWORDS}


def _resolve_name_to_code(nombre: str) -> str | None:
    """Resuelve un nombre de grupo del CSV a su codigo GICS."""
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
    """Codigos GICS candidatos para un CIIU dado (via su Seccion CIIU)."""
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


_CIIU_EMBEBIDO_RE = re.compile(r"\(([A-U])(\d{3,4})\)")


def extract_ciiu_from_text(texto: str | None) -> str | None:
    """Extrae el codigo CIIU numerico embebido en el texto."""
    if not texto:
        return None
    m = _CIIU_EMBEBIDO_RE.search(texto)
    return m.group(2) if m else None


def extract_all_ciiu_from_text(texto: str | None) -> list[str]:
    """Todos los codigos CIIU embebidos, en orden de aparicion sin duplicados."""
    if not texto:
        return []
    vistos: list[str] = []
    for _, digitos in _CIIU_EMBEBIDO_RE.findall(texto):
        if digitos not in vistos:
            vistos.append(digitos)
    return vistos


def ciiu_division_to_gics(ciiu: str | int | None) -> str | None:
    """Resuelve un UNICO codigo GICS de grupo para un CIIU, por division (2 dig)."""
    if ciiu is None:
        return None
    digitos = "".join(c for c in str(ciiu) if c.isdigit())
    if len(digitos) < 2:
        return None
    if len(digitos) >= 4 and digitos[:4] in _CIIU_CLASE_OVERRIDES:
        return _CIIU_CLASE_OVERRIDES[digitos[:4]]
    division = int(digitos[:2])
    if division in _CIIU_DIVISION_GICS:
        return _CIIU_DIVISION_GICS[division]
    candidatos = ciiu_to_gics_candidates(digitos)
    return candidatos[0] if candidatos else None


def sectores_ancla_local(g_code: str | None, ciiu: str | int | None) -> list[str]:
    """Sectores GICS a consultar para el anclaje LOCAL (2.1.2/2.1.3)."""
    sectores = [g_code] if g_code else []
    div = ciiu_division_to_gics(ciiu)
    if div and div not in sectores:
        sectores.append(div)
    return sectores
