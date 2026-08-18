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
    size: int | None = None
    modified_at: str = ""
    digest: str = ""


def discover_models(config: Config) -> dict[str, Any]:
    options: list[ModelOption] = []
    providers: dict[str, str] = {}

    ollama_models = _discover_ollama(config.ollama_url)
    providers["ollama"] = "online" if ollama_models else "unavailable"
    options.extend(ollama_models)

    lm_studio_models = _discover_openai_compatible("http://localhost:1234/v1/models", "lm_studio")
    providers["lm_studio"] = "online" if lm_studio_models else "unavailable"
    options.extend(lm_studio_models)

    detected_ids = {option.id for option in options if option.available}
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
    settings = config.model_settings()
    resolved_settings = _resolve_settings(settings, options)
    unavailable_settings = {
        key: value
        for key, value in settings.items()
        if value and value not in detected_ids and "whisper" not in value.lower()
    }
    return {
        "settings": settings,
        "resolved_settings": resolved_settings,
        "unavailable_settings": unavailable_settings,
        "models": [asdict(option) for option in options],
        "providers": providers,
        "diagnostics": {
            "ollama_url": config.ollama_url,
            "ollama_model_count": len(ollama_models),
            "lm_studio_model_count": len(lm_studio_models),
            "detected_chat_models": sorted(option.id for option in options if option.available and option.kind == "chat"),
        },
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
            details = model.get("details") if isinstance(model.get("details"), dict) else {}
            parameter_size = details.get("parameter_size") if isinstance(details, dict) else None
            quantization = details.get("quantization_level") if isinstance(details, dict) else None
            suffix_parts = [part for part in [parameter_size, quantization] if isinstance(part, str) and part]
            label = name.strip()
            if suffix_parts:
                label = f"{label} ({', '.join(suffix_parts)})"
            options.append(
                ModelOption(
                    name.strip(),
                    "ollama",
                    "chat",
                    label,
                    size=model.get("size") if isinstance(model.get("size"), int) else None,
                    modified_at=model.get("modified_at") if isinstance(model.get("modified_at"), str) else "",
                    digest=model.get("digest") if isinstance(model.get("digest"), str) else "",
                )
            )
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


def _resolve_settings(settings: dict[str, str], options: list[ModelOption]) -> dict[str, str]:
    available_chat = [option.id for option in options if option.available and option.kind == "chat"]
    available_stt = [option.id for option in options if option.kind == "speech_to_text"]

    return {
        "planner_model": _resolve_model(settings.get("planner_model", ""), available_chat),
        "router_model": _resolve_model(settings.get("router_model", ""), available_chat),
        "voice_stt_model": _resolve_model(settings.get("voice_stt_model", ""), available_stt),
    }


def _resolve_model(selected: str, available: list[str]) -> str:
    if selected in available:
        return selected
    if not available:
        return selected
    preferred = [
        "qwen3:latest",
        "qwen3.6:27b",
        "qwen3.5:27b-q4_k_m",
        "qwen2.5:7b",
    ]
    for model_id in preferred:
        if model_id in available:
            return model_id
    return available[0]
