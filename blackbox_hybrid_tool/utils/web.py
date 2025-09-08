from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Optional

import requests


def strip_html(html: str) -> str:
    # Very naive HTML -> text
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class WebFetcher:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def fetch(self, url: str) -> Dict[str, Any]:
        r = requests.get(url, timeout=self.timeout)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        text = r.text if "text" in content_type or "html" in content_type else r.content.decode("utf-8", errors="ignore")
        return {
            "url": url,
            "status": r.status_code,
            "content_type": content_type,
            "text": text,
            "text_stripped": strip_html(text) if "html" in content_type.lower() else text,
        }


class WebSearch:
    """Pluggable web search. Requires API key depending on engine.

    Supported engines (via env):
    - SERPAPI (SERPAPI_KEY)
    - Tavily (TAVILY_API_KEY)
    Fallback: raises if not configured
    """

    def __init__(self, engine: Optional[str] = None, timeout: int = 20):
        self.engine = (engine or os.getenv("WEB_SEARCH_ENGINE") or "").lower()
        self.timeout = timeout

    def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        if self.engine in ("serpapi", "serp"):
            key = os.getenv("SERPAPI_KEY")
            if not key:
                raise RuntimeError("SERPAPI_KEY no configurada")
            params = {
                "engine": "google",
                "q": query,
                "api_key": key,
                "num": num_results,
            }
            r = requests.get("https://serpapi.com/search", params=params, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            out = []
            for item in (data.get("organic_results") or [])[:num_results]:
                out.append({"title": item.get("title"), "link": item.get("link"), "snippet": item.get("snippet")})
            return {"engine": "serpapi", "results": out}

        if self.engine in ("tavily",):
            key = os.getenv("TAVILY_API_KEY")
            if not key:
                raise RuntimeError("TAVILY_API_KEY no configurada")
            payload = {"query": query, "search_depth": "basic", "max_results": num_results}
            r = requests.post("https://api.tavily.com/search", json=payload, headers={"Authorization": key}, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            out = []
            for item in (data.get("results") or [])[:num_results]:
                out.append({"title": item.get("title"), "link": item.get("url"), "snippet": item.get("content")})
            return {"engine": "tavily", "results": out}

        raise RuntimeError("Motor de búsqueda no configurado. Usa SERPAPI_KEY o TAVILY_API_KEY.")

