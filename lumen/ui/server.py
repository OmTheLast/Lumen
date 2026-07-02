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
  <main class="shell">
    <section class="hero">
      <div class="mark" aria-hidden="true">
        <span class="core"></span>
        <span class="ring ring-a"></span>
        <span class="ring ring-b"></span>
      </div>
      <p class="eyebrow">Local desktop agent</p>
      <h1>Lumen</h1>
      <p id="message" class="message">Lumen is awake.</p>
      <p id="detail" class="detail">Waiting for a command.</p>
    </section>
    <section class="transcript-wrap">
      <p class="label">Last heard</p>
      <p id="transcript" class="transcript">Nothing yet.</p>
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
  --bg: #0a0c10;
  --text: #f4f6f8;
  --muted: #9aa4af;
  --line: rgba(255, 255, 255, 0.12);
  --cyan: #55d6ff;
  --green: #6ee7a7;
  --gold: #ffd166;
  --rose: #ff7a90;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at 12% 18%, rgba(85, 214, 255, 0.16), transparent 28%),
    radial-gradient(circle at 82% 24%, rgba(110, 231, 167, 0.12), transparent 24%),
    linear-gradient(145deg, #090b0f 0%, #10141b 54%, #090b0f 100%);
  color: var(--text);
  overflow: hidden;
}

.shell {
  width: min(980px, calc(100vw - 48px));
  min-height: 100vh;
  margin: 0 auto;
  display: grid;
  align-content: center;
  gap: 32px;
}

.hero { max-width: 720px; }

.mark {
  position: relative;
  width: 104px;
  height: 104px;
  margin-bottom: 28px;
}

.core, .ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
}

.core {
  inset: 28px;
  background: radial-gradient(circle at 34% 30%, #fff, var(--cyan) 38%, #146a82 100%);
  box-shadow: 0 0 34px rgba(85, 214, 255, 0.72);
}

.ring {
  border: 1px solid rgba(85, 214, 255, 0.32);
  animation: breathe 4s ease-in-out infinite;
}

.ring-b {
  inset: 13px;
  border-color: rgba(110, 231, 167, 0.34);
  animation-delay: -1.5s;
}

.eyebrow {
  color: var(--green);
  margin: 0 0 12px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0;
}

h1 {
  margin: 0;
  font-size: clamp(68px, 12vw, 156px);
  line-height: 0.88;
  letter-spacing: 0;
}

.message {
  margin: 28px 0 0;
  font-size: clamp(24px, 4vw, 44px);
  line-height: 1.08;
}

.detail {
  max-width: 680px;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 18px;
  line-height: 1.5;
}

.transcript-wrap {
  width: min(680px, 100%);
  border-top: 1px solid var(--line);
  padding-top: 20px;
}

.label {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0;
}

.transcript {
  margin: 0;
  color: #d9e0e8;
  font-size: 20px;
  line-height: 1.4;
}

.presence {
  position: fixed;
  right: 22px;
  bottom: 22px;
  display: grid;
  grid-template-columns: 56px minmax(0, 118px);
  gap: 12px;
  align-items: center;
  padding: 12px 14px 12px 12px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(10, 14, 20, 0.76);
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.36);
  backdrop-filter: blur(18px);
}

.presence-orb {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 28%, #fff, var(--cyan) 42%, #153846 100%);
  box-shadow: 0 0 24px rgba(85, 214, 255, 0.52);
}

.presence-orb span {
  position: absolute;
  left: 50%;
  bottom: 13px;
  width: 5px;
  height: 13px;
  border-radius: 99px;
  background: rgba(8, 18, 24, 0.72);
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
.presence.listening .presence-orb { box-shadow: 0 0 32px rgba(110, 231, 167, 0.7); }
.presence.thinking .presence-orb { filter: hue-rotate(52deg); animation: tilt 1.8s ease-in-out infinite; }
.presence.acting .presence-orb { filter: hue-rotate(120deg); }
.presence.speaking .presence-orb span { animation-duration: 0.55s; }
.presence.error .presence-orb { filter: hue-rotate(180deg); box-shadow: 0 0 28px rgba(255, 122, 144, 0.72); }

@keyframes breathe {
  0%, 100% { transform: scale(0.92); opacity: 0.42; }
  50% { transform: scale(1.08); opacity: 0.9; }
}

@keyframes meter {
  0%, 100% { transform: translateX(-50%) scaleY(0.45); }
  50% { transform: translateX(-50%) scaleY(1.25); }
}

@keyframes tilt {
  0%, 100% { transform: rotate(-4deg); }
  50% { transform: rotate(4deg); }
}

@media (max-width: 640px) {
  body { overflow: auto; }
  .shell { width: min(100vw - 28px, 980px); padding: 44px 0 120px; align-content: start; }
  h1 { font-size: 76px; }
  .message { font-size: 28px; }
  .presence { right: 12px; bottom: 12px; grid-template-columns: 48px 98px; }
  .presence-orb { width: 48px; height: 48px; }
}
"""


APP_JS = """const presence = document.getElementById("presence");
const message = document.getElementById("message");
const detail = document.getElementById("detail");
const transcript = document.getElementById("transcript");
const stateLabel = document.getElementById("stateLabel");
const stateHint = document.getElementById("stateHint");

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
  } catch {
    presence.className = "presence error";
    stateLabel.textContent = "Offline";
    stateHint.textContent = "Reconnecting";
  }
}

refresh();
setInterval(refresh, 650);
"""
