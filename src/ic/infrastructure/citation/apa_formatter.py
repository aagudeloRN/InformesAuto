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
    """Formato APA 7 para informes/reportes (PDF sectorial).

    No expone rutas locales — solo URLs públicas (DT-033).
    """
    nombre = meta.autor or meta.fuente_nombre
    titulo_md = f"*{meta.titulo}*"
    distinto = meta.fuente_nombre and meta.fuente_nombre != nombre
    fuente_part = f" {meta.fuente_nombre}." if distinto else "."
    # Rutas locales de archivo no son citables públicamente; se omiten (DT-033)
    is_public_url = meta.url and meta.url.startswith("http")
    url_part = f" {meta.url}" if is_public_url else ""
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
    """Formatea chunks con autor/año para que el LLM cite (Autor, año) — nunca nombres de archivo.

    Los PDFs locales no exponen su ruta; solo autor e año. (DT-033)
    """
    parts = []
    for i, c in enumerate(chunks, 1):
        meta = extract_citation_metadata(c)
        src_label = f"{meta.autor or meta.fuente_nombre}, {meta.año}"
        # Rutas locales de PDFs no son URLs públicas; excluirlas para no exponer filenames
        is_local_pdf = (
            c.fuente_tipo == "pdf" and c.fuente_url and not c.fuente_url.startswith("http")
        )
        url_part = f" — {c.fuente_url}" if c.fuente_url and not is_local_pdf else ""
        parts.append(f"[{i}] {c.chunk_texto}\nFuente: {src_label}{url_part}")
    return "\n\n---\n\n".join(parts)


# Patrón de cita inline (Autor, año): grupo 1 = autor(es), grupo 2 = año o "s.f.".
_CITA_RE = re.compile(r"\(([^()]+),\s*(\d{4}|s\.f\.)\)")


def _cita_matches_ref(autor_cita: str, autores_refs: set[str]) -> bool:
    """True si el autor de la cita mapea a alguna referencia (coincidencia por subcadena)."""
    autor_cita = autor_cita.strip().lower()
    return any(autor_cita in a or a in autor_cita for a in autores_refs)


def find_orphan_citations(texto: str, refs: list[Referencia]) -> list[str]:
    """Devuelve citas (Autor, año) del texto que no coinciden con ninguna referencia."""
    autores_refs = {r.autor.lower() for r in refs}
    orphans = [
        m.group(0)
        for m in _CITA_RE.finditer(texto)
        if not _cita_matches_ref(m.group(1), autores_refs)
    ]
    return list(dict.fromkeys(orphans))


def strip_orphan_citations(texto: str, refs: list[Referencia]) -> tuple[str, int]:
    """Suprime del texto las citas (Autor, año) sin referencia que las respalde (DT-052).

    Quitar una atribución no sustentada es correcto por RN-001 (nunca inventar atribuciones):
    ante una cita huérfana, se elimina la cita, no se fabrica una fuente. Devuelve el texto
    saneado y cuántas citas se suprimieron. Limpia el espacio sobrante que deja la cita.
    """
    autores_refs = {r.autor.lower() for r in refs}
    n = 0

    def _sub(m: re.Match) -> str:
        nonlocal n
        if _cita_matches_ref(m.group(1), autores_refs):
            return m.group(0)
        n += 1
        return ""

    saneado = _CITA_RE.sub(_sub, texto)
    # Colapsa el doble espacio o el " ." que pueda quedar tras borrar la cita.
    saneado = re.sub(r" +([.,;:])", r"\1", saneado)
    saneado = re.sub(r"[ \t]{2,}", " ", saneado)
    return saneado, n


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
