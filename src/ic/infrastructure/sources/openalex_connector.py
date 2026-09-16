"""Conector para la API pública de OpenAlex.

OpenAlex no requiere API key. Proporcionar `mailto` en los parámetros
identifica al cliente y lo pone en el "polite pool" (mayor rate limit).
Docs: https://docs.openalex.org/
"""

from datetime import date

import httpx

from ic.shared.config import Settings
from ic.shared.types import WebResult

_BASE_URL = "https://api.openalex.org"


def _build_metadatos(work: dict, acceso: str) -> dict:
    """Extrae campos APA-relevantes de un objeto Work de OpenAlex."""
    authors = work.get("authorships", [])
    autor = None
    if authors:
        display = authors[0].get("author", {}).get("display_name", "")
        if display:
            # Apellido, Inicial — formato APA base
            partes = display.rsplit(" ", 1)
            if len(partes) == 2:
                autor = f"{partes[1]}, {partes[0][0]}."
            else:
                autor = display

    source = (work.get("primary_location") or {}).get("source") or {}
    fuente_nombre = source.get("display_name") or "OpenAlex"
    doi = work.get("doi")

    return {
        "titulo": work.get("title") or "Sin título",
        "fuente_nombre": fuente_nombre,
        "año": str(work.get("publication_year") or "s.f."),
        "fecha_acceso": acceso,
        "autor": autor,
        "doi": doi,
        "openalex_id": work.get("id"),
        "cited_by_count": work.get("cited_by_count", 0),
    }


class OpenAlexConnector:
    """Wrapper sobre la REST API de OpenAlex."""

    def __init__(self, settings: Settings) -> None:
        self._email = settings.openalex_email
        self._headers = {"User-Agent": f"InformesAuto/0.5 (mailto:{self._email or 'anon'})"}

    def search(self, query: str, max_results: int = 5) -> list[WebResult]:
        """Busca trabajos académicos en OpenAlex.

        Retorna lista de WebResult con metadatos APA completos.
        Devuelve lista vacía si el servicio no está disponible.
        """
        params: dict[str, str | int] = {
            "search": query,
            "per-page": max_results,
            "sort": "cited_by_count:desc",
            "select": "id,title,doi,publication_year,cited_by_count,authorships,primary_location",
        }
        if self._email:
            params["mailto"] = self._email

        try:
            resp = httpx.get(
                f"{_BASE_URL}/works",
                params=params,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return []

        acceso = date.today().isoformat()
        results: list[WebResult] = []
        for work in resp.json().get("results", []):
            metadatos = _build_metadatos(work, acceso)
            doi = work.get("doi") or ""
            url = doi if doi else work.get("id", "")
            titulo = metadatos["titulo"]
            año = metadatos["año"]
            fuente = metadatos["fuente_nombre"]
            abstract = work.get("abstract_inverted_index")
            content = _reconstruct_abstract(abstract) if abstract else f"{titulo} ({fuente}, {año})"

            results.append(
                WebResult(
                    url=url,
                    title=titulo,
                    content=content,
                    snippet=content[:300],
                    metadatos=metadatos,
                )
            )
        return results


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruye el abstract desde el índice invertido de OpenAlex."""
    if not inverted_index:
        return ""
    max_pos = max(pos for positions in inverted_index.values() for pos in positions)
    words: list[str] = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(w for w in words if w)
