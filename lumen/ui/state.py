"""Shared UI state for the local presence page."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass
class PresenceSnapshot:
    state: str = "idle"
    message: str = "Lumen is awake."
    detail: str = "Waiting for a command."
    transcript: str = ""
    updated_at: str = field(default_factory=lambda: _now())


class PresenceState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = PresenceSnapshot()

    def update(
        self,
        state: str,
        message: str,
        *,
        detail: str = "",
        transcript: str | None = None,
    ) -> None:
        with self._lock:
            self._snapshot.state = state
            self._snapshot.message = message
            self._snapshot.detail = detail
            if transcript is not None:
                self._snapshot.transcript = transcript
            self._snapshot.updated_at = _now()

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self._snapshot)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

