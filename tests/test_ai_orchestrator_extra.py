import os
import pytest
import requests
from pathlib import Path

from blackbox_hybrid_tool.core.ai_client import AIOrchestrator
from blackbox_hybrid_tool.core.ai_client import BlackboxClient


def test_import_available_models_from_csv(tmp_path, monkeypatch):
    # Prepare CSV
    csv_path = tmp_path / "models.csv"
    csv_path.write_text(
        "Modelo,Contexto,Costo de Entrada ($/M tokens),Costo de Salida ($/M tokens)\n"
        "o3,128k,5,15\n",
        encoding="utf-8",
    )
    # Prepare orchestrator with temp config file to avoid writing into repo
    cfg_path = tmp_path / "models.json"
    cfg_path.write_text(
        '{"default_model":"auto","models":{"blackbox":{"api_key":"k","model":"blackboxai/openai/o1","enabled":true}}}',
        encoding="utf-8",
    )
    o = AIOrchestrator(config_file=str(cfg_path))
    n = o.import_available_models_from_csv(str(csv_path))
    assert n == 1
    # ensure config file was updated
    saved = cfg_path.read_text(encoding="utf-8")
    assert "available_models" in saved


def test_ensure_best_model_prefers_non_gemini(tmp_path):
    cfg_path = tmp_path / "models.json"
    import json
    cfg_path.write_text(
        json.dumps(
            {
                "default_model": "auto",
                "models": {"blackbox": {"api_key": "k", "model": "blackboxai/openai/o1", "enabled": True}},
                "available_models": [
                    {"model": "blackboxai/google/gemini-1.5-pro"},
                    {"model": "o1"},
                    {"model": "gpt-4o-mini"},
                ],
            }
        ),
        encoding="utf-8",
    )
    o = AIOrchestrator(config_file=str(cfg_path))
    # After init, _ensure_best_model has run; ensure model avoids gemini and picks one available
    m = o.models_config["models"]["blackbox"]["model"]
    assert m in ("o1", "gpt-4o-mini")


def test_orchestrator_get_client_errors_and_override(tmp_path, monkeypatch):
    # Base config file
    import json
    cfg_path = tmp_path / "models.json"
    cfg_path.write_text(
        json.dumps(
            {
                "default_model": "auto",
                "models": {"blackbox": {"api_key": "k", "model": "blackboxai/openai/o1", "enabled": True}},
            }
        ),
        encoding="utf-8",
    )
    o = AIOrchestrator(config_file=str(cfg_path))
    # Override path (contains slash) should pass through to client with model kwarg
    class FakeClient:
        def __init__(self):
            self.called = False
            self.kw = None
        def generate_response(self, prompt, **kw):
            self.called = True
            self.kw = kw
            return "r"
    fake = FakeClient()
    o.get_client = lambda mt=None: fake  # type: ignore
    out = o.generate_response("p", model_type="blackboxai/openai/o1")
    assert out == "r" and fake.called and fake.kw.get("model").endswith("/o1")
    # Missing api_key
    o2 = AIOrchestrator(config_file=str(cfg_path))
    o2.models_config["models"]["blackbox"]["api_key"] = ""
    with pytest.raises(ValueError):
        o2.get_client()
    # Disabled model
    o3 = AIOrchestrator(config_file=str(cfg_path))
    o3.models_config["models"]["blackbox"]["enabled"] = False
    with pytest.raises(ValueError):
        o3.get_client()
    # switch_model invalid
    with pytest.raises(ValueError):
        o.switch_model("does-not-exist")


def test_blackbox_client_debug_and_error(monkeypatch):
    bc = BlackboxClient("sk", {"model": "blackbox"})
    # success with debug True
    class R:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}
    monkeypatch.setattr("blackbox_hybrid_tool.core.ai_client.requests.post", lambda *a, **k: R())
    assert bc.generate_response("p", debug=True) == "ok"
    # error path with RequestException and detail
    class E(Exception):
        pass
    class BadReq(requests.RequestException):
        pass
    class RB:
        text = "detail"
    def boom(*a, **k):
        ex = BadReq("bad")
        ex.response = RB()  # type: ignore
        raise ex
    monkeypatch.setattr("blackbox_hybrid_tool.core.ai_client.requests.post", boom)
    out = bc.generate_response("p", debug=True)
    assert "Error en la API" in out


def test_blackbox_client_debug_json_dump_fallback(monkeypatch):
    # Force json.dumps in debug printing to fail to hit Raw Response branch
    class Unserializable:
        pass
    class R:
        status_code = 200
        text = "raw"
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [{"message": {"content": "ok"}}], "bad": Unserializable()}
    bc = BlackboxClient("sk", {"model": "blackbox"})
    monkeypatch.setattr("blackbox_hybrid_tool.core.ai_client.requests.post", lambda *a, **k: R())
    assert bc.generate_response("p", debug=True) == "ok"


def test_orchestrator_init_catches_best_model_errors(tmp_path, monkeypatch):
    import json
    cfg_path = tmp_path / "models.json"
    cfg_path.write_text(json.dumps({"default_model":"auto","models":{"blackbox": {"api_key":"k","model":"blackbox","enabled": True}}}), encoding="utf-8")
    # Patch _ensure_best_model to raise to cover except path
    orig = AIOrchestrator._ensure_best_model
    AIOrchestrator._ensure_best_model = lambda self: (_ for _ in ()).throw(RuntimeError("x"))  # type: ignore
    try:
        o = AIOrchestrator(config_file=str(cfg_path))
        assert o.models_config["models"]["blackbox"]["enabled"] is True
    finally:
        AIOrchestrator._ensure_best_model = orig  # type: ignore


def test_orchestrator_env_overrides(tmp_path, monkeypatch):
    import json
    cfg_path = tmp_path / "models.json"
    cfg_path.write_text(json.dumps({"default_model":"auto","models":{"blackbox": {"api_key":"","model":"blackbox","enabled": True}}}), encoding="utf-8")
    # BLACKBOX_API_KEY takes precedence
    monkeypatch.setenv("BLACKBOX_API_KEY", "bb")
    o = AIOrchestrator(config_file=str(cfg_path))
    assert o.models_config["models"]["blackbox"]["api_key"] == "bb"
    # API_KEY fallback when BLACKBOX_API_KEY missing
    monkeypatch.delenv("BLACKBOX_API_KEY", raising=False)
    monkeypatch.setenv("API_KEY", "generic")
    o2 = AIOrchestrator(config_file=str(cfg_path))
    assert o2.models_config["models"]["blackbox"]["api_key"] == "generic"


def test_get_client_with_other_key_branch(tmp_path):
    import json
    cfg_path = tmp_path / "models.json"
    cfg_path.write_text(json.dumps({"default_model":"auto","models":{"blackbox": {"api_key":"k","model":"blackbox","enabled": True}}}), encoding="utf-8")
    o = AIOrchestrator(config_file=str(cfg_path))
    c = o.get_client("other")
    from blackbox_hybrid_tool.core.ai_client import BlackboxClient as BBC
    assert isinstance(c, BBC)


def test_import_csv_exception_path(monkeypatch, tmp_path):
    import csv, json
    cfg_path = tmp_path / "models.json"
    cfg_path.write_text(json.dumps({"default_model":"auto","models":{"blackbox": {"api_key":"k","model":"blackbox","enabled": True}}}), encoding="utf-8")
    o = AIOrchestrator(config_file=str(cfg_path))
    class BadReader:
        def __iter__(self):
            raise RuntimeError("boom")
    monkeypatch.setattr("blackbox_hybrid_tool.core.ai_client.csv.DictReader", lambda f: BadReader())
    assert o.import_available_models_from_csv(str(tmp_path/"x.csv")) == 0


def test_load_config_defaults_when_missing(tmp_path, monkeypatch):
    # Point to non-existent config file to trigger default config branch
    o = AIOrchestrator(config_file=str(tmp_path / "nope.json"))
    cfg = o.models_config
    assert cfg.get("models", {}).get("blackbox", {}).get("enabled") is True
    # Import CSV missing file returns 0
    assert o.import_available_models_from_csv(str(tmp_path / "nope.csv")) == 0
