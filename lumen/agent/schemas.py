"""Shared structured action schemas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Action:
    tool: str
    args: dict[str, Any]
    reason: str = ""


@dataclass(frozen=True)
class Plan:
    response: str
    actions: list[Action]


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    observation: str
    data: dict[str, Any] | None = None

