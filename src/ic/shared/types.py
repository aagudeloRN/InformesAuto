from dataclasses import dataclass, field
from enum import Enum


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
    chunk_id: str | None = None  # id del EmbeddingVectorial (trazabilidad: MMR, persistencia web)


@dataclass
class DescripcionEmpresa:
    nombre_empresa: str
    actividad_ciiu: str | None
    texto: str
    # DT-063: bloque "## Productos y servicios" extraído de la descripción (Cap 1). Señal de
    # precisión que guía el descubrimiento de competidores (steer del prompt global + re-rank de
    # locales por solape de actividad), en vez del sub-código GICS. "" → fallback a nivel grupo.
    productos_servicios: str = ""


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
    radar_data: dict | None = None  # {dimensions: [...], competidores: {nombre: [scores]}} (T16.1)


@dataclass
class Referencia:
    clave: str
    autor: str
    año: str
    titulo: str
    fuente: str
    url: str | None
    apa_string: str


class CuadranteKey(str, Enum):
    """Identificadores internos de los cuatro cuadrantes de la matriz 2×2 de Cap 2.2."""
    MASIVO_TRADICIONAL = "masivo_tradicional"
    MASIVO_INNOVADOR   = "masivo_innovador"
    NICHO_TRADICIONAL  = "nicho_tradicional"
    NICHO_INNOVADOR    = "nicho_innovador"


@dataclass
class ClasificacionCompetidor:
    """Asignación de un competidor de Cap 2.1 a uno de los cuatro cuadrantes."""
    nombre: str
    cuadrante: CuadranteKey
    dato_no_disponible: bool = False


@dataclass
class Cap22Division:
    """Resultado completo del subcapítulo 2.2 División de Competidores."""
    texto: str
    clasificaciones: list["ClasificacionCompetidor"]
    n_empresas_procesadas: int
    retrieval_suficiente: bool
    warnings_nombres_ajenos: list[str] = field(default_factory=list)


@dataclass
class Cap21Globales:
    texto: str
    candidatos: list[str]
    n_candidatos_con_web: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class Cap21Regionales:
    texto: str
    empresas_emis: list[str]
    n_con_emis: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class Cap21Startups:
    texto: str
    locales: list[str]
    internacionales: list[str]
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class Cap21Jugadores:
    texto: str
    globales: "Cap21Globales | None"
    regionales: "Cap21Regionales | None"
    startups: "Cap21Startups | None"
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


@dataclass
class CostReport:
    """Registro de costo de una llamada LLM individual."""
    modelo: str
    tokens_in: int
    tokens_out: int
    costo_usd: float
    capitulo: str = ""


@dataclass
class CapMercado:
    """Cap 2.3 Mercado (T21.6, DT-044): tamaño de mercado, segmentos y tabla por región."""
    texto: str
    n_chunks_usados: int
    retrieval_suficiente: bool
    chunks_usados: list["ChunkResult"] = field(default_factory=list)


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
    cap_22_division: "Cap22Division | None" = None
    cap_mercado: "CapMercado | None" = None
    cap_tendencias: "CapTendencias | None" = None
    cap_ecosistema: "CapEcosistema | None" = None
    cap_convergencia: "CapConvergencia | None" = None
    cap_accionables: "CapAccionables | None" = None
    resumen_ejecutivo: "ResumenEjecutivo | None" = None
    referencias: list[Referencia] = field(default_factory=list)
    ruta_docx: str | None = None
    cost_reports: list[CostReport] = field(default_factory=list)
    costo_total_usd: float = 0.0
