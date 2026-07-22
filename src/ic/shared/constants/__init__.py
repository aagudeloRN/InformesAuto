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
