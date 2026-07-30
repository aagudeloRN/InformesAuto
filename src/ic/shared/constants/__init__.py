from enum import StrEnum


class EstadoInforme(StrEnum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    FALLIDO = "fallido"


class TipoDocumento(StrEnum):
    PDF_SECTORIAL = "pdf_sectorial"
    PAPER_ACADEMICO = "paper_academico"
    INFORME_EMIS = "informe_emis"
    OTRO = "otro"


class TipoFuente(StrEnum):
    """Etiqueta de procedencia del chunk (metadatos->>'tipo_fuente'), palanca de reserva/boost
    y telemetría de mix de fuentes. Distinta de ``TipoDocumento`` (tipo del documento).

    - INFORME_COMPILADO: informes sectoriales de Ruta N — compilaciones de múltiples fuentes
      (ADR-012); alimentan la reserva sectorial garantizada.
    - INFORME_EMIS: informes EMIS individuales (una fuente por doc). Antes quedaban con
      ``tipo_fuente`` NULL → sin telemetría ni palanca (DT-054); DT-057 los etiqueta.
    """

    INFORME_COMPILADO = "informe_compilado"
    INFORME_EMIS = "informe_emis"


class EstadoIngesta(StrEnum):
    PENDIENTE = "pendiente"
    PROCESADO = "procesado"
    ERROR = "error"


class FuenteTipo(StrEnum):
    WEB = "web"
    PDF = "pdf"
    OPENALEX = "openalex"
    ARXIV = "arxiv"
    CROSSREF = "crossref"
