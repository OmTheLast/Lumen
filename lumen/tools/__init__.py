"""Tool registry."""

from __future__ import annotations

from lumen.tools.apps import open_app, open_url, web_search
from lumen.tools.files import read_file, write_file
from lumen.tools.screen import screenshot
from lumen.tools.shell import run_shell


TOOLS = {
    "open_app": open_app,
    "open_url": open_url,
    "web_search": web_search,
    "screenshot": screenshot,
    "read_file": read_file,
    "write_file": write_file,
    "run_shell": run_shell,
}

