from dataclasses import dataclass, field


@dataclass
class WebResult:
    url: str
    title: str
    content: str
    snippet: str = ""


@dataclass
class ChunkResult:
    chunk_texto: str
    fuente_tipo: str
    fuente_url: str | None
    score: float
    metadatos: dict | None = field(default=None)
