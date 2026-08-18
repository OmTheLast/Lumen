"""Native macOS app window for the local Lumen interface."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppWindowHandle:
    process: subprocess.Popen[bytes]


def start_app_window(*, url: str) -> AppWindowHandle | None:
    """Open the local Lumen UI in a native app window."""
    if platform.system() != "Darwin":
        return None

    binary = _ensure_window_binary()
    if binary is None:
        return None

    try:
        process = subprocess.Popen(
            [str(binary), "--url", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    return AppWindowHandle(process)


def _ensure_window_binary() -> Path | None:
    swiftc = shutil.which("swiftc")
    if swiftc is None:
        return None

    source = Path(__file__).with_name("macos_window.swift")
    if not source.exists():
        return None

    build_dir = source.parents[2] / "dist" / "helpers"
    binary = build_dir / "lumen-window"
    if binary.exists() and binary.stat().st_mtime >= source.stat().st_mtime:
        return binary

    build_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [swiftc, str(source), "-O", "-o", str(binary)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return binary
