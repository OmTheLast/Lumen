"""Planner that turns user requests into structured actions."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus

from lumen.agent.schemas import Action, Plan, ToolResult
from lumen.config import Config
from lumen.llm.ollama_client import OllamaClient, OllamaError


SYSTEM_PROMPT = """You are Lumen, a local macOS desktop agent.

Return only valid JSON in this exact shape:
{
  "response": "short natural language response",
  "actions": [
    {
      "tool": "tool_name",
      "args": {"name": "value"},
      "reason": "why this action is needed"
    }
  ]
}

Available tools:
- open_app(app_name): open a macOS application.
- open_url(url, browser): open a URL, optionally in a browser.
- web_search(query, browser, engine): search the web in a browser.
- browser_new_tab(url, browser): open a new browser tab, optionally with a URL.
- browser_close_tab(browser): close the active browser tab.
- browser_reload_tab(browser): reload the active browser tab.
- browser_switch_tab(direction, browser): switch to the next or previous tab.
- browser_active_tab(browser): report the active tab title and URL.
- screenshot(filename): take a screenshot.
- read_file(path): read a UTF-8 text file.
- write_file(path, content): write a UTF-8 text file.
- run_shell(command): run a shell command.

Prefer browser tools, open_app/open_url/web_search over run_shell.
Use the fewest actions needed.
If no tool is needed, return an empty actions array.
"""


class Planner:
    def __init__(self, config: Config, client: OllamaClient) -> None:
        self.config = config
        self.client = client
        self.history: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def plan(self, user_input: str) -> Plan:
        simple = self._simple_plan(user_input)
        if simple is not None:
            return simple

        self.history.append({"role": "user", "content": user_input})
        self._trim_history()

        try:
            content = self.client.chat(
                self.config.planner_model,
                self.history,
                json_mode=True,
            )
        except OllamaError as exc:
            return Plan(str(exc), [])

        plan = self._parse_plan(content)
        self.history.append({"role": "assistant", "content": json.dumps(self._plan_to_json(plan))})
        return plan

    def observe(self, action: Action, result: ToolResult) -> None:
        observation = {
            "tool": action.tool,
            "ok": result.ok,
            "observation": result.observation,
            "data": result.data or {},
        }
        self.history.append({"role": "assistant", "content": f"OBSERVATION: {json.dumps(observation)}"})
        self._trim_history()

    def final_response(self, user_input: str, observations: list[str]) -> str:
        if not observations:
            return ""

        messages = self.history + [
            {
                "role": "user",
                "content": (
                    "Summarize the completed action for the user in one short sentence. "
                    f"Original request: {user_input}\nObservations:\n" + "\n".join(observations)
                ),
            }
        ]
        try:
            return self.client.chat(self.config.router_model, messages, timeout=60)
        except OllamaError:
            return observations[-1]

    def _trim_history(self) -> None:
        non_system = self.history[1:]
        keep = self.config.max_history_turns * 2
        if len(non_system) > keep:
            self.history = [self.history[0], *non_system[-keep:]]

    def _parse_plan(self, content: str) -> Plan:
        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                return Plan(content.strip(), [])
            try:
                raw = json.loads(match.group(0))
            except json.JSONDecodeError:
                return Plan(content.strip(), [])

        if not isinstance(raw, dict):
            return Plan(str(raw), [])

        response = raw.get("response")
        actions_raw = raw.get("actions")
        actions: list[Action] = []
        if isinstance(actions_raw, list):
            for item in actions_raw:
                action = self._parse_action(item)
                if action is not None:
                    actions.append(action)

        return Plan(response if isinstance(response, str) else "", actions)

    def _parse_action(self, item: Any) -> Action | None:
        if not isinstance(item, dict):
            return None
        tool = item.get("tool")
        args = item.get("args")
        reason = item.get("reason")
        if not isinstance(tool, str) or not isinstance(args, dict):
            return None
        return Action(tool=tool, args=args, reason=reason if isinstance(reason, str) else "")

    def _plan_to_json(self, plan: Plan) -> dict[str, Any]:
        return {
            "response": plan.response,
            "actions": [
                {"tool": action.tool, "args": action.args, "reason": action.reason}
                for action in plan.actions
            ],
        }

    def _simple_plan(self, text: str) -> Plan | None:
        lowered = text.strip().lower()
        if not lowered:
            return Plan("", [])

        youtube_match = re.fullmatch(
            r"(?:open\s+)?(?:youtube|you\s*tube)(?:\s+and)?\s+search(?:\s+for)?\s+(.+)",
            text.strip(),
            re.IGNORECASE,
        )
        if youtube_match:
            query = youtube_match.group(1).strip()
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            return Plan(
                response=f"Searching YouTube for {query}.",
                actions=[
                    Action(
                        tool="open_url",
                        args={"url": url, "browser": self.config.default_browser},
                        reason="The user asked to search YouTube.",
                    )
                ],
            )

        youtube_open = re.fullmatch(r"(?:open|launch|start)\s+(?:youtube|you\s*tube)", text.strip(), re.IGNORECASE)
        if youtube_open:
            return Plan(
                response="Opening YouTube.",
                actions=[
                    Action(
                        tool="open_url",
                        args={"url": "https://www.youtube.com", "browser": self.config.default_browser},
                        reason="The user asked to open YouTube.",
                    )
                ],
            )

        new_tab_match = re.fullmatch(
            r"(?:open\s+)?(?:a\s+)?new\s+(?:(safari|chrome|google chrome|firefox|arc|brave|edge)\s+)?tab(?:\s+(?:with|to|at)\s+(.+))?",
            text.strip(),
            re.IGNORECASE,
        )
        if new_tab_match:
            browser = self._normalize_browser(new_tab_match.group(1) or self.config.default_browser)
            url = (new_tab_match.group(2) or "").strip()
            return Plan(
                response="Opening a new tab.",
                actions=[
                    Action(
                        tool="browser_new_tab",
                        args={"browser": browser, "url": url},
                        reason="The user asked to open a new browser tab.",
                    )
                ],
            )

        close_tab_match = re.fullmatch(
            r"(?:close|remove)\s+(?:the\s+)?(?:(safari|chrome|google chrome|firefox|arc|brave|edge)\s+)?(?:current\s+|active\s+)?tab",
            text.strip(),
            re.IGNORECASE,
        )
        if close_tab_match:
            browser = self._normalize_browser(close_tab_match.group(1) or self.config.default_browser)
            return Plan(
                response="Closing the active tab.",
                actions=[
                    Action(
                        tool="browser_close_tab",
                        args={"browser": browser},
                        reason="The user asked to close the active browser tab.",
                    )
                ],
            )

        reload_tab_match = re.fullmatch(
            r"(?:reload|refresh)\s+(?:the\s+)?(?:(safari|chrome|google chrome|firefox|arc|brave|edge)\s+)?(?:current\s+|active\s+)?tab",
            text.strip(),
            re.IGNORECASE,
        )
        if reload_tab_match:
            browser = self._normalize_browser(reload_tab_match.group(1) or self.config.default_browser)
            return Plan(
                response="Reloading the active tab.",
                actions=[
                    Action(
                        tool="browser_reload_tab",
                        args={"browser": browser},
                        reason="The user asked to reload the active browser tab.",
                    )
                ],
            )

        switch_tab_match = re.fullmatch(
            r"(?:go\s+to\s+|switch\s+to\s+)?(?:the\s+)?(next|previous|prev|left|right)\s+(?:(safari|chrome|google chrome|firefox|arc|brave|edge)\s+)?tab",
            text.strip(),
            re.IGNORECASE,
        )
        if switch_tab_match:
            direction = switch_tab_match.group(1).lower()
            if direction == "right":
                direction = "next"
            elif direction == "left":
                direction = "previous"
            browser = self._normalize_browser(switch_tab_match.group(2) or self.config.default_browser)
            return Plan(
                response=f"Switching to the {direction} tab.",
                actions=[
                    Action(
                        tool="browser_switch_tab",
                        args={"browser": browser, "direction": direction},
                        reason="The user asked to switch browser tabs.",
                    )
                ],
            )

        active_tab_match = re.fullmatch(
            r"(?:what|which)\s+(?:(safari|chrome|google chrome|firefox|arc|brave|edge)\s+)?tab\s+(?:am\s+i\s+on|is\s+open)|(?:show|tell\s+me)\s+(?:the\s+)?(?:current|active)\s+(?:(safari|chrome|google chrome|firefox|arc|brave|edge)\s+)?tab",
            text.strip(),
            re.IGNORECASE,
        )
        if active_tab_match:
            browser = self._normalize_browser(
                next((group for group in active_tab_match.groups() if group), self.config.default_browser)
            )
            return Plan(
                response="Checking the active tab.",
                actions=[
                    Action(
                        tool="browser_active_tab",
                        args={"browser": browser},
                        reason="The user asked which browser tab is active.",
                    )
                ],
            )

        app_match = re.fullmatch(r"(open|launch|start)\s+(.+)", text.strip(), re.IGNORECASE)
        if app_match:
            app_name = app_match.group(2).strip()
            if not self._looks_like_search(app_name):
                return Plan(
                    response=f"Opening {app_name}.",
                    actions=[
                        Action(
                            tool="open_app",
                            args={"app_name": app_name},
                            reason=f"The user asked to open {app_name}.",
                        )
                    ],
                )

        browser_search = re.fullmatch(
            r"(?:open\s+)?(safari|chrome|google chrome|firefox|arc|brave)(?:\s+and)?\s+search(?:\s+the\s+web)?\s+(?:for\s+)?(.+)",
            text.strip(),
            re.IGNORECASE,
        )
        if browser_search:
            browser = self._normalize_browser(browser_search.group(1))
            query = browser_search.group(2).strip()
            return Plan(
                response=f"Searching for {query}.",
                actions=[
                    Action(
                        tool="web_search",
                        args={"query": query, "browser": browser, "engine": "google"},
                        reason="The user asked to search the web in a specific browser.",
                    )
                ],
            )

        search_match = re.fullmatch(
            r"(?:search|google|look up|search the web)(?:\s+for)?\s+(.+)",
            text.strip(),
            re.IGNORECASE,
        )
        if search_match:
            query = search_match.group(1).strip()
            return Plan(
                response=f"Searching for {query}.",
                actions=[
                    Action(
                        tool="web_search",
                        args={"query": query, "browser": self.config.default_browser, "engine": "google"},
                        reason="The user asked to search the web.",
                    )
                ],
            )

        screenshot_match = re.fullmatch(
            r"(?:take|capture|grab)\s+(?:a\s+)?screenshot(?:\s+(?:called|named|as)\s+(.+))?",
            text.strip(),
            re.IGNORECASE,
        )
        if screenshot_match:
            filename = (screenshot_match.group(1) or "lumen-screenshot").strip()
            return Plan(
                response=f"Taking a screenshot called {filename}.",
                actions=[
                    Action(
                        tool="screenshot",
                        args={"filename": filename},
                        reason="The user asked to capture the screen.",
                    )
                ],
            )

        return None

    def _looks_like_search(self, value: str) -> bool:
        lowered = value.lower()
        return " search " in f" {lowered} " or lowered.startswith("search ")

    def _normalize_browser(self, browser: str) -> str:
        normalized = browser.strip().lower()
        if normalized == "chrome":
            return "Google Chrome"
        if normalized == "brave":
            return "Brave Browser"
        return browser.strip().title()
