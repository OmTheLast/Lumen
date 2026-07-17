"""Dependency-free local web UI server."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any
from urllib.parse import urlparse
import webbrowser

from lumen.ui.state import PresenceState


class PresenceServer:
    def __init__(self, state: PresenceState, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.state = state
        self.host = host
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self, *, open_browser: bool = True) -> str:
        handler = self._make_handler()
        last_error: OSError | None = None
        for candidate in range(self.port, self.port + 20):
            try:
                self._server = ThreadingHTTPServer((self.host, candidate), handler)
                self.port = candidate
                break
            except OSError as exc:
                last_error = exc
        else:
            raise RuntimeError(f"Could not start Lumen UI: {last_error}")

        self._thread = threading.Thread(target=self._server.serve_forever, name="lumen-ui", daemon=True)
        self._thread.start()
        if open_browser:
            webbrowser.open(self.url)
        return self.url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        presence = self.state

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                route = urlparse(self.path).path
                if route == "/":
                    self._send_text(INDEX_HTML, "text/html; charset=utf-8")
                    return
                if route == "/styles.css":
                    self._send_text(STYLES_CSS, "text/css; charset=utf-8")
                    return
                if route == "/app.js":
                    self._send_text(APP_JS, "application/javascript; charset=utf-8")
                    return
                if route == "/state":
                    self._send_json(presence.as_dict())
                    return
                self.send_error(404)

            def log_message(self, format: str, *args: Any) -> None:
                return

            def _send_text(self, body: str, content_type: str) -> None:
                encoded = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _send_json(self, payload: dict[str, Any]) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return Handler


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lumen</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main class="console">
    <section class="framework" aria-label="Lumen status framework">
      <div class="hud hud-top"></div>
      <div class="hud hud-right"></div>
      <div class="hud hud-bottom"></div>
      <div class="scope" aria-hidden="true">
        <div class="sphere">
          <span class="axis axis-a"></span>
          <span class="axis axis-b"></span>
          <span class="axis axis-c"></span>
          <span class="arc arc-a"></span>
          <span class="arc arc-b"></span>
          <span class="arc arc-c"></span>
          <span class="arc arc-d"></span>
          <span class="filament filament-a"></span>
          <span class="filament filament-b"></span>
          <span class="filament filament-c"></span>
          <span class="filament filament-d"></span>
          <span class="spark spark-a"></span>
          <span class="spark spark-b"></span>
          <span class="spark spark-c"></span>
          <span class="spark spark-d"></span>
          <span class="nucleus"></span>
        </div>
      </div>
      <div class="readout readout-left">
        <span>local agent</span>
        <strong>Lumen</strong>
      </div>
      <div class="readout readout-right">
        <span>state</span>
        <strong id="stateReadout">Idle</strong>
      </div>
      <div class="status-panel">
        <p class="eyebrow">local desktop agent</p>
        <h1>Lumen</h1>
        <p id="message" class="message">Lumen is awake.</p>
        <p id="detail" class="detail">Waiting for a command.</p>
      </div>
      <div class="transcript-panel">
        <p class="label">last heard</p>
        <p id="transcript" class="transcript">Nothing yet.</p>
      </div>
    </section>
  </main>
  <aside id="presence" class="presence idle" aria-live="polite">
    <div class="presence-orb">
      <span></span><span></span><span></span>
    </div>
    <div class="presence-copy">
      <strong id="stateLabel">Idle</strong>
      <small id="stateHint">Waiting</small>
    </div>
  </aside>
  <script src="/app.js"></script>
</body>
</html>
"""


STYLES_CSS = """:root {
  color-scheme: dark;
  --bg: #050403;
  --text: #fff2df;
  --muted: #b99470;
  --line: rgba(255, 148, 58, 0.24);
  --orange: #ff8f2d;
  --amber: #ffc35b;
  --ember: #ff5d1f;
  --deep: #120905;
  --red: #ff665f;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at 50% 47%, rgba(255, 149, 42, 0.16), transparent 32%),
    linear-gradient(90deg, rgba(255, 139, 36, 0.06) 1px, transparent 1px),
    linear-gradient(0deg, rgba(255, 139, 36, 0.05) 1px, transparent 1px),
    linear-gradient(145deg, #030201 0%, #0d0704 52%, #030201 100%);
  background-size: auto, 58px 58px, 58px 58px, auto;
  color: var(--text);
  overflow: hidden;
}

.console {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 34px;
}

.framework {
  position: relative;
  width: min(900px, calc(100vw - 48px));
  aspect-ratio: 1 / 0.78;
  min-height: 540px;
  border: 1px solid rgba(255, 143, 45, 0.28);
  background:
    linear-gradient(90deg, transparent 0 7%, rgba(255, 143, 45, 0.08) 7% 7.25%, transparent 7.25% 92.75%, rgba(255, 143, 45, 0.08) 92.75% 93%, transparent 93%),
    linear-gradient(0deg, transparent 0 10%, rgba(255, 143, 45, 0.08) 10% 10.35%, transparent 10.35% 89.65%, rgba(255, 143, 45, 0.08) 89.65% 90%, transparent 90%),
    radial-gradient(circle at 50% 47%, rgba(255, 139, 36, 0.12), rgba(8, 4, 2, 0.92) 54%, rgba(3, 2, 1, 0.96));
  box-shadow: inset 0 0 80px rgba(255, 94, 24, 0.08), 0 24px 80px rgba(0, 0, 0, 0.46);
  overflow: hidden;
}

.framework::before,
.framework::after {
  content: "";
  position: absolute;
  pointer-events: none;
}

.framework::before {
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(255, 172, 83, 0.06) 0 1px,
    transparent 1px 5px
  );
  mix-blend-mode: screen;
  opacity: 0.32;
  animation: scanlines 7s linear infinite;
}

.framework::after {
  inset: 18px;
  border: 1px solid rgba(255, 143, 45, 0.18);
  clip-path: polygon(0 0, 34% 0, 34% 2px, 66% 2px, 66% 0, 100% 0, 100% 100%, 70% 100%, 70% calc(100% - 2px), 30% calc(100% - 2px), 30% 100%, 0 100%);
}

.hud {
  position: absolute;
  background: linear-gradient(90deg, transparent, rgba(255, 166, 66, 0.86), transparent);
  opacity: 0.72;
}

.hud-top {
  top: 38px;
  left: 48px;
  width: 58%;
  height: 3px;
  animation: hudShift 5s ease-in-out infinite;
}

.hud-right {
  top: 92px;
  right: 36px;
  width: 3px;
  height: 58%;
  background: linear-gradient(0deg, transparent, rgba(255, 166, 66, 0.86), transparent);
  animation: hudShiftVertical 4.5s ease-in-out infinite;
}

.hud-bottom {
  bottom: 42px;
  right: 72px;
  width: 48%;
  height: 3px;
  animation: hudShift 6.5s ease-in-out infinite reverse;
}

.scope {
  position: absolute;
  inset: 70px 78px 92px;
  display: grid;
  place-items: center;
}

.sphere {
  position: relative;
  width: min(470px, 58vw);
  aspect-ratio: 1;
  border-radius: 50%;
  border: 1px solid rgba(255, 164, 64, 0.32);
  background:
    repeating-conic-gradient(from 18deg, rgba(255, 171, 72, 0.2) 0 2deg, transparent 2deg 7deg),
    radial-gradient(circle at 50% 50%, rgba(255, 194, 88, 0.22), transparent 9%),
    radial-gradient(circle at 44% 48%, rgba(255, 112, 29, 0.24), transparent 28%),
    radial-gradient(circle, transparent 54%, rgba(255, 131, 35, 0.13) 55%, transparent 71%);
  box-shadow: inset 0 0 64px rgba(255, 102, 25, 0.18), 0 0 74px rgba(255, 115, 24, 0.22);
  animation: spherePulse 4.4s ease-in-out infinite;
  isolation: isolate;
}

.sphere::before,
.sphere::after {
  content: "";
  position: absolute;
  inset: 8%;
  border-radius: 50%;
  border: 1px solid rgba(255, 181, 78, 0.22);
}

.sphere::before {
  transform: rotateX(68deg);
  animation: rotateSlow 9s linear infinite;
}

.sphere::after {
  inset: 17%;
  transform: rotateY(66deg);
  animation: rotateSlow 7s linear infinite reverse;
}

.axis,
.arc,
.filament,
.spark,
.nucleus {
  position: absolute;
  display: block;
  border-radius: 999px;
  pointer-events: none;
}

.axis {
  left: 12%;
  right: 12%;
  top: 50%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 185, 81, 0.88), transparent);
  transform-origin: center;
}

.axis-a { transform: rotate(12deg); }
.axis-b { transform: rotate(58deg); opacity: 0.62; }
.axis-c { transform: rotate(-34deg); opacity: 0.46; }

.arc {
  inset: 10%;
  border: 1px solid transparent;
  border-top-color: rgba(255, 205, 96, 0.9);
  border-right-color: rgba(255, 108, 26, 0.42);
  animation: orbit 6.6s linear infinite;
}

.arc-b {
  inset: 19%;
  border-top-color: rgba(255, 133, 33, 0.8);
  animation-duration: 4.9s;
  animation-direction: reverse;
}

.arc-c {
  inset: 31%;
  border-top-color: rgba(255, 235, 154, 0.72);
  animation-duration: 3.7s;
}

.arc-d {
  inset: 4%;
  border-left-color: rgba(255, 141, 37, 0.48);
  border-bottom-color: rgba(255, 198, 90, 0.28);
  transform: rotate(-18deg);
  animation-duration: 10.4s;
}

.filament {
  left: 50%;
  top: 50%;
  width: 42%;
  height: 1px;
  transform-origin: 0 50%;
  background: linear-gradient(90deg, rgba(255, 245, 183, 0.9), rgba(255, 138, 42, 0.48), transparent);
  filter: drop-shadow(0 0 8px rgba(255, 149, 45, 0.72));
  animation: filamentSweep 3.6s ease-in-out infinite;
}

.filament-a { transform: rotate(8deg); }
.filament-b { transform: rotate(137deg); animation-delay: -0.7s; opacity: 0.64; }
.filament-c { transform: rotate(221deg); animation-delay: -1.4s; opacity: 0.52; }
.filament-d { transform: rotate(302deg); animation-delay: -2.1s; opacity: 0.44; }

.spark {
  width: 6px;
  height: 6px;
  background: #ffd27c;
  box-shadow: 0 0 18px rgba(255, 183, 77, 0.95), 0 0 38px rgba(255, 92, 24, 0.62);
}

.spark-a { left: 73%; top: 32%; animation: sparkDrift 5s ease-in-out infinite; }
.spark-b { left: 29%; top: 67%; animation: sparkDrift 6s ease-in-out infinite reverse; }
.spark-c { left: 52%; top: 18%; animation: sparkDrift 4.2s ease-in-out infinite; }
.spark-d { left: 83%; top: 56%; animation: sparkDrift 5.4s ease-in-out infinite reverse; opacity: 0.78; }

.nucleus {
  inset: 40%;
  background:
    radial-gradient(circle, #fff9d7 0 8%, #ffc45f 28%, #ff6d1d 56%, transparent 57%),
    conic-gradient(from 0deg, transparent, rgba(255, 236, 156, 0.9), transparent 35%, rgba(255, 97, 24, 0.85), transparent 70%);
  box-shadow: 0 0 38px rgba(255, 202, 87, 0.98), 0 0 116px rgba(255, 89, 21, 0.78);
  animation: nucleus 1.9s ease-in-out infinite;
}

.readout {
  position: absolute;
  padding: 10px 12px;
  border-left: 2px solid rgba(255, 159, 55, 0.7);
  background: rgba(18, 8, 2, 0.46);
}

.readout span,
.label,
.eyebrow {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0;
}

.readout strong {
  display: block;
  margin-top: 4px;
  color: var(--amber);
  font-size: 15px;
}

.readout-left { left: 48px; top: 64px; }
.readout-right { right: 52px; bottom: 84px; text-align: right; border-left: 0; border-right: 2px solid rgba(255, 159, 55, 0.7); }

.status-panel {
  position: absolute;
  left: 48px;
  bottom: 88px;
  width: min(360px, calc(100% - 96px));
  z-index: 2;
}

.eyebrow {
  margin: 0 0 12px;
}

h1 {
  margin: 0;
  font-size: clamp(52px, 7vw, 96px);
  line-height: 0.9;
  letter-spacing: 0;
  text-shadow: 0 0 34px rgba(255, 128, 32, 0.42);
}

.message {
  margin: 22px 0 0;
  color: #ffe1b5;
  font-size: clamp(22px, 3vw, 32px);
  line-height: 1.12;
}

.detail {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.45;
}

.transcript-panel {
  position: absolute;
  right: 48px;
  top: 76px;
  width: min(310px, calc(100% - 96px));
  padding: 14px 16px;
  border: 1px solid rgba(255, 143, 45, 0.22);
  background: rgba(10, 5, 2, 0.46);
  box-shadow: inset 0 0 28px rgba(255, 110, 24, 0.08);
}

.label {
  margin: 0 0 8px;
}

.transcript {
  margin: 0;
  color: #ffd9a0;
  font-size: 16px;
  line-height: 1.4;
}

.presence {
  position: fixed;
  right: 18px;
  bottom: 18px;
  display: grid;
  grid-template-columns: 56px minmax(0, 116px);
  gap: 12px;
  align-items: center;
  padding: 12px 14px 12px 12px;
  border: 1px solid rgba(255, 143, 45, 0.28);
  border-radius: 12px;
  background: rgba(12, 5, 2, 0.82);
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.46), inset 0 0 28px rgba(255, 102, 24, 0.1);
  backdrop-filter: blur(18px);
  z-index: 10;
}

.presence-orb {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 1px solid rgba(255, 199, 100, 0.52);
  background:
    radial-gradient(circle at 50% 50%, #fff7c5 0 5%, #ffbd58 13%, transparent 14%),
    repeating-conic-gradient(from 0deg, rgba(255, 198, 91, 0.92) 0 5deg, transparent 5deg 12deg),
    radial-gradient(circle, transparent 43%, rgba(255, 136, 35, 0.48) 44% 47%, transparent 48%),
    conic-gradient(from 20deg, transparent, rgba(255, 164, 64, 0.9), transparent 44%, rgba(255, 98, 25, 0.76), transparent 78%);
  box-shadow: 0 0 28px rgba(255, 128, 32, 0.68), inset 0 0 18px rgba(255, 193, 91, 0.16);
  animation: orbit 5.5s linear infinite;
}

.presence-orb span {
  position: absolute;
  left: 50%;
  bottom: 13px;
  width: 5px;
  height: 13px;
  border-radius: 99px;
  background: rgba(20, 7, 2, 0.82);
  transform: translateX(-50%);
  animation: meter 1.2s ease-in-out infinite;
}

.presence-orb span:nth-child(1) { margin-left: -10px; animation-delay: -0.2s; }
.presence-orb span:nth-child(2) { height: 20px; }
.presence-orb span:nth-child(3) { margin-left: 10px; animation-delay: -0.45s; }

.presence-copy strong,
.presence-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.presence-copy strong {
  font-size: 15px;
}

.presence-copy small {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.presence.idle .presence-orb span { animation-play-state: paused; opacity: 0.44; }
.presence.listening .presence-orb { box-shadow: 0 0 34px rgba(255, 196, 91, 0.82); }
.presence.thinking .presence-orb { animation-duration: 2.4s; }
.presence.acting .presence-orb { animation-duration: 1.1s; }
.presence.speaking .presence-orb span { animation-duration: 0.55s; }
.presence.error .presence-orb { box-shadow: 0 0 28px rgba(255, 102, 95, 0.72); filter: saturate(1.5); }

@keyframes scanlines {
  from { transform: translateY(-28px); }
  to { transform: translateY(28px); }
}

@keyframes hudShift {
  0%, 100% { transform: translateX(-18px); opacity: 0.38; }
  50% { transform: translateX(18px); opacity: 0.88; }
}

@keyframes hudShiftVertical {
  0%, 100% { transform: translateY(-18px); opacity: 0.38; }
  50% { transform: translateY(18px); opacity: 0.88; }
}

@keyframes spherePulse {
  0%, 100% { transform: scale(0.985); opacity: 0.9; }
  50% { transform: scale(1.015); opacity: 1; }
}

@keyframes rotateSlow {
  from { transform: rotate(0deg) rotateX(68deg); }
  to { transform: rotate(360deg) rotateX(68deg); }
}

@keyframes orbit {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes sparkDrift {
  0%, 100% { transform: translate3d(0, 0, 0) scale(0.8); opacity: 0.45; }
  50% { transform: translate3d(18px, -12px, 0) scale(1.22); opacity: 1; }
}

@keyframes filamentSweep {
  0%, 100% { opacity: 0.2; width: 28%; }
  45% { opacity: 0.92; width: 48%; }
  70% { opacity: 0.38; width: 34%; }
}

@keyframes nucleus {
  0%, 100% { transform: scale(0.82); opacity: 0.78; }
  50% { transform: scale(1.18); opacity: 1; }
}

@keyframes meter {
  0%, 100% { transform: translateX(-50%) scaleY(0.45); }
  50% { transform: translateX(-50%) scaleY(1.25); }
}

@media (max-width: 640px) {
  body { overflow: auto; }
  .console { padding: 14px; place-items: start center; }
  .framework { width: calc(100vw - 28px); min-height: 680px; aspect-ratio: auto; }
  .scope { inset: 96px 18px 210px; }
  .sphere { width: min(340px, 82vw); }
  .status-panel { left: 22px; right: 22px; bottom: 150px; width: auto; }
  .transcript-panel { left: 22px; right: 22px; top: auto; bottom: 36px; width: auto; }
  .readout-left { left: 22px; top: 28px; }
  .readout-right { right: 22px; bottom: auto; top: 28px; }
  h1 { font-size: 62px; }
  .message { font-size: 24px; }
  .presence { right: 12px; bottom: 12px; grid-template-columns: 48px 98px; }
  .presence-orb { width: 48px; height: 48px; }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }
}
"""


APP_JS = """const presence = document.getElementById("presence");
const message = document.getElementById("message");
const detail = document.getElementById("detail");
const transcript = document.getElementById("transcript");
const stateLabel = document.getElementById("stateLabel");
const stateHint = document.getElementById("stateHint");
const stateReadout = document.getElementById("stateReadout");

const labels = {
  idle: ["Idle", "Waiting"],
  listening: ["Listening", "Recording"],
  thinking: ["Thinking", "Planning"],
  acting: ["Acting", "Using tools"],
  speaking: ["Speaking", "Responding"],
  error: ["Needs attention", "Check terminal"]
};

async function refresh() {
  try {
    const response = await fetch("/state", { cache: "no-store" });
    const state = await response.json();
    const name = state.state || "idle";
    presence.className = `presence ${name}`;
    message.textContent = state.message || "Lumen is awake.";
    detail.textContent = state.detail || "Waiting for a command.";
    transcript.textContent = state.transcript || "Nothing yet.";
    const label = labels[name] || labels.idle;
    stateLabel.textContent = label[0];
    stateHint.textContent = label[1];
    stateReadout.textContent = label[0];
  } catch {
    presence.className = "presence error";
    stateLabel.textContent = "Offline";
    stateHint.textContent = "Reconnecting";
    stateReadout.textContent = "Offline";
  }
}

refresh();
setInterval(refresh, 650);
"""
