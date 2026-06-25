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


@dataclass
class DescripcionEmpresa:
    nombre_empresa: str
    actividad_ciiu: str | None
    texto: str


@dataclass
class ClasificacionGICS:
    grupo_gics: str
    justificacion: str
    texto_raw: str


@dataclass
class CapBenchmarking:
    texto: str
    n_chunks_usados: int
    retrieval_suficiente: bool
