import re
from datetime import date
from urllib.parse import urlparse

import httpx
from ddgs import DDGS

from ic.shared.config import Settings
from ic.shared.types import WebResult

_CIIU_RE = re.compile(r"CIIU[:\s]*(\d{4,6})", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return url


def _extract_year(text: str) -> str | None:
    m = _YEAR_RE.search(text)
    return m.group(0) if m else None


def _build_metadatos(url: str, title: str, content: str) -> dict:
    return {
        "titulo": title or "Sin título",
        "fuente_nombre": _extract_domain(url),
        "año": _extract_year(content) or "s.f.",
        "fecha_acceso": date.today().isoformat(),
        "autor": None,
    }


class WebConnector:
    def __init__(self, settings: Settings) -> None:
        self._tavily_key = settings.tavily_api_key
        self._use_tavily = bool(self._tavily_key)

    def search(
        self, query: str, max_results: int = 5, force_ddg: bool = False
    ) -> list[WebResult]:
        """Busca en la web. force_ddg=True omite Tavily aunque esté configurado
        (útil en tests para no gastar créditos del free tier)."""
        if self._use_tavily and not force_ddg:
            return self._search_tavily(query, max_results)
        return self._search_ddg(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[WebResult]:
        payload = {
            "api_key": self._tavily_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        resp = httpx.post("https://api.tavily.com/search", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", []):
            url = item.get("url", "")
            title = item.get("title", "")
            content = item.get("content", "")
            results.append(
                WebResult(
                    url=url,
                    title=title,
                    content=content,
                    snippet=content[:300],
                    metadatos=_build_metadatos(url, title, content),
                )
            )
        return results

    def _search_ddg(self, query: str, max_results: int) -> list[WebResult]:
        results = []
        for item in DDGS().text(query, max_results=max_results):
            url = item.get("href", "")
            title = item.get("title", "")
            content = item.get("body", "")
            results.append(
                WebResult(
                    url=url,
                    title=title,
                    content=content,
                    snippet=content[:300],
                    metadatos=_build_metadatos(url, title, content),
                )
            )
        return results

    def extract_ciiu(self, results: list[WebResult]) -> str | None:
        for r in results:
            for text in (r.title, r.snippet, r.content):
                m = _CIIU_RE.search(text)
                if m:
                    return m.group(1)
        return None
