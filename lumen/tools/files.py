"""File tools."""

from __future__ import annotations

import os

from lumen.agent.schemas import ToolResult


def read_file(path: str) -> ToolResult:
    path = os.path.expanduser(path.strip())
    try:
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        return ToolResult(False, f"File not found: {path}")
    except PermissionError:
        return ToolResult(False, f"Permission denied: {path}")
    except OSError as exc:
        return ToolResult(False, f"Could not read {path}: {exc}")
    return ToolResult(True, content, {"path": path})


def write_file(path: str, content: str) -> ToolResult:
    path = os.path.expanduser(path.strip())
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
    except OSError as exc:
        return ToolResult(False, f"Could not write {path}: {exc}")
    return ToolResult(True, f"Wrote {len(content)} characters to {path}.", {"path": path})

