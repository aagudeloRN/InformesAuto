"""Ensamblador determinista de la sección 2.2 (División de Competidores).

Recibe el JSON validado del LLM (cuadrantes + prosa) y la lista cerrada de empresas de
Cap 2.1. Convierte a markdown exactamente en el formato del contrato
`specs/004-cap22-division-competidores/contracts/markdown-output.md`.

Puro: sin I/O ni dependencias de infraestructura. Fácil de testear en aislamiento.
"""

from __future__ import annotations

_TITULO = "## 2.2. División de Competidores"

_CUADRANTE_LABELS: dict[str, tuple[str, str]] = {
    "masivo_tradicional": ("Masivo / Volumen", "Jugadores Tradicionales (Modelos Consolidados)"),
    "masivo_innovador":   ("Masivo / Volumen", "Entrantes Innovadores (Modelos Ágiles / DeepTech / Startups)"),
    "nicho_tradicional":  ("Nicho / Premium",  "Jugadores Tradicionales (Modelos Consolidados)"),
    "nicho_innovador":    ("Nicho / Premium",  "Entrantes Innovadores (Modelos Ágiles / DeepTech / Startups)"),
}

_ROW_ORDER = [
    ("Masivo / Volumen", "masivo_tradicional", "masivo_innovador"),
    ("Nicho / Premium",  "nicho_tradicional",  "nicho_innovador"),
]

_ABSENT_PARAGRAPH = (
    "## 2.2. División de Competidores\n\n"
    "La segmentación de grupos estratégicos no pudo realizarse porque no se identificaron "
    "competidores suficientes en la sección 2.1. Se recomienda ampliar las fuentes de datos "
    "o ajustar los criterios de búsqueda antes de regenerar este subcapítulo."
)

_NINGUNO = "(ninguno)"


class CoverageError(ValueError):
    """Se lanza cuando alguna empresa de la lista cerrada no queda clasificada."""


class DuplicateError(ValueError):
    """Se lanza cuando una empresa aparece en más de un cuadrante."""


def assemble_seccion_22(cap22_llm_output: dict, closed_list: list[str]) -> str:
    """Convierte el JSON validado del LLM en el markdown final de la sección 2.2.

    Args:
        cap22_llm_output: dict con claves ``cuadrantes`` (dict[str, list[str]]),
            ``intro`` (str), ``sintesis_incumbente`` (str), ``sintesis_entrante`` (str).
        closed_list: lista de nombres exactos de empresas de Cap 2.1 (ya validados).

    Returns:
        Markdown completo de la sección 2.2 conforme al contrato.

    Raises:
        CoverageError: si alguna empresa de closed_list no aparece en cuadrante alguno.
        DuplicateError: si alguna empresa aparece en más de un cuadrante.
    """
    cuadrantes: dict[str, list[str]] = cap22_llm_output.get("cuadrantes", {})
    intro: str = (cap22_llm_output.get("intro") or "").strip()
    sintesis_incumbente: str = (cap22_llm_output.get("sintesis_incumbente") or "").strip()
    sintesis_entrante: str = (cap22_llm_output.get("sintesis_entrante") or "").strip()

    # --- Validación de duplicados ---
    seen: dict[str, str] = {}
    for clave, nombres in cuadrantes.items():
        for nombre in nombres:
            if nombre in seen:
                raise DuplicateError(
                    f"'{nombre}' aparece en '{seen[nombre]}' y en '{clave}'"
                )
            seen[nombre] = clave

    # --- Validación de cobertura ---
    nombres_en_tabla = set(seen.keys())
    faltantes = [n for n in closed_list if n not in nombres_en_tabla]
    if faltantes:
        raise CoverageError(
            f"Empresas sin clasificar: {faltantes}"
        )

    # --- Render de la tabla 2×2 ---
    header = (
        "| Enfoque de mercado | "
        "Jugadores Tradicionales (Modelos Consolidados) | "
        "Entrantes Innovadores (Modelos Ágiles / DeepTech / Startups) |"
    )
    separator = "|---|---|---|"
    rows: list[str] = []
    for fila_label, clave_trad, clave_innov in _ROW_ORDER:
        cell_trad = ", ".join(cuadrantes.get(clave_trad, [])) or _NINGUNO
        cell_innov = ", ".join(cuadrantes.get(clave_innov, [])) or _NINGUNO
        rows.append(f"| **{fila_label}** | {cell_trad} | {cell_innov} |")

    tabla = "\n".join([header, separator, *rows])

    # --- Síntesis de Presión Competitiva ---
    sintesis = (
        "### Síntesis de Presión Competitiva\n\n"
        "#### La defensa del incumbente\n\n"
        f"{sintesis_incumbente}\n\n"
        "#### El ataque del entrante y la servitización\n\n"
        f"{sintesis_entrante}"
    )

    partes = [_TITULO, "", intro, "", tabla, "", sintesis]
    return "\n".join(partes).strip()


def absent_paragraph() -> str:
    """Devuelve el párrafo de ausencia estándar para Cap 2.2."""
    return _ABSENT_PARAGRAPH
