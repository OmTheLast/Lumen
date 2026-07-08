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


def start_overlay(*, state_url: str, size: int = 172) -> OverlayHandle | None:
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
        str(max(132, size)),
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
    size = 172

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
    _run_overlay(state_url, max(132, size))
    return 0


def _run_overlay(state_url: str, size: int) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.title("Lumen")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.94)
    except tk.TclError:
        pass

    width = size
    height = max(96, int(size * 0.58))
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
        label, hint = self.labels.get(mode, self.labels["idle"])

        self.canvas.delete("all")
        self._draw_panel(color)
        self._draw_orb(color, mode)
        self._draw_text(label, hint)
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

    def _draw_panel(self, color: str) -> None:
        w, h = self.width, self.height
        self.canvas.create_rectangle(1, 1, w - 2, h - 2, fill="#120703", outline="#5f2c0d", width=1)
        self.canvas.create_rectangle(4, 4, w - 5, h - 5, outline="#2b1408", width=1)
        self.canvas.create_line(12, h - 12, w - 12, h - 12, fill="#3d1b09")
        self.canvas.create_line(12, 12, 58, 12, fill=color, width=1)
        self.canvas.create_line(w - 58, 12, w - 12, 12, fill=color, width=1)

    def _draw_orb(self, color: str, mode: str) -> None:
        cx = 43
        cy = self.height // 2
        radius = 25
        pulse = 1 + 0.06 * math.sin(self.frame / 3)
        if mode == "idle":
            pulse = 1

        outer = radius * pulse
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
            cx - 9,
            cy - 9,
            cx + 9,
            cy + 9,
            fill=color,
            outline="#ffd89a",
            width=1,
        )

        angle = self.frame / 8
        for offset in (0, 2.1, 4.2):
            x1 = cx + math.cos(angle + offset) * 8
            y1 = cy + math.sin(angle + offset) * 20
            x2 = cx + math.cos(angle + offset + math.pi) * 22
            y2 = cy + math.sin(angle + offset + math.pi) * 7
            self.canvas.create_line(x1, y1, x2, y2, fill="#6f350f", width=1)

        bar_scale = 0.5 if mode == "idle" else 0.8 + 0.45 * math.sin(self.frame / 2)
        for index, x in enumerate((cx - 8, cx, cx + 8)):
            bar_h = (10 + index * 4) * bar_scale
            self.canvas.create_rectangle(
                x - 2,
                cy + 17 - bar_h,
                x + 2,
                cy + 17,
                fill="#190902",
                outline="",
            )

    def _draw_text(self, label: str, hint: str) -> None:
        x = 82
        y = self.height // 2 - 12
        self.canvas.create_text(x, y, anchor="w", text=label, fill="#fff1d8", font=("Helvetica", 15, "bold"))
        self.canvas.create_text(x, y + 22, anchor="w", text=hint, fill="#d39a60", font=("Helvetica", 12))


if __name__ == "__main__":
    raise SystemExit(main())
