import re
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
    tipo_fuente: str | None = None


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
        tipo_fuente=meta.get("tipo_fuente"),
    )


def format_inline(meta: CitationMetadata) -> str:
    nombre = meta.autor or meta.fuente_nombre
    return f"({nombre}, {meta.año})"


def _is_person_author(autor: str) -> bool:
    """Heurística: autor es persona si contiene coma (Apellido, N.) o exactamente 2 palabras."""
    return "," in autor or (len(autor.split()) == 2 and autor[0].isupper())


def _apa_web(meta: CitationMetadata) -> str:
    """Formato APA 7 para fuentes web."""
    nombre = meta.autor or meta.fuente_nombre
    titulo_md = f"*{meta.titulo}*"
    sitio = meta.fuente_nombre if meta.autor else ""
    sitio_part = f" {sitio}." if sitio and sitio != nombre else "."
    if meta.url:
        if meta.fecha_acceso and meta.año == "s.f.":
            url_part = f" Recuperado el {meta.fecha_acceso} de {meta.url}"
        else:
            url_part = f" {meta.url}"
    else:
        url_part = ""
    return f"{nombre}. ({meta.año}). {titulo_md}{sitio_part}{url_part}"


def _apa_academic(meta: CitationMetadata) -> str:
    """Formato APA 7 para fuentes académicas (OpenAlex, artículos)."""
    nombre = meta.autor or meta.fuente_nombre
    titulo_md = f"*{meta.titulo}*"
    fuente_md = f"*{meta.fuente_nombre}*" if meta.fuente_nombre else ""
    fuente_part = f" {fuente_md}." if fuente_md and fuente_md != f"*{nombre}*" else "."
    url_part = f" {meta.url}" if meta.url else ""
    return f"{nombre}. ({meta.año}). {titulo_md}{fuente_part}{url_part}"


def _apa_report(meta: CitationMetadata) -> str:
    """Formato APA 7 para informes/reportes (PDF sectorial)."""
    nombre = meta.autor or meta.fuente_nombre
    titulo_md = f"*{meta.titulo}*"
    distinto = meta.fuente_nombre and meta.fuente_nombre != nombre
    fuente_part = f" {meta.fuente_nombre}." if distinto else "."
    url_part = f" {meta.url}" if meta.url else ""
    # Informes compilados de Ruta N: se aclara que agregan múltiples fuentes (ADR-012)
    etiqueta = (
        " [Informe compilado de múltiples fuentes]"
        if meta.tipo_fuente == "informe_compilado"
        else " [Informe]"
    )
    return f"{nombre}. ({meta.año}). {titulo_md}{etiqueta}.{fuente_part}{url_part}"


def format_reference(meta: CitationMetadata, fuente_tipo: str = "web") -> Referencia:
    nombre = meta.autor or meta.fuente_nombre
    clave = f"{nombre.replace(' ', '').replace(',', '')}{meta.año}"

    if fuente_tipo == "openalex":
        apa = _apa_academic(meta)
    elif fuente_tipo == "pdf":
        apa = _apa_report(meta)
    else:
        apa = _apa_web(meta)

    return Referencia(
        clave=clave,
        autor=nombre,
        año=meta.año,
        titulo=meta.titulo,
        fuente=meta.fuente_nombre,
        url=meta.url,
        apa_string=apa,
    )


def format_chunks_with_meta(chunks: list[ChunkResult]) -> str:
    """Formatea chunks incluyendo autor y año para que el LLM pueda citar inline."""
    parts = []
    for i, c in enumerate(chunks, 1):
        meta = extract_citation_metadata(c)
        src_label = f"{meta.autor or meta.fuente_nombre}, {meta.año}"
        url_part = f" — {c.fuente_url}" if c.fuente_url else ""
        parts.append(f"[{i}] {c.chunk_texto}\nFuente: {src_label}{url_part}")
    return "\n\n---\n\n".join(parts)


def find_orphan_citations(texto: str, refs: list[Referencia]) -> list[str]:
    """Devuelve citas (Autor, año) del texto que no coinciden con ninguna referencia."""
    pattern = re.compile(r"\(([^()]+),\s*(\d{4}|s\.f\.)\)")
    autores_refs = {r.autor.lower() for r in refs}
    orphans: list[str] = []
    for m in pattern.finditer(texto):
        autor_cita = m.group(1).strip().lower()
        if not any(autor_cita in a or a in autor_cita for a in autores_refs):
            orphans.append(m.group(0))
    return list(dict.fromkeys(orphans))


def build_references_section(chunks: list[ChunkResult]) -> list[Referencia]:
    seen_urls: set[str] = set()
    refs: list[Referencia] = []
    for chunk in chunks:
        url_key = chunk.fuente_url or chunk.chunk_texto[:80]
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)
        meta = extract_citation_metadata(chunk)
        tipo = chunk.fuente_tipo or "web"
        refs.append(format_reference(meta, fuente_tipo=tipo))
    refs.sort(key=lambda r: r.autor.lower())
    return refs
