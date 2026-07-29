"""Coherencia interna del informe (Fase 22, T22.1, Q1).

Funciones puras (Dependency Agnosticism): construyen el contexto de "hallazgos de capítulos
anteriores" que alimenta al Cap 6 (Accionables) para que sus recomendaciones referencien
explícitamente el análisis previo (benchmarking, tendencias, ecosistema, convergencia), en
lugar de derivarse solo del retrieval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Encabezado de área del Cap 5 en formato canónico markdown: "## 5.1 Área Estratégica: ..."
_CAP5_AREA_RE = re.compile(r"^##\s*5\.(\d+)\b.*$", re.MULTILINE)


@dataclass(frozen=True)
class SectorHistogram:
    """Histograma anti-mezcla de los chunks citados (Fase 22, T22.A3, TIER 4 trazabilidad).

    Clasifica cada chunk citado respecto al sector de la empresa del informe:
    - ``on_sector``: el chunk pertenece al sector esperado (primario o array multi-sector).
    - ``exento``: fuente sin sector propio (web/académica) o documento global cross-sector
      (``es_global=true``) — exenta por diseño (ADR-012/018).
    - ``ajeno``: chunk de un sector específico DISTINTO al esperado → contaminación real.

    ``ajenos`` lista los (titulo, sector_gics) de los chunks ajenos para el log de auditoría.
    """

    on_sector: int = 0
    exento: int = 0
    ajeno: int = 0
    ajenos: list[tuple[str, str]] = field(default_factory=list)


def _es_global(meta: dict) -> bool:
    """`es_global` viene de jsonb: puede ser bool True o la cadena 'true'."""
    val = meta.get("es_global")
    return val is True or str(val).lower() == "true"


def sector_histogram(
    metadatos: list[dict | None], sector_empresa: str
) -> SectorHistogram:
    """Clasifica los metadatos de los chunks citados por su relación con el sector esperado.

    Helper puro (Dependency Agnosticism): opera sobre los ``metadatos`` ya en memoria de los
    chunks citados, sin I/O. Criterio DT-053 (multi-sector): un chunk es *on-sector* si el
    sector de la empresa coincide con su ``sector_gics`` primario O está en su array
    ``sectores``; es *exento* si es global (``es_global``) o no trae sector propio
    (``sector_gics`` None y ``sectores`` vacío); *ajeno* en otro caso.

    RN-001: solo mide y reporta; nunca reatribuye ni inventa la fuente de un chunk.
    """
    on_sector = exento = ajeno = 0
    ajenos: list[tuple[str, str]] = []
    for meta in metadatos:
        meta = meta or {}
        sector_gics = meta.get("sector_gics")
        sectores = meta.get("sectores") or []
        if sector_empresa == sector_gics or sector_empresa in sectores:
            on_sector += 1
        elif _es_global(meta) or (sector_gics is None and not sectores):
            exento += 1
        else:
            ajeno += 1
            ajenos.append((meta.get("titulo") or "(sin título)", str(sector_gics)))
    return SectorHistogram(
        on_sector=on_sector, exento=exento, ajeno=ajeno, ajenos=ajenos
    )


def build_caps_summary(
    caps: list[tuple[str, str]], max_chars_per_cap: int = 600
) -> str:
    """Une resúmenes etiquetados de capítulos previos para inyectarlos en un prompt.

    `caps` es una lista de pares (etiqueta, texto). Cada texto se recorta a
    `max_chars_per_cap` caracteres (por límite de contexto) y se antepone su etiqueta. Los
    capítulos con texto vacío o en blanco se ignoran. Devuelve el bloque unido, o "" si no
    hay contenido.
    """
    partes: list[str] = []
    for etiqueta, texto in caps:
        if not texto or not texto.strip():
            continue
        recorte = texto.strip()
        if len(recorte) > max_chars_per_cap:
            recorte = recorte[:max_chars_per_cap].rstrip() + "…"
        partes.append(f"## {etiqueta}\n{recorte}")
    return "\n\n---\n\n".join(partes)


def enforce_cap5_areas(texto: str, max_area: int = 4) -> tuple[str, list[str]]:
    """Fija el Cap 5 a sus áreas canónicas (Fase 22, T22.6, DT-047).

    El Cap 5 (Convergencia) tiene EXACTAMENTE 4 áreas (5.1–5.4). La síntesis del LLM a veces
    inventa subsecciones extra (5.5, 5.6…). Esta función elimina las áreas cuyo número supera
    `max_area`, conservando el intro (texto antes de la primera `## 5.x`) y las áreas 5.1–5.4.
    Cada área abarca desde su encabezado hasta el siguiente `## 5.x` o el fin del texto.

    Es RN-safe: quitar áreas improvisadas no fabrica contenido. Devuelve el texto saneado y la
    lista de encabezados eliminados (para logging). Si no hay encabezados `## 5.x`, no toca nada.
    """
    matches = list(_CAP5_AREA_RE.finditer(texto))
    if not matches:
        return texto, []

    partes: list[str] = [texto[: matches[0].start()]]
    eliminados: list[str] = []
    for i, m in enumerate(matches):
        fin = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        seccion = texto[m.start():fin]
        if int(m.group(1)) <= max_area:
            partes.append(seccion)
        else:
            eliminados.append(m.group(0).strip())

    if not eliminados:
        return texto, []
    saneado = "".join(partes).rstrip() + "\n"
    return saneado, eliminados
