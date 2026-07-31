"""Semilla mínima de pares competidores VERIFICADOS por sector (DT-061/T3).

Datos curados por humano (no salida del LLM): empresas reales, consolidadas y verificables del
sector, con su sub-actividad GICS (food/beverage/tobacco). Alimentan el KB como estado
``verificado`` con provenance ``usuario/curado`` (RN-001: curación honesta, no invención). El
``nombre_normalizado`` está precalculado con la misma clave de dedup del NER
(``normalize_entity``) para consolidar con candidatos ya presentes sin duplicar; un test verifica
esa consistencia. Esta semilla es un arranque **mínimo**; la cobertura regional amplia llega con
la base Colombia (DT-050), que reusa el mismo esquema (``sub_gics``).

La empresa Alpina se omite a propósito (es la empresa analizada del E2E de calibración).
"""

from __future__ import annotations

from ic.shared.constants.gics_groups import (
    SUB_GICS_302020_FOOD,
)

# sector_gics (grupo, 4 díg) → lista de pares verificados con su sub-código (6 díg).
PARES_VERIFICADOS: dict[str, list[dict[str, str]]] = {
    "3020": [
        # Lácteos / alimentos Colombia (pares directos de una láctea).
        {"nombre": "Colanta", "nombre_normalizado": "colanta", "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Alquería", "nombre_normalizado": "alquería", "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Coolechera", "nombre_normalizado": "coolechera",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Colácteos", "nombre_normalizado": "colácteos",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Freskaleche", "nombre_normalizado": "freskaleche",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Parmalat", "nombre_normalizado": "parmalat", "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Gloria Colombia", "nombre_normalizado": "gloria colombia",
         "sub_gics": SUB_GICS_302020_FOOD},
        # Alimentos Colombia (mismo sub-sector, pares indirectos).
        {"nombre": "Grupo Nutresa", "nombre_normalizado": "grupo nutresa",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Colombina", "nombre_normalizado": "colombina",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Team Foods Colombia", "nombre_normalizado": "team foods colombia",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Casa Luker", "nombre_normalizado": "casa luker",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Productos Ramo", "nombre_normalizado": "productos ramo",
         "sub_gics": SUB_GICS_302020_FOOD},
        # Lácteos / alimentos globales consolidados.
        {"nombre": "Nestlé", "nombre_normalizado": "nestlé", "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Danone", "nombre_normalizado": "danone", "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Lactalis", "nombre_normalizado": "lactalis", "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "FrieslandCampina", "nombre_normalizado": "frieslandcampina",
         "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Fonterra", "nombre_normalizado": "fonterra", "sub_gics": SUB_GICS_302020_FOOD},
        {"nombre": "Arla Foods", "nombre_normalizado": "arla foods",
         "sub_gics": SUB_GICS_302020_FOOD},
    ],
}


def pares_de_sector(sector_gics: str) -> list[dict[str, str]]:
    """Pares verificados curados de un sector (lista vacía si no hay semilla). Puro."""
    return PARES_VERIFICADOS.get(sector_gics, [])
