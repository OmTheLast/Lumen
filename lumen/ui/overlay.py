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
        self.nodes = self._build_nodes()

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
        radius = min(self.width, self.height) * 0.31
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

        projected = self._project_nodes(cx, cy, outer)
        edges: list[tuple[dict[str, float], dict[str, float], float]] = []
        for i, a in enumerate(projected):
            for b in projected[i + 1 :]:
                same_ring = a["ring"] == b["ring"] and abs(a["index"] - b["index"]) <= 1
                dist = math.dist((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"]))
                if same_ring or dist < 0.42:
                    edges.append((a, b, (a["rz"] + b["rz"]) / 2))
        edges.sort(key=lambda edge: edge[2])
        for a, b, z in edges[:210]:
            shade = self._shade(color, max(0.18, min(0.72, (z + 1.25) / 2.7)))
            self.canvas.create_line(a["px"], a["py"], b["px"], b["py"], fill=shade, width=1)

        self._draw_projected_ring(cx, cy, outer, color, 0.74, "xy")
        self._draw_projected_ring(cx, cy, outer, color, 0.48, "xz")
        self._draw_core(cx, cy, outer, color)

        for point in sorted(projected, key=lambda item: item["rz"]):
            alpha = max(0.26, min(1.0, (point["rz"] + 1.2) / 2.2))
            shade = self._shade(color, alpha)
            r = 1.2 + point["depth"] * 0.9
            self.canvas.create_oval(point["px"] - r, point["py"] - r, point["px"] + r, point["py"] + r, fill=shade, outline="")

    def _draw_status_tick(self, color: str, label: str) -> None:
        cx = self.width - 25
        cy = self.height - 25
        self.canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, fill="#170803", outline="#5f2c0d", width=1)
        self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=color, outline="")

    def _build_nodes(self) -> list[dict[str, float]]:
        nodes: list[dict[str, float]] = []
        for lat in range(-60, 61, 30):
            phi = math.radians(lat)
            ring_count = round(14 * math.cos(phi)) + 7
            for index in range(ring_count):
                theta = (index / ring_count) * math.pi * 2
                nodes.append(
                    {
                        "x": math.cos(phi) * math.cos(theta),
                        "y": math.sin(phi),
                        "z": math.cos(phi) * math.sin(theta),
                        "ring": float(lat),
                        "index": float(index),
                    }
                )
        for index in range(24):
            angle = index * 2.399963
            z = 1 - (2 * index + 1) / 24
            radius = math.sqrt(1 - z * z)
            nodes.append(
                {
                    "x": math.cos(angle) * radius,
                    "y": math.sin(angle) * radius,
                    "z": z,
                    "ring": 999.0,
                    "index": float(index),
                }
            )
        return nodes

    def _project_nodes(self, cx: float, cy: float, radius: float) -> list[dict[str, float]]:
        projected: list[dict[str, float]] = []
        for node in self.nodes:
            point = self._project_point(node, cx, cy, radius)
            projected.append(
                {
                    **node,
                    "px": point["px"],
                    "py": point["py"],
                    "rz": point["rz"],
                    "depth": point["depth"],
                }
            )
        return projected

    def _project_point(self, node: dict[str, float], cx: float, cy: float, radius: float) -> dict[str, float]:
        ay = self.frame * 0.038
        ax = math.sin(self.frame * 0.017) * 0.42 + 0.22
        az = math.cos(self.frame * 0.013) * 0.16
        focal = 2.35
        x = node["x"]
        y = node["y"]
        z = node["z"]
        cos_y = math.cos(ay)
        sin_y = math.sin(ay)
        x, z = x * cos_y - z * sin_y, x * sin_y + z * cos_y
        cos_x = math.cos(ax)
        sin_x = math.sin(ax)
        y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x
        cos_z = math.cos(az)
        sin_z = math.sin(az)
        x, y = x * cos_z - y * sin_z, x * sin_z + y * cos_z
        depth = focal / (focal - z)
        return {"px": cx + x * radius * depth, "py": cy + y * radius * depth, "rz": z, "depth": depth}

    def _draw_projected_ring(self, cx: float, cy: float, radius: float, color: str, scale: float, plane: str) -> None:
        points: list[dict[str, float]] = []
        for index in range(73):
            angle = (index / 72) * math.pi * 2
            wobble = 0.04 * math.sin(angle * 3 + self.frame * 0.06)
            node = {"x": 0.0, "y": 0.0, "z": 0.0}
            if plane == "xy":
                node["x"] = math.cos(angle) * scale
                node["y"] = math.sin(angle) * scale * (0.7 + wobble)
                node["z"] = math.sin(angle * 2 + self.frame * 0.04) * 0.08
            else:
                node["x"] = math.cos(angle) * scale
                node["y"] = math.sin(angle * 2 + self.frame * 0.03) * 0.08
                node["z"] = math.sin(angle) * scale * (0.64 + wobble)
            points.append(self._project_point(node, cx, cy, radius))
        for start, end in zip(points, points[1:]):
            shade = self._shade(color, max(0.24, min(0.78, (start["rz"] + end["rz"] + 2.0) / 4.8)))
            self.canvas.create_line(start["px"], start["py"], end["px"], end["py"], fill=shade, width=1)

    def _draw_core(self, cx: float, cy: float, radius: float, color: str) -> None:
        orbit = {
            "x": math.sin(self.frame * 0.092) * 0.16 + 0.06,
            "y": math.cos(self.frame * 0.111) * 0.11,
            "z": math.sin(self.frame * 0.133) * 0.18,
        }
        core = self._project_point(orbit, cx, cy, radius)
        glow = 9 * core["depth"]
        self.canvas.create_oval(
            core["px"] - glow * 2.4,
            core["py"] - glow * 2.4,
            core["px"] + glow * 2.4,
            core["py"] + glow * 2.4,
            fill=self._shade(color, 0.35),
            outline="",
        )
        self.canvas.create_oval(
            core["px"] - glow,
            core["py"] - glow,
            core["px"] + glow,
            core["py"] + glow,
            fill=color,
            outline="#ffd89a",
            width=1,
        )
        for index in range(5):
            angle = self.frame * 0.16 + index * 1.26
            node = {
                "x": orbit["x"] + math.cos(angle) * 0.09,
                "y": orbit["y"] + math.sin(angle * 1.2) * 0.07,
                "z": orbit["z"] + math.sin(angle) * 0.08,
            }
            point = self._project_point(node, cx, cy, radius)
            self.canvas.create_line(core["px"], core["py"], point["px"], point["py"], fill=self._shade(color, 0.5), width=1)
            self.canvas.create_oval(point["px"] - 1.7, point["py"] - 1.7, point["px"] + 1.7, point["py"] + 1.7, fill="#ffd89a", outline="")

    def _shade(self, color: str, alpha: float) -> str:
        color = color.lstrip("#")
        red = int(color[0:2], 16)
        green = int(color[2:4], 16)
        blue = int(color[4:6], 16)
        mix = max(0.0, min(1.0, alpha))
        red = int(red * mix)
        green = int(green * mix)
        blue = int(blue * mix)
        return f"#{red:02x}{green:02x}{blue:02x}"


if __name__ == "__main__":
    raise SystemExit(main())
