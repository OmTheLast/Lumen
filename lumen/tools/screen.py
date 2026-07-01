"""Screen tools."""

from __future__ import annotations

import os
import subprocess

from lumen.agent.schemas import ToolResult
from lumen.config import Config


def screenshot(filename: str = "lumen-screenshot") -> ToolResult:
    config = Config()
    os.makedirs(config.screenshot_dir, exist_ok=True)
    clean_name = filename.strip() or "lumen-screenshot"
    if not clean_name.endswith(".png"):
        clean_name = f"{clean_name}.png"
    save_path = os.path.join(config.screenshot_dir, clean_name)

    try:
        subprocess.run(["screencapture", save_path], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return ToolResult(False, f"Could not take screenshot: {exc.stderr.strip()}")
    return ToolResult(True, f"Screenshot saved to {save_path}.", {"path": save_path})

