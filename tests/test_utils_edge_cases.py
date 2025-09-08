import io
import os
import pytest
from pathlib import Path

from blackbox_hybrid_tool.utils.patcher import apply_patch_to_text
from blackbox_hybrid_tool.utils import self_repo as sr
from blackbox_hybrid_tool.utils.web import WebSearch


def test_apply_patch_to_text_context_mismatch_raises():
    original = ["a", "b"]
    # hunk expects 'x' which doesn't match
    from blackbox_hybrid_tool.utils.patcher import Hunk
    h = Hunk(src_start=1, src_len=1, dst_start=1, dst_len=1, lines=[(' ', 'x')])
    with pytest.raises(ValueError):
        apply_patch_to_text(original, [h])


def test_extract_snapshot_raises_without_embed(tmp_path, monkeypatch):
    # Point EMBED_MODULE to a non-existent file to trigger error
    fake = tmp_path / "no_payload.py"
    monkeypatch.setattr(sr, "EMBED_MODULE", fake)
    with pytest.raises(FileNotFoundError):
        sr.extract_snapshot(tmp_path / "out")


def test_websearch_serpapi_missing_key_raises(monkeypatch):
    os.environ.pop("SERPAPI_KEY", None)
    ws = WebSearch(engine="serpapi")
    with pytest.raises(RuntimeError):
        ws.search("q")


def test_websearch_tavily_missing_key_raises(monkeypatch):
    os.environ.pop("TAVILY_API_KEY", None)
    ws = WebSearch(engine="tavily")
    with pytest.raises(RuntimeError):
        ws.search("q")

