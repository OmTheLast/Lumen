"""macOS app and browser tools."""

from __future__ import annotations

import json
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


def browser_new_tab(url: str = "", browser: str = "Safari") -> ToolResult:
    browser = _normalize_browser(browser)
    browser_literal = _applescript_string(browser)
    url = _normalize_url(url)
    url_literal = _applescript_string(url)
    if _is_chrome_family(browser):
        script = f"""
        tell application {browser_literal}
          activate
          if (count of windows) = 0 then make new window
          if {url_literal} is "" then
            make new tab at end of tabs of front window
          else
            make new tab at end of tabs of front window with properties {{URL:{url_literal}}}
          end if
          set active tab index of front window to count of tabs of front window
        end tell
        """
    else:
        script = f"""
        tell application {browser_literal}
          activate
          if (count of windows) = 0 then make new document
          if {url_literal} is "" then
            tell front window to make new tab at end of tabs
          else
            tell front window to make new tab at end of tabs with properties {{URL:{url_literal}}}
          end if
          set current tab of front window to last tab of front window
        end tell
        """
    result = _run_applescript(script)
    if not result.ok:
        return result
    detail = f" with {url}" if url else ""
    return ToolResult(True, f"Opened a new {browser} tab{detail}.", {"browser": browser, "url": url or None})


def browser_close_tab(browser: str = "Safari") -> ToolResult:
    browser = _normalize_browser(browser)
    browser_literal = _applescript_string(browser)
    if _is_chrome_family(browser):
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          close active tab of front window
        end tell
        """
    else:
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          close current tab of front window
        end tell
        """
    result = _run_applescript(script)
    if not result.ok:
        return result
    return ToolResult(True, f"Closed the active {browser} tab.", {"browser": browser})


def browser_reload_tab(browser: str = "Safari") -> ToolResult:
    browser = _normalize_browser(browser)
    browser_literal = _applescript_string(browser)
    if _is_chrome_family(browser):
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          reload active tab of front window
        end tell
        """
    else:
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          do JavaScript "window.location.reload()" in current tab of front window
        end tell
        """
    result = _run_applescript(script)
    if not result.ok:
        return result
    return ToolResult(True, f"Reloaded the active {browser} tab.", {"browser": browser})


def browser_switch_tab(direction: str = "next", browser: str = "Safari") -> ToolResult:
    browser = _normalize_browser(browser)
    browser_literal = _applescript_string(browser)
    direction = direction.strip().lower()
    offset = -1 if direction in {"previous", "prev", "left", "back"} else 1
    if _is_chrome_family(browser):
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          set tabCount to count of tabs of front window
          if tabCount = 0 then error "No browser tabs are open."
          set currentIndex to active tab index of front window
          set nextIndex to ((currentIndex - 1 + ({offset}) + tabCount) mod tabCount) + 1
          set active tab index of front window to nextIndex
          return title of active tab of front window
        end tell
        """
    else:
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          set tabCount to count of tabs of front window
          if tabCount = 0 then error "No browser tabs are open."
          set currentIndex to index of current tab of front window
          set nextIndex to ((currentIndex - 1 + ({offset}) + tabCount) mod tabCount) + 1
          set current tab of front window to tab nextIndex of front window
          return name of current tab of front window
        end tell
        """
    result = _run_applescript(script)
    if not result.ok:
        return result
    clean_direction = "previous" if offset < 0 else "next"
    return ToolResult(True, f"Switched to the {clean_direction} {browser} tab.", {"browser": browser, "title": result.data.get("output")})


def browser_active_tab(browser: str = "Safari") -> ToolResult:
    browser = _normalize_browser(browser)
    browser_literal = _applescript_string(browser)
    if _is_chrome_family(browser):
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          return (title of active tab of front window) & linefeed & (URL of active tab of front window)
        end tell
        """
    else:
        script = f"""
        tell application {browser_literal}
          if (count of windows) = 0 then error "No browser window is open."
          return (name of current tab of front window) & linefeed & (URL of current tab of front window)
        end tell
        """
    result = _run_applescript(script)
    if not result.ok:
        return result
    output = str(result.data.get("output") or "")
    title, _, url = output.partition("\n")
    return ToolResult(True, f"Active {browser} tab: {title or url}", {"browser": browser, "title": title, "url": url})


def _run_applescript(script: str) -> ToolResult:
    try:
        result = subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout).strip()
        return ToolResult(False, f"Browser control failed: {detail}")
    return ToolResult(True, "Browser control completed.", {"output": result.stdout.strip()})


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def _normalize_browser(browser: str) -> str:
    value = browser.strip().lower()
    if value in {"", "safari"}:
        return "Safari"
    if value in {"chrome", "google chrome"}:
        return "Google Chrome"
    if value == "brave":
        return "Brave Browser"
    if value == "edge":
        return "Microsoft Edge"
    return browser.strip()


def _is_chrome_family(browser: str) -> bool:
    return browser in {"Google Chrome", "Brave Browser", "Microsoft Edge"}


def _applescript_string(value: str) -> str:
    return json.dumps(value)
