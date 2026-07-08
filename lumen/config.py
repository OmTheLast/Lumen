"""Runtime configuration for Lumen."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    ollama_url: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    planner_model: str = os.getenv("LUMEN_PLANNER_MODEL", "qwen3.6:27b")
    router_model: str = os.getenv("LUMEN_ROUTER_MODEL", "qwen3:latest")
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
    overlay_size: int = int(os.getenv("LUMEN_OVERLAY_SIZE", "172"))
    voice_stt_model: str = os.getenv("LUMEN_VOICE_STT_MODEL", "mlx-community/whisper-tiny")
    voice_auto_max_seconds: float = float(os.getenv("LUMEN_VOICE_AUTO_MAX_SECONDS", "12"))
    voice_silence_seconds: float = float(os.getenv("LUMEN_VOICE_SILENCE_SECONDS", "0.8"))
    voice_silence_threshold: float = float(os.getenv("LUMEN_VOICE_SILENCE_THRESHOLD", "0.012"))
