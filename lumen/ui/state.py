"""Shared UI state for the local presence page."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from queue import Empty, Queue
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


class ChatBridge:
    def __init__(self) -> None:
        self._lock = Lock()
        self._queue: Queue[str] = Queue()
        self._messages: list[dict[str, str]] = [
            {"role": "system", "text": "Local channel open.", "time": _clock_label()}
        ]

    def post_user_message(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        with self._lock:
            self._messages.append({"role": "user", "text": text, "time": _clock_label()})
        self._queue.put(text)

    def append_lumen_message(self, text: str) -> None:
        text = text.strip() or "Done."
        with self._lock:
            self._messages.append({"role": "lumen", "text": text, "time": _clock_label()})

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"messages": list(self._messages[-24:])}

    def get_next(self, timeout: float = 0.5) -> str | None:
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clock_label() -> str:
    return datetime.now().strftime("%H:%M")
