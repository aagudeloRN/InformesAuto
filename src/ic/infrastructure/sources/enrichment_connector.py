"""Conector de fuentes secundarias para enriquecimiento de evidencia (Spec 008 / US2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.config import Settings

logger = logging.getLogger("enrichment_connector")


@dataclass
class FragmentoEnriquecido:
    """Chunk de texto obtenido de fuente secundaria para enriquecimiento del índice."""

    texto: str
    titulo: str
    autores: str | None
    año: str
    url: str | None
    fuente: str  # "openalex" o "web_enrichment"
    sector_gics: str
    idioma: str


class EnrichmentConnector:
    """Conector unificado de enriquecimiento secundario (OpenAlex + Web Fallback)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.openalex = OpenAlexConnector(settings)
        self.web = WebConnector(settings)

    def fetch_fragments(
        self, query: str, sector_gics: str, max_results: int = 5
    ) -> list[FragmentoEnriquecido]:
        """Recupera fragmentos desde OpenAlex, con fallback a WebSearch (si < 2 resultados)."""
        fragmentos: list[FragmentoEnriquecido] = []

        try:
            results_openalex = self.openalex.search(query, max_results=max_results)
            for res in results_openalex:
                fragmentos.extend(
                    self._to_fragmentos(res, fuente="openalex", sector_gics=sector_gics)
                )
        except Exception as exc:
            logger.warning("Error al consultar OpenAlex: %s", exc)

        if len(fragmentos) < 2:
            try:
                results_web = self.web.search(query, max_results=max_results)
                for res in results_web:
                    fragmentos.extend(
                        self._to_fragmentos(res, fuente="web_enrichment", sector_gics=sector_gics)
                    )
            except Exception as exc:
                logger.warning("Error al consultar Web Search fallback: %s", exc)

        return fragmentos

    def _to_fragmentos(self, res, fuente: str, sector_gics: str) -> list[FragmentoEnriquecido]:
        texto = res.content or res.snippet or res.title
        if not texto or len(texto.strip()) < 30:
            return []

        meta = res.metadatos or {}
        titulo = res.title or meta.get("titulo") or "Sin título"
        autores = meta.get("autor")
        año = str(meta.get("año") or "s.f.")
        url = res.url or meta.get("doi")
        idioma = meta.get("idioma") or getattr(res, "idioma", None) or "es"

        parrafos = [p.strip() for p in texto.split("\n\n") if len(p.strip()) >= 30]
        if not parrafos:
            parrafos = [texto.strip()]

        chunks = []
        for p in parrafos:
            chunks.append(
                FragmentoEnriquecido(
                    texto=p[:2000],
                    titulo=titulo,
                    autores=autores,
                    año=año,
                    url=url,
                    fuente=fuente,
                    sector_gics=sector_gics,
                    idioma=idioma,
                )
            )
        return chunks
