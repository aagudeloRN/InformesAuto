from dataclasses import dataclass
from urllib.parse import urlparse

from ic.shared.types import ChunkResult, Referencia


@dataclass
class CitationMetadata:
    titulo: str
    fuente_nombre: str
    año: str
    autor: str | None
    url: str | None
    fecha_acceso: str | None


def _domain_from_url(url: str | None) -> str:
    if not url:
        return "Fuente desconocida"
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return url


def extract_citation_metadata(chunk: ChunkResult) -> CitationMetadata:
    meta = chunk.metadatos or {}
    return CitationMetadata(
        titulo=meta.get("titulo") or (chunk.chunk_texto[:60] + "…"),
        fuente_nombre=meta.get("fuente_nombre") or _domain_from_url(chunk.fuente_url),
        año=meta.get("año") or "s.f.",
        autor=meta.get("autor"),
        url=chunk.fuente_url,
        fecha_acceso=meta.get("fecha_acceso"),
    )


def format_inline(meta: CitationMetadata) -> str:
    nombre = meta.autor or meta.fuente_nombre
    return f"({nombre}, {meta.año})"


def format_reference(meta: CitationMetadata) -> Referencia:
    nombre = meta.autor or meta.fuente_nombre
    clave = f"{nombre.replace(' ', '')}{meta.año}"

    if meta.url:
        recuperado = f" Recuperado de {meta.url}"
        if meta.fecha_acceso:
            recuperado = f" Recuperado el {meta.fecha_acceso} de {meta.url}"
    else:
        recuperado = ""

    apa = f"{nombre}. ({meta.año}). {meta.titulo}.{recuperado}"

    return Referencia(
        clave=clave,
        autor=nombre,
        año=meta.año,
        titulo=meta.titulo,
        fuente=meta.fuente_nombre,
        url=meta.url,
        apa_string=apa,
    )


def build_references_section(chunks: list[ChunkResult]) -> list[Referencia]:
    seen_urls: set[str] = set()
    refs: list[Referencia] = []
    for chunk in chunks:
        url_key = chunk.fuente_url or chunk.chunk_texto[:80]
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)
        meta = extract_citation_metadata(chunk)
        refs.append(format_reference(meta))
    refs.sort(key=lambda r: r.autor.lower())
    return refs
