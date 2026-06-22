import re

import httpx
from ddgs import DDGS

from ic.shared.config import Settings
from ic.shared.types import WebResult

_CIIU_RE = re.compile(r"CIIU[:\s]*(\d{4,6})", re.IGNORECASE)


class WebConnector:
    def __init__(self, settings: Settings) -> None:
        self._tavily_key = settings.tavily_api_key
        self._use_tavily = bool(self._tavily_key)

    def search(self, query: str, max_results: int = 5) -> list[WebResult]:
        if self._use_tavily:
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
            results.append(
                WebResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    snippet=item.get("content", "")[:300],
                )
            )
        return results

    def _search_ddg(self, query: str, max_results: int) -> list[WebResult]:
        results = []
        for item in DDGS().text(query, max_results=max_results):
            results.append(
                WebResult(
                    url=item.get("href", ""),
                    title=item.get("title", ""),
                    content=item.get("body", ""),
                    snippet=item.get("body", "")[:300],
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
