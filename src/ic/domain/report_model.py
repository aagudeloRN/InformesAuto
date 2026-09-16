"""Modelo de documento intermedio — bloques semánticos inmutables.

domain/ no importa python-docx ni matplotlib; solo define la estructura.
Los renderers en infrastructure/render/ consumen este modelo.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Heading:
    text: str
    level: int  # 1–4


@dataclass(frozen=True)
class Paragraph:
    text: str
    style: str = "Normal"


@dataclass(frozen=True)
class TableBlock:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    caption: str = ""


@dataclass(frozen=True)
class FigureBlock:
    image_path: str
    alt: str
    caption: str = ""


@dataclass(frozen=True)
class CitationBlock:
    apa_string: str  # puede contener marcadores *cursiva* (APA 7 — Fase 10)


@dataclass(frozen=True)
class Callout:
    text: str
    kind: str  # "absent_data" | "actionable" | "warning"


@dataclass(frozen=True)
class PageBreak:
    pass


@dataclass(frozen=True)
class Toc:
    title: str = "Tabla de Contenidos"


DocumentBlock = (
    Heading | Paragraph | TableBlock | FigureBlock | CitationBlock | Callout | PageBreak | Toc
)


@dataclass
class ReportDocument:
    title: str
    company: str
    date: str
    blocks: list[DocumentBlock] = field(default_factory=list)
    disclaimer: str = ""
