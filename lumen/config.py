"""Runtime configuration for Lumen."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import json
from typing import Any


CONFIG_PATH = Path(os.path.expanduser(os.getenv("LUMEN_CONFIG_PATH", "~/.lumen/config.json")))


MODEL_SETTING_KEYS = {
    "planner_model",
    "router_model",
    "voice_stt_model",
}


def _read_user_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_user_config(values: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    existing = _read_user_config(path)
    existing.update({key: value for key, value in values.items() if value is not None})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _configured_value(key: str, env_name: str, default: str) -> str:
    if env_name in os.environ:
        return os.environ[env_name]
    value = _read_user_config().get(key)
    return value if isinstance(value, str) and value.strip() else default


@dataclass
class Config:
    ollama_url: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    planner_model: str = _configured_value("planner_model", "LUMEN_PLANNER_MODEL", "qwen3.6:27b")
    router_model: str = _configured_value("router_model", "LUMEN_ROUTER_MODEL", "qwen3:latest")
    max_history_turns: int = int(os.getenv("LUMEN_MAX_HISTORY_TURNS", "12"))
    default_browser: str = os.getenv("LUMEN_DEFAULT_BROWSER", "Safari")
    screenshot_dir: str = os.path.expanduser(
        os.getenv("LUMEN_SCREENSHOT_DIR", "~/Documents/lumen/screenshots")
    )
    ui_enabled: bool = os.getenv("LUMEN_UI_ENABLED", "1") != "0"
    ui_host: str = os.getenv("LUMEN_UI_HOST", "127.0.0.1")
    ui_port: int = int(os.getenv("LUMEN_UI_PORT", "8765"))
    ui_open_browser: bool = os.getenv("LUMEN_UI_OPEN_BROWSER", "1") != "0"
    overlay_enabled: bool = os.getenv("LUMEN_OVERLAY_ENABLED", "1") != "0"
    overlay_size: int = int(os.getenv("LUMEN_OVERLAY_SIZE", "136"))
    voice_stt_model: str = _configured_value(
        "voice_stt_model",
        "LUMEN_VOICE_STT_MODEL",
        "mlx-community/whisper-tiny",
    )
    voice_auto_max_seconds: float = float(os.getenv("LUMEN_VOICE_AUTO_MAX_SECONDS", "12"))
    voice_silence_seconds: float = float(os.getenv("LUMEN_VOICE_SILENCE_SECONDS", "0.8"))
    voice_silence_threshold: float = float(os.getenv("LUMEN_VOICE_SILENCE_THRESHOLD", "0.012"))

    def model_settings(self) -> dict[str, str]:
        return {
            "planner_model": self.planner_model,
            "router_model": self.router_model,
            "voice_stt_model": self.voice_stt_model,
        }

    def update_model_settings(self, values: dict[str, Any]) -> dict[str, str]:
        updates: dict[str, str] = {}
        for key in MODEL_SETTING_KEYS:
            value = values.get(key)
            if isinstance(value, str) and value.strip():
                updates[key] = value.strip()
        for key, value in updates.items():
            setattr(self, key, value)
        if updates:
            save_user_config(updates)
        return self.model_settings()
