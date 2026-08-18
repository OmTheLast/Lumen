from lumen.config import save_user_config
from lumen.config import Config
from lumen.models import discover_models


def test_save_user_config_merges_values(tmp_path):
    path = tmp_path / "config.json"

    save_user_config({"planner_model": "qwen3:test"}, path)
    save_user_config({"router_model": "qwen3:fast"}, path)

    assert "qwen3:test" in path.read_text(encoding="utf-8")
    assert "qwen3:fast" in path.read_text(encoding="utf-8")


def test_discover_models_includes_configured_models(monkeypatch):
    monkeypatch.setattr("lumen.models._discover_ollama", lambda _url: [])
    monkeypatch.setattr("lumen.models._discover_openai_compatible", lambda _url, _provider: [])
    config = Config(planner_model="planner:test", router_model="router:test", voice_stt_model="whisper:test")

    payload = discover_models(config)
    ids = {model["id"] for model in payload["models"]}

    assert {"planner:test", "router:test", "whisper:test"}.issubset(ids)


def test_discover_models_resolves_missing_chat_model(monkeypatch):
    from lumen.models import ModelOption

    monkeypatch.setattr(
        "lumen.models._discover_ollama",
        lambda _url: [ModelOption("qwen3:latest", "ollama", "chat", "qwen3:latest")],
    )
    monkeypatch.setattr("lumen.models._discover_openai_compatible", lambda _url, _provider: [])
    config = Config(planner_model="deleted:test", router_model="qwen3:latest", voice_stt_model="whisper:test")

    payload = discover_models(config)

    assert payload["settings"]["planner_model"] == "deleted:test"
    assert payload["resolved_settings"]["planner_model"] == "qwen3:latest"
    assert payload["unavailable_settings"]["planner_model"] == "deleted:test"
    assert payload["diagnostics"]["ollama_model_count"] == 1
