"""Local model discovery and settings payloads."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import requests

from lumen.config import Config


@dataclass(frozen=True)
class ModelOption:
    id: str
    provider: str
    kind: str
    label: str
    available: bool = True


def discover_models(config: Config) -> dict[str, Any]:
    options: list[ModelOption] = []
    providers: dict[str, str] = {}

    ollama_models = _discover_ollama(config.ollama_url)
    providers["ollama"] = "online" if ollama_models else "unavailable"
    options.extend(ollama_models)

    lm_studio_models = _discover_openai_compatible("http://localhost:1234/v1/models", "lm_studio")
    providers["lm_studio"] = "online" if lm_studio_models else "unavailable"
    options.extend(lm_studio_models)

    for model_id in {
        config.planner_model,
        config.router_model,
        config.voice_stt_model,
        "mlx-community/whisper-tiny",
        "mlx-community/whisper-small-mlx",
    }:
        if model_id and not any(option.id == model_id for option in options):
            provider = "mlx_whisper" if "whisper" in model_id.lower() else "configured"
            kind = "speech_to_text" if "whisper" in model_id.lower() else "chat"
            options.append(ModelOption(model_id, provider, kind, model_id, available=False))

    options.sort(key=lambda item: (item.kind, item.provider, item.label.lower()))
    return {
        "settings": config.model_settings(),
        "models": [asdict(option) for option in options],
        "providers": providers,
        "config_path": str(config_path()),
    }


def config_path() -> str:
    from lumen.config import CONFIG_PATH

    return str(CONFIG_PATH)


def _discover_ollama(base_url: str) -> list[ModelOption]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=0.7)
        response.raise_for_status()
    except requests.RequestException:
        return []
    payload = response.json()
    models = payload.get("models")
    if not isinstance(models, list):
        return []
    options: list[ModelOption] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("name")
        if isinstance(name, str) and name.strip():
            options.append(ModelOption(name.strip(), "ollama", "chat", name.strip()))
    return options


def _discover_openai_compatible(url: str, provider: str) -> list[ModelOption]:
    try:
        response = requests.get(url, timeout=0.5)
        response.raise_for_status()
    except requests.RequestException:
        return []
    payload = response.json()
    models = payload.get("data")
    if not isinstance(models, list):
        return []
    options: list[ModelOption] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id")
        if isinstance(model_id, str) and model_id.strip():
            options.append(ModelOption(model_id.strip(), provider, "chat", model_id.strip()))
    return options
