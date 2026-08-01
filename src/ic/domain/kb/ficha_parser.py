"""Parser puro de las fichas de competidor del Cap 2 (DT-064/T3).

Extrae, del markdown que emite `chain_03_benchmarking`, los campos de cada ficha de la sección 2.1
para persistirlos en el KB (`entidad_atributos`) y reusarlos entre corridas del mismo sector. Sin
I/O ni dependencias de infraestructura (Dependency Agnosticism): reusa `parse_markdown`
(`domain/markdown_parser`) y devuelve un modelo verificable.

Formato de entrada: `SYSTEM_PROMPT_03` instruye una tabla vertical `| Campo | Valor |` por
competidor, agrupada bajo `### Referentes Globales / Regionales / Startups`. También tolera la tabla
ancha (una fila por competidor) de los informes manuales, para la futura siembra del KB.

RN-001: no fabrica datos. Descarta celdas vacías o "Dato no disponible"; el mapeo de etiquetas es
tolerante (substring sobre texto sin acentos) pero nunca inventa un campo que no esté en la tabla.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from ic.domain.markdown_parser import parse_markdown
from ic.domain.report_model import Heading, TableBlock

TIER_GLOBAL = "global"
TIER_REGIONAL = "regional"
TIER_STARTUP = "startup"

# Claves canónicas de ficha (DT064_FICHA_SPEC.md §"Campos por competidor").
FICHA_KEYS = (
    "pais_origen",
    "resumen_estrategico",
    "portafolio",
    "canales_precios",
    "presencia_geografica",
    "factor_diferencial",
    "propuesta_valor",
    "mayor_fortaleza",
)

_AUSENTE = "dato no disponible"


@dataclass
class FichaCompetidor:
    """Ficha de un competidor extraída de 2.1: nombre, tier y campos canónicos poblados."""

    nombre: str
    tier: str
    campos: dict[str, str] = field(default_factory=dict)


def _sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.casefold()) if unicodedata.category(c) != "Mn"
    )


def _tier_de_heading(texto: str) -> str | None:
    t = _sin_acentos(texto)
    if "global" in t:
        return TIER_GLOBAL
    if "regional" in t or "latam" in t or "colombia" in t:
        return TIER_REGIONAL
    if "startup" in t or "disruptor" in t or "foodtech" in t or "emergente" in t:
        return TIER_STARTUP
    return None


def _clave_de_etiqueta(label: str) -> str | None:
    """Mapea la etiqueta de una fila/columna a una clave canónica. Tolerante (substring)."""
    t = _sin_acentos(label)
    if "nombre" in t or t == "empresa":
        return "nombre"
    if "pais" in t or "origen" in t:
        return "pais_origen"
    if "resumen" in t:
        return "resumen_estrategico"
    if "portafolio" in t or "producto" in t:
        return "portafolio"
    if "canal" in t or "precio" in t:
        return "canales_precios"
    if "presencia" in t or "geografic" in t:
        return "presencia_geografica"
    if "fortaleza" in t:
        return "mayor_fortaleza"
    if "propuesta" in t or ("valor" in t and "diferencial" not in t):
        return "propuesta_valor"
    if "factor" in t or "diferencial" in t or "innovador" in t:
        return "factor_diferencial"
    return None


def _es_valor_util(valor: str) -> bool:
    v = valor.strip()
    return bool(v) and _AUSENTE not in _sin_acentos(v)


def _split_nombre_pais(valor: str) -> tuple[str, str | None]:
    """"Nestlé — Suiza" → ("Nestlé", "Suiza"). Sin separador → (valor, None)."""
    for sep in ("—", "–", " - ", "|"):
        if sep in valor:
            izq, der = valor.split(sep, 1)
            return izq.strip(), (der.strip() or None)
    return valor.strip(), None


def _campos_desde_pares(pares: list[tuple[str, str]]) -> tuple[str, dict[str, str]]:
    """De una lista (etiqueta, valor) arma (nombre, campos canónicos)."""
    nombre = ""
    campos: dict[str, str] = {}
    for etiqueta, valor in pares:
        clave = _clave_de_etiqueta(etiqueta)
        if clave is None or not _es_valor_util(valor):
            continue
        if clave == "nombre":
            nombre, pais = _split_nombre_pais(valor)
            if pais and "pais_origen" not in campos:
                campos["pais_origen"] = pais
        else:
            campos[clave] = valor.strip()
    return nombre, campos


def parse_fichas_competidores(texto: str) -> list[FichaCompetidor]:
    """Extrae las fichas de competidor de 2.1 desde el markdown del Cap 2. Puro.

    Reconoce dos formatos: tabla vertical `| Campo | Valor |` (una por competidor, la que emite el
    sistema) y tabla ancha (una fila por competidor, la de los informes manuales). Solo devuelve
    fichas con nombre y al menos un campo poblado.
    """
    blocks = parse_markdown(texto)
    fichas: list[FichaCompetidor] = []
    tier = TIER_GLOBAL  # por defecto hasta ver un heading de tier
    for block in blocks:
        if isinstance(block, Heading):
            nuevo = _tier_de_heading(block.text)
            if nuevo is not None:
                tier = nuevo
            continue
        if not isinstance(block, TableBlock):
            continue
        headers = [h.strip() for h in block.headers]
        claves_header = [_clave_de_etiqueta(h) for h in headers]
        es_vertical = len(headers) == 2 and claves_header.count("nombre") == 0
        if es_vertical:
            # Tabla vertical: la cabecera es (Campo, Valor) y cada fila es un par.
            pares = [(block.headers[0], block.headers[1])]
            pares += [(r[0], r[1]) for r in block.rows if len(r) >= 2]
            nombre, campos = _campos_desde_pares(pares)
            if nombre and campos:
                fichas.append(FichaCompetidor(nombre=nombre, tier=tier, campos=campos))
        elif "nombre" in claves_header:
            # Tabla ancha: cada fila de datos es una ficha; las columnas son los campos.
            for r in block.rows:
                pares = [(headers[i], r[i]) for i in range(min(len(headers), len(r)))]
                nombre, campos = _campos_desde_pares(pares)
                if nombre and campos:
                    fichas.append(FichaCompetidor(nombre=nombre, tier=tier, campos=campos))
    return fichas
