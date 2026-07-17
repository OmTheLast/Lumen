"""Native always-on-top Lumen orb overlay."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from dataclasses import dataclass
from typing import Any
from urllib.request import urlopen


@dataclass(frozen=True)
class OverlayHandle:
    process: subprocess.Popen[bytes]


def start_overlay(*, state_url: str, size: int = 136) -> OverlayHandle | None:
    """Start the native overlay as a helper process.

    On macOS, Tk/AppKit windows must be created on the main thread. Running the
    overlay in a helper process keeps Lumen's terminal loop responsive and avoids
    crashing the main process.
    """
    cmd = [
        sys.executable,
        "-m",
        "lumen.ui.overlay",
        "--state-url",
        state_url,
        "--size",
        str(max(96, size)),
    ]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        print(f"Overlay unavailable: {exc}")
        return None
    return OverlayHandle(process)


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    state_url = ""
    size = 136

    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--state-url" and index + 1 < len(argv):
            state_url = argv[index + 1]
            index += 2
            continue
        if arg == "--size" and index + 1 < len(argv):
            size = int(argv[index + 1])
            index += 2
            continue
        index += 1

    if not state_url:
        print("Missing --state-url")
        return 2
    _run_overlay(state_url, max(96, size))
    return 0


def _run_overlay(state_url: str, size: int) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.title("Lumen")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.96)
    except tk.TclError:
        pass

    width = size
    height = size
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = max(0, screen_w - width - 22)
    y = max(0, screen_h - height - 58)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.configure(bg="#090402")

    canvas = tk.Canvas(root, width=width, height=height, highlightthickness=0, bg="#090402")
    canvas.pack(fill="both", expand=True)

    renderer = _OverlayRenderer(canvas, state_url, width, height)
    renderer.tick()
    root.mainloop()


class _OverlayRenderer:
    colors = {
        "idle": "#ff9a35",
        "listening": "#ffc15c",
        "thinking": "#ff8f2d",
        "acting": "#ff6f1f",
        "speaking": "#ffd17c",
        "error": "#ff665f",
    }

    labels = {
        "idle": ("Idle", "Waiting"),
        "listening": ("Listening", "Recording"),
        "thinking": ("Thinking", "Planning"),
        "acting": ("Acting", "Using tools"),
        "speaking": ("Speaking", "Responding"),
        "error": ("Attention", "Check terminal"),
        "offline": ("Offline", "Reconnecting"),
    }

    def __init__(self, canvas: Any, state_url: str, width: int, height: int) -> None:
        self.canvas = canvas
        self.state_url = state_url
        self.width = width
        self.height = height
        self.frame = 0
        self.last_state: dict[str, Any] = {"state": "idle"}

    def tick(self) -> None:
        snapshot = self._fetch_state()
        mode = str(snapshot.get("state") or "idle")
        color = self.colors.get(mode, self.colors["idle"])
        label, _ = self.labels.get(mode, self.labels["idle"])

        self.canvas.delete("all")
        self._draw_orb(color, mode)
        self._draw_status_tick(color, label)
        self.frame += 1
        self.canvas.after(80, self.tick)

    def _fetch_state(self) -> dict[str, Any]:
        try:
            with urlopen(self.state_url, timeout=0.25) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                self.last_state = payload
                return payload
        except Exception:
            self.last_state = {"state": "offline"}
        return self.last_state

    def _draw_orb(self, color: str, mode: str) -> None:
        cx = self.width // 2
        cy = self.height // 2
        radius = min(self.width, self.height) * 0.34
        pulse = 1 + 0.045 * math.sin(self.frame / 3)
        if mode == "idle":
            pulse = 1

        outer = radius * pulse
        self.canvas.create_oval(
            cx - outer - 13,
            cy - outer - 13,
            cx + outer + 13,
            cy + outer + 13,
            outline="#301405",
            width=1,
            fill="#0b0401",
        )
        for index, angle in enumerate(range(0, 360, 18)):
            theta = math.radians(angle + self.frame * 1.7)
            inner = outer * (0.76 if index % 2 else 0.86)
            x1 = cx + math.cos(theta) * inner
            y1 = cy + math.sin(theta) * inner
            x2 = cx + math.cos(theta) * (outer + 8)
            y2 = cy + math.sin(theta) * (outer + 8)
            self.canvas.create_line(x1, y1, x2, y2, fill=color if index % 3 == 0 else "#6a2d0b", width=1)

        self.canvas.create_oval(
            cx - outer,
            cy - outer,
            cx + outer,
            cy + outer,
            outline=color,
            width=2,
            fill="#1a0802",
        )
        self.canvas.create_oval(
            cx - outer * 0.74,
            cy - outer * 0.74,
            cx + outer * 0.74,
            cy + outer * 0.74,
            outline="#7d3b11",
            width=1,
        )
        self.canvas.create_oval(
            cx - outer * 0.48,
            cy - outer * 0.48,
            cx + outer * 0.48,
            cy + outer * 0.48,
            outline="#a65318",
            width=1,
        )
        self.canvas.create_oval(
            cx - 11,
            cy - 11,
            cx + 11,
            cy + 11,
            fill=color,
            outline="#ffd89a",
            width=1,
        )

        angle = self.frame / 8
        for offset in (0, 1.31, 2.73, 4.19):
            x1 = cx + math.cos(angle + offset) * 6
            y1 = cy + math.sin(angle + offset) * 7
            x2 = cx + math.cos(angle + offset) * (outer * 0.78)
            y2 = cy + math.sin(angle + offset) * (outer * 0.78)
            self.canvas.create_line(x1, y1, x2, y2, fill="#ffb14a", width=1)

        for offset in (0.4, 2.5, 4.8):
            sx = cx + math.cos(angle * 0.9 + offset) * outer * 0.62
            sy = cy + math.sin(angle * 1.1 + offset) * outer * 0.62
            self.canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="#ffd788", outline="")

    def _draw_status_tick(self, color: str, label: str) -> None:
        cx = self.width - 25
        cy = self.height - 25
        self.canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, fill="#170803", outline="#5f2c0d", width=1)
        self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=color, outline="")


if __name__ == "__main__":
    raise SystemExit(main())
