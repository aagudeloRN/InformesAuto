"""Mapeo CIIU → Sección CIIU Rev.4 → códigos GICS candidatos (Fase 14, T14.6, DT-023).

Sirve para (a) acotar la clasificación GICS del LLM cuando se conoce el CIIU de la empresa y
(b) validar/corregir el `sector_gics` resuelto antes del filtro sectorial (ADR-012).

La tabla origen es `documentos_sectoriales/Comparacion_GICS_CIIU.csv` (Sección CIIU → nombres
de Grupos Industriales GICS). El mapeo es grueso y multivaluado: una Sección puede
corresponder a varios grupos GICS.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from ic.shared.constants.gics_groups import _normalize, gics_options

# .../src/ic/shared/constants/ciiu_gics.py → parents[4] es la raíz del repo.
_CSV_PATH = (
    Path(__file__).resolve().parents[4] / "documentos_sectoriales" / "Comparacion_GICS_CIIU.csv"
)

# CIIU Rev.4: rango de divisiones (2 primeros dígitos) → letra de Sección.
# (01-03=A, 05-09=B, 10-33=C, 35=D, 36-39=E, 41-43=F, 45-47=G, 49-53=H, 55-56=I, 58-63=J,
#  64-66=K, 68=L, 69-75=M, 77-82=N, 84=O, 85=P, 86-88=Q, 90-93=R, 94-96=S, 97-98=T, 99=U)
_SECCION_RANGOS: list[tuple[int, int, str]] = [
    (1, 3, "A"),
    (5, 9, "B"),
    (10, 33, "C"),
    (35, 35, "D"),
    (36, 39, "E"),
    (41, 43, "F"),
    (45, 47, "G"),
    (49, 53, "H"),
    (55, 56, "I"),
    (58, 63, "J"),
    (64, 66, "K"),
    (68, 68, "L"),
    (69, 75, "M"),
    (77, 82, "N"),
    (84, 84, "O"),
    (85, 85, "P"),
    (86, 88, "Q"),
    (90, 93, "R"),
    (94, 96, "S"),
    (97, 98, "T"),
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


# --- Grano por DIVISIÓN CIIU (DT-050) -----------------------------------------------------------
# El mapeo por Sección (arriba) es multivaluado (Sección C → 10 grupos GICS): sirve para *acotar*
# la clasificación del LLM, pero es demasiado grueso para *asignar* un sector a las ~98k empresas
# del directorio EMIS. La columna "Sector (Local)" de EmpresasColombia trae el CIIU Rev.4 embebido
# entre paréntesis (p. ej. "…(M7010)", "…(F4111)", "…(A0141)"); con la DIVISIÓN (2 díg) se resuelve
# un grupo GICS único en el 99 %+ de los casos. Tabla finita y revisable (curación humana futura).
# Puro, sin modelo (ADR-002).

# Código CIIU con letra de Sección + 3-4 dígitos, embebido en el texto local: "…(M7010)".
_CIIU_EMBEBIDO_RE = re.compile(r"\(([A-U])(\d{3,4})\)")

# División (2 primeros dígitos) → código de Grupo GICS (4 díg). Elección del grupo dominante de la
# división; los casos genuinamente ambiguos (comercio) se afinan con `_CIIU_CLASE_OVERRIDES`.
_CIIU_DIVISION_GICS: dict[int, str] = {
    # A — Agricultura, ganadería, pesca → producción agroindustrial de alimentos.
    1: "3020",
    2: "3020",
    3: "3020",
    # B — Minería.
    5: "1010",
    6: "1010",
    7: "1510",
    8: "1510",
    9: "1010",
    # C — Manufactura.
    10: "3020",
    11: "3020",
    12: "3020",  # alimentos, bebidas, tabaco
    13: "2520",
    14: "2520",
    15: "2520",  # textiles, confección, cuero/calzado
    16: "1510",
    17: "1510",  # madera, papel
    18: "2020",  # impresión (servicios comerciales)
    19: "1010",  # coque y refinación de petróleo
    20: "1510",
    22: "1510",
    23: "1510",
    24: "1510",  # químicos, caucho/plástico, minerales, metales
    21: "3520",  # farmacéutica
    25: "2010",
    27: "2010",
    28: "2010",
    30: "2010",
    33: "2010",  # metalmecánica/maquinaria
    26: "4520",  # electrónica/informática/óptica
    29: "2510",  # vehículos automotores
    31: "2520",
    32: "2520",  # muebles, otras manufacturas
    # D — Electricidad/gas.
    35: "5510",
    # E — Agua/residuos.
    36: "5510",
    37: "2020",
    38: "2020",
    39: "2020",
    # F — Construcción.
    41: "2010",
    42: "2010",
    43: "2010",
    # G — Comercio (ambiguo 2550/3010; ver overrides de clase para básicos).
    45: "2550",
    46: "2550",
    47: "2550",
    # H — Transporte y almacenamiento.
    49: "2030",
    50: "2030",
    51: "2030",
    52: "2030",
    53: "2030",
    # I — Alojamiento y servicio de comidas.
    55: "2530",
    56: "2530",
    # J — Información y comunicaciones.
    58: "5020",
    59: "5020",
    60: "5020",  # edición, cine/música, radiodifusión
    61: "5010",  # telecomunicaciones
    62: "4510",
    63: "4510",  # programación, servicios de información
    # K — Financiero y seguros.
    64: "4010",
    65: "4030",
    66: "4020",
    # L — Inmobiliario.
    68: "6020",
    # M — Actividades profesionales, científicas y técnicas (publicidad → medios).
    69: "2020",
    70: "2020",
    71: "2020",
    72: "2020",
    73: "5020",
    74: "2020",
    75: "2020",
    # N — Servicios administrativos y de apoyo.
    77: "2020",
    78: "2020",
    79: "2020",
    80: "2020",
    81: "2020",
    82: "2020",
    # O — Administración pública y defensa.
    84: "2020",
    # P — Educación.
    85: "2530",
    # Q — Salud humana y asistencia social.
    86: "3510",
    87: "3510",
    88: "3510",
    # R — Arte, entretenimiento y recreación.
    90: "5020",
    91: "5020",
    92: "5020",
    93: "2530",
    # S — Otras actividades de servicios.
    94: "2020",
    95: "2530",
    96: "2530",
}

# Overrides por CLASE (4 díg) para la ambigüedad de comercio (Sección G): alimentos/farmacia son
# consumo básico (3010), no discrecional (2550). Solo se listan las clases básicas; el resto de G
# cae en el default de división (2550).
_CIIU_CLASE_OVERRIDES: dict[str, str] = {
    # mayorista de básicos (alimentos/bebidas/tabaco)
    "4630": "3010",
    "4631": "3010",
    "4632": "3010",
    "4633": "3010",
    "4634": "3010",
    "4711": "3010",
    "4719": "3010",  # minorista no especializado (predomina alimentos)
    # minorista de alimentos y bebidas
    "4721": "3010",
    "4722": "3010",
    "4723": "3010",
    "4724": "3010",
    "4729": "3010",
    "4773": "3010",  # minorista de productos farmacéuticos y medicinales
}


def extract_ciiu_from_text(texto: str | None) -> str | None:
    """Extrae el código CIIU numérico embebido en el texto "Sector (Local)". Puro.

    "Elaboración De Productos Lácteos (C1040)" → "1040". Devuelve la primera coincidencia (una
    empresa multi-actividad se separa aguas arriba). None si no hay código embebido.
    """
    if not texto:
        return None
    m = _CIIU_EMBEBIDO_RE.search(texto)
    return m.group(2) if m else None


def extract_all_ciiu_from_text(texto: str | None) -> list[str]:
    """Todos los códigos CIIU embebidos, en orden de aparición sin duplicados. Puro.

    Una fila EMIS multi-actividad ("… (M7010); … (M7020)") produce varias membresías sectoriales.
    """
    if not texto:
        return []
    vistos: list[str] = []
    for _, digitos in _CIIU_EMBEBIDO_RE.findall(texto):
        if digitos not in vistos:
            vistos.append(digitos)
    return vistos


def ciiu_division_to_gics(ciiu: str | int | None) -> str | None:
    """Resuelve un ÚNICO código GICS de grupo para un CIIU, por división (2 díg). Puro (DT-050).

    1. Override por clase (4 díg) para el comercio de básicos (alimentos/farmacia → 3010).
    2. División (2 díg) → grupo GICS dominante.
    3. Fallback: primer candidato del mapeo por Sección (grueso) si la división no está mapeada.

    None si no hay CIIU o no se puede resolver (p. ej. Sección U sin correspondencia).
    """
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
    """Sectores GICS a consultar para el anclaje LOCAL (2.1.2/2.1.3). Puro (DT-UI04b).

    El grupo clasificado por el LLM y el grupo canónico del CIIU pueden diferir sin que ninguno
    esté "mal": una generadora de energía solar (CIIU D3511) se clasifica coloquialmente como
    "Energía" (GICS 1010, que en GICS es petróleo/gas/minería) cuando su grupo GICS canónico es
    "Servicios públicos" (5510, Utilities), donde vive la data curada de pares (EPM, Celsia,
    Isagen). Anclar solo por el grupo del LLM deja el tier local con pares irrelevantes (minería)
    o vacío. Se une el grupo clasificado con el grupo **preciso** del CIIU por división
    (``ciiu_division_to_gics``, single y sin ruido — 8610→3510 no arrastra 2020) para que el
    re-rank por solape de producto elija los mejores pares de ambos. Orden estable, sin duplicados;
    ``ciiu`` ausente/no numérico → solo el grupo del LLM (invariante). No fabrica sectores: solo
    añade el que el CIIU ya implica de forma determinista (ADR-002).
    """
    sectores = [g_code] if g_code else []
    div = ciiu_division_to_gics(ciiu)
    if div and div not in sectores:
        sectores.append(div)
    return sectores
