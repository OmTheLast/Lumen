"""Shell tool."""

from __future__ import annotations

import subprocess

from lumen.agent.schemas import ToolResult


def run_shell(command: str) -> ToolResult:
    command = command.strip()
    if not command:
        return ToolResult(False, "No shell command provided.")

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return ToolResult(False, "Command timed out after 30 seconds.")
    except OSError as exc:
        return ToolResult(False, f"Command failed: {exc}")

    output = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        return ToolResult(False, output or f"Command exited with code {result.returncode}.")
    return ToolResult(True, output or "Command completed with no output.")

