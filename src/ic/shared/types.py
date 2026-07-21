from dataclasses import dataclass, field


@dataclass
class WebResult:
    url: str
    title: str
    content: str
    snippet: str = ""
    metadatos: dict | None = field(default=None)


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
    chunks_usados: list["ChunkResult"] = field(default_factory=list)
    tabla_data: list[list[str]] | None = None  # datos estructurados para tabla Word (T11.3)


@dataclass
class Referencia:
    clave: str
    autor: str
    año: str
    titulo: str
    fuente: str
    url: str | None
    apa_string: str


@dataclass
class CostReport:
    """Registro de costo de una llamada LLM individual."""
    modelo: str
    tokens_in: int
    tokens_out: int
    costo_usd: float
    capitulo: str = ""


@dataclass
class CapTendencias:
    texto: str
    n_chunks_usados: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class CapEcosistema:
    texto: str
    n_chunks_usados: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class CapConvergencia:
    texto: str
    n_chunks_usados: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class CapAccionables:
    texto: str
    n_chunks_usados: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class ResumenEjecutivo:
    texto: str
    n_chunks_usados: int = 0
    retrieval_suficiente: bool = True
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class InformePiloto:
    empresa: DescripcionEmpresa
    gics: ClasificacionGICS
    cap_benchmarking: CapBenchmarking
    cap_tendencias: "CapTendencias | None" = None
    cap_ecosistema: "CapEcosistema | None" = None
    cap_convergencia: "CapConvergencia | None" = None
    cap_accionables: "CapAccionables | None" = None
    resumen_ejecutivo: "ResumenEjecutivo | None" = None
    referencias: list[Referencia] = field(default_factory=list)
    ruta_docx: str | None = None
    cost_reports: list[CostReport] = field(default_factory=list)
    costo_total_usd: float = 0.0
