import os
from unittest.mock import Mock, patch

import pytest

from blackbox_hybrid_tool.utils.web import strip_html, WebFetcher, WebSearch
from blackbox_hybrid_tool.utils.github_client import GitHubClient


def test_strip_html_basic():
    html = "<html><head><style>p{}</style><script>1</script></head><body><p>Hi</p></body></html>"
    assert strip_html(html) == "Hi"


def test_webfetcher_fetch_success(monkeypatch):
    class R:
        status_code = 200
        headers = {"content-type": "text/html"}
        text = "<h1>hello</h1>"
        def raise_for_status(self):
            return None
    monkeypatch.setattr("blackbox_hybrid_tool.utils.web.requests.get", lambda url, timeout=15: R())
    wf = WebFetcher(timeout=1)
    data = wf.fetch("http://x")
    assert data["status"] == 200 and "hello" in data["text_stripped"].lower()


def test_websearch_serpapi_success(monkeypatch):
    os.environ["SERPAPI_KEY"] = "k"
    os.environ.pop("TAVILY_API_KEY", None)
    class R:
        def raise_for_status(self):
            return None
        def json(self):
            return {"organic_results": [{"title": "t", "link": "u", "snippet": "s"}]}
    with patch("blackbox_hybrid_tool.utils.web.requests.get", return_value=R()):
        ws = WebSearch(engine="serpapi")
        out = ws.search("q", num_results=1)
        assert out["engine"] == "serpapi" and len(out["results"]) == 1


def test_websearch_tavily_success(monkeypatch):
    os.environ["TAVILY_API_KEY"] = "k"
    os.environ.pop("SERPAPI_KEY", None)
    class R:
        def raise_for_status(self):
            return None
        def json(self):
            return {"results": [{"title": "t", "url": "u", "content": "s"}]}
    with patch("blackbox_hybrid_tool.utils.web.requests.post", return_value=R()):
        ws = WebSearch(engine="tavily")
        out = ws.search("q", num_results=1)
        assert out["engine"] == "tavily" and len(out["results"]) == 1


def test_websearch_requires_engine(monkeypatch):
    os.environ.pop("SERPAPI_KEY", None)
    os.environ.pop("TAVILY_API_KEY", None)
    ws = WebSearch(engine=None)
    with pytest.raises(RuntimeError):
        ws.search("q")


def test_github_client_headers_and_calls(monkeypatch):
    os.environ["GH_TOKEN"] = "t"
    client = GitHubClient()
    assert "Authorization" in client.headers
    class R:
        def raise_for_status(self):
            return None
        def json(self):
            return {"ok": True}
    # get_user
    with patch("blackbox_hybrid_tool.utils.github_client.requests.get", return_value=R()):
        assert client.get_user().get("ok") is True
    # create_gist
    with patch("blackbox_hybrid_tool.utils.github_client.requests.post", return_value=R()):
        assert client.create_gist({"a.txt": "x"}).get("ok") is True


def test_github_client_requires_token(monkeypatch):
    os.environ.pop("GH_TOKEN", None)
    os.environ.pop("GITHUB_TOKEN", None)
    with pytest.raises(ValueError):
        GitHubClient()

