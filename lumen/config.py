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

