"""macOS app and browser tools."""

from __future__ import annotations

import subprocess
from urllib.parse import quote_plus

from lumen.agent.schemas import ToolResult


def open_app(app_name: str) -> ToolResult:
    app_name = app_name.strip().strip("\"'")
    if not app_name:
        return ToolResult(False, "No app name provided.")

    try:
        subprocess.run(["open", "-a", app_name], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return ToolResult(False, f"Could not open {app_name}: {exc.stderr.strip()}")
    return ToolResult(True, f"Opened {app_name}.", {"app": app_name})


def open_url(url: str, browser: str = "") -> ToolResult:
    url = url.strip()
    if not url:
        return ToolResult(False, "No URL provided.")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    cmd = ["open"]
    if browser.strip():
        cmd.extend(["-a", browser.strip()])
    cmd.append(url)

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return ToolResult(False, f"Could not open URL: {exc.stderr.strip()}")
    return ToolResult(True, f"Opened {url}.", {"url": url, "browser": browser.strip() or None})


def web_search(query: str, browser: str = "Safari", engine: str = "google") -> ToolResult:
    query = query.strip()
    if not query:
        return ToolResult(False, "No search query provided.")

    engine = engine.lower().strip()
    if engine == "duckduckgo":
        url = f"https://duckduckgo.com/?q={quote_plus(query)}"
    else:
        url = f"https://www.google.com/search?q={quote_plus(query)}"

    result = open_url(url, browser=browser)
    if not result.ok:
        return result
    return ToolResult(True, f"Searched {engine} for: {query}", {"query": query, "url": url, "browser": browser})

