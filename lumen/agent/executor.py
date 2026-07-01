"""Executes planned actions through the tool registry."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from lumen.agent.schemas import Action, ToolResult
from lumen.agent.safety import SafetyBroker
from lumen.tools import TOOLS


class Executor:
    def __init__(self, safety: SafetyBroker | None = None) -> None:
        self.safety = safety or SafetyBroker()

    def execute(self, action: Action) -> ToolResult:
        tool = TOOLS.get(action.tool)
        if tool is None:
            return ToolResult(False, f"Unknown tool: {action.tool}")

        decision = self.safety.assess(action)
        if not self.safety.confirm(action, decision):
            return ToolResult(False, f"Cancelled {action.tool}.")

        try:
            kwargs = self._filter_kwargs(tool, action.args)
            return tool(**kwargs)
        except TypeError as exc:
            return ToolResult(False, f"Invalid arguments for {action.tool}: {exc}")
        except Exception as exc:
            return ToolResult(False, f"Tool {action.tool} failed: {exc}")

    def _filter_kwargs(self, tool: Callable[..., ToolResult], args: dict[str, Any]) -> dict[str, Any]:
        signature = inspect.signature(tool)
        valid = set(signature.parameters)
        return {key: value for key, value in args.items() if key in valid}

