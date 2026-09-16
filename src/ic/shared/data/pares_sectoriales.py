"""Semilla mínima de pares competidores VERIFICADOS por sector (DT-061/T3, DT-061b).

Datos curados por humano (no salida del LLM): empresas reales, consolidadas y verificables del
sector, con su sub-actividad GICS (food/beverage/tobacco) y su **alcance** (``global`` = actor de
clase mundial / ``local`` = jugador grande de país). Alimentan el KB como estado ``verificado`` con
provenance ``usuario/curado`` (RN-001: curación honesta, no invención).

El anclaje de la sección de competidores de **clase mundial** (2.1.1) filtra ``alcance='global'``;
los locales grandes (Colanta, Alquería…) son otro componente y su fuente natural es la base Colombia
(DT-050). Un actor local que además sea referencia mundial (p. ej. Nutresa) se marca ``global``.

El ``nombre_normalizado`` está precalculado con la clave de dedup del NER (``normalize_entity``)
para consolidar con candidatos ya presentes sin duplicar; un test lo verifica. Semilla de
arranque **mínima**; el recall global amplio llega con DT-062 (LLM recomienda actores globales,
corroborado por web). La empresa Alpina se omite a propósito (es la analizada del E2E).
"""

from __future__ import annotations

from ic.shared.constants.gics_groups import SUB_GICS_302020_FOOD

_GLOBAL = "global"
_LOCAL = "local"

# sector_gics (grupo, 4 díg) → pares verificados (nombre, normalizado, sub-código, alcance).
PARES_VERIFICADOS: dict[str, list[dict[str, str]]] = {
    "3020": [
        # --- Clase mundial (alcance=global): actores lácteos/food representativos globales. ---
        {
            "nombre": "Nestlé",
            "nombre_normalizado": "nestlé",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Danone",
            "nombre_normalizado": "danone",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Lactalis",
            "nombre_normalizado": "lactalis",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "FrieslandCampina",
            "nombre_normalizado": "frieslandcampina",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Fonterra",
            "nombre_normalizado": "fonterra",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Arla Foods",
            "nombre_normalizado": "arla foods",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Parmalat",
            "nombre_normalizado": "parmalat",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Yili",
            "nombre_normalizado": "yili",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Mengniu",
            "nombre_normalizado": "mengniu",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Saputo",
            "nombre_normalizado": "saputo",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Savencia",
            "nombre_normalizado": "savencia",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        {
            "nombre": "Grupo Lala",
            "nombre_normalizado": "grupo lala",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        # Frontera: multinacional latina con presencia global → clase mundial.
        {
            "nombre": "Grupo Nutresa",
            "nombre_normalizado": "grupo nutresa",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _GLOBAL,
        },
        # --- Jugadores locales grandes (alcance=local): otro componente (2.1.2 / DT-050). ---
        {
            "nombre": "Colanta",
            "nombre_normalizado": "colanta",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Alquería",
            "nombre_normalizado": "alquería",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Coolechera",
            "nombre_normalizado": "coolechera",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Colácteos",
            "nombre_normalizado": "colácteos",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Freskaleche",
            "nombre_normalizado": "freskaleche",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Gloria Colombia",
            "nombre_normalizado": "gloria colombia",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Colombina",
            "nombre_normalizado": "colombina",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Team Foods Colombia",
            "nombre_normalizado": "team foods colombia",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Casa Luker",
            "nombre_normalizado": "casa luker",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
        {
            "nombre": "Productos Ramo",
            "nombre_normalizado": "productos ramo",
            "sub_gics": SUB_GICS_302020_FOOD,
            "alcance": _LOCAL,
        },
    ],
}


def pares_de_sector(sector_gics: str) -> list[dict[str, str]]:
    """Pares verificados curados de un sector (lista vacía si no hay semilla). Puro."""
    return PARES_VERIFICADOS.get(sector_gics, [])
