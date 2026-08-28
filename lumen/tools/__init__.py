"""Tool registry."""

from __future__ import annotations

from lumen.tools.apps import browser_active_tab
from lumen.tools.apps import browser_close_tab
from lumen.tools.apps import browser_new_tab
from lumen.tools.apps import browser_reload_tab
from lumen.tools.apps import browser_switch_tab
from lumen.tools.apps import open_app, open_url, web_search
from lumen.tools.files import read_file, write_file
from lumen.tools.screen import screenshot
from lumen.tools.shell import run_shell


TOOLS = {
    "open_app": open_app,
    "open_url": open_url,
    "web_search": web_search,
    "browser_new_tab": browser_new_tab,
    "browser_close_tab": browser_close_tab,
    "browser_reload_tab": browser_reload_tab,
    "browser_switch_tab": browser_switch_tab,
    "browser_active_tab": browser_active_tab,
    "screenshot": screenshot,
    "read_file": read_file,
    "write_file": write_file,
    "run_shell": run_shell,
}
