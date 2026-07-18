"""Dependency-free local web UI server."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any
from urllib.parse import urlparse
import webbrowser

from lumen.ui.state import ChatBridge, PresenceState


class PresenceServer:
    def __init__(
        self,
        state: PresenceState,
        host: str = "127.0.0.1",
        port: int = 8765,
        chat_bridge: ChatBridge | None = None,
    ) -> None:
        self.state = state
        self.chat_bridge = chat_bridge or ChatBridge()
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
        chat_bridge = self.chat_bridge

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
                if route == "/chat":
                    self._send_json(chat_bridge.snapshot())
                    return
                self.send_error(404)

            def do_POST(self) -> None:
                route = urlparse(self.path).path
                if route == "/chat":
                    payload = self._read_json()
                    text = str(payload.get("text") or "").strip()[:600]
                    if not text:
                        self._send_json({"ok": False, "error": "empty message"}, status=400)
                        return
                    chat_bridge.post_user_message(text)
                    presence.update("thinking", "Command received.", detail=text, transcript=text)
                    self._send_json({"ok": True})
                    return
                if route == "/voice-note":
                    length = int(self.headers.get("Content-Length", "0") or "0")
                    _ = self.rfile.read(min(length, 12_000_000))
                    chat_bridge.append_lumen_message("Voice note captured. Browser transcription bridge comes next.")
                    presence.update("idle", "Voice note received.", detail="Browser voice-message capture is active.")
                    self._send_json({"ok": True})
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

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(min(length, 64_000))
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:
                    return {}
                return payload if isinstance(payload, dict) else {}

            def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status)
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
          <canvas id="frameworkCanvas" class="sigil-canvas"></canvas>
          <span class="shell shell-a"></span>
          <span class="shell shell-b"></span>
          <span class="shell shell-c"></span>
          <span class="scaffold scaffold-a"></span>
          <span class="scaffold scaffold-b"></span>
          <span class="scaffold scaffold-c"></span>
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
      <section class="chat-panel" aria-label="Lumen chat">
        <div class="chat-head">
          <span>console channel</span>
          <strong>Chat / voice</strong>
        </div>
        <div id="chatLog" class="chat-log"></div>
        <form id="chatForm" class="chat-form">
          <input id="chatInput" name="message" autocomplete="off" placeholder="Message Lumen..." />
          <button type="button" id="voiceButton" class="voice-button" aria-label="Record voice message">
            <span></span>
          </button>
          <button type="submit" class="send-button">Send</button>
        </form>
      </section>
    </section>
  </main>
  <aside id="presence" class="presence idle" aria-live="polite">
    <div class="presence-orb">
      <canvas id="presenceCanvas" class="presence-canvas"></canvas>
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
  place-items: stretch;
  padding: 0;
}

.framework {
  position: relative;
  width: 100vw;
  height: 100vh;
  min-height: 620px;
  border: 0;
  background:
    radial-gradient(circle at 50% 47%, rgba(255, 139, 36, 0.12), rgba(8, 4, 2, 0.92) 54%, rgba(3, 2, 1, 0.96));
  box-shadow: inset 0 0 80px rgba(255, 94, 24, 0.08);
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
  display: none;
}

.hud {
  display: none;
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
  inset: 0;
  display: grid;
  place-items: center;
  z-index: 1;
}

.sphere {
  position: relative;
  width: min(76vmin, 820px);
  aspect-ratio: 1;
  border-radius: 50%;
  border: 1px solid rgba(255, 164, 64, 0.32);
  background:
    repeating-conic-gradient(from 18deg, rgba(255, 171, 72, 0.2) 0 2deg, transparent 2deg 7deg),
    radial-gradient(circle at 50% 50%, rgba(255, 194, 88, 0.22), transparent 9%),
    radial-gradient(circle at 44% 48%, rgba(255, 112, 29, 0.24), transparent 28%),
    radial-gradient(circle, transparent 54%, rgba(255, 131, 35, 0.13) 55%, transparent 71%);
  box-shadow: inset 0 0 64px rgba(255, 102, 25, 0.18), 0 0 74px rgba(255, 115, 24, 0.22);
  transform: rotateX(0deg) rotateY(0deg) scale(1);
  transform-style: preserve-3d;
  transition: transform 120ms ease-out;
  animation: spherePulse 4.4s ease-in-out infinite;
  isolation: isolate;
}

.sigil-canvas {
  position: absolute;
  inset: -8%;
  width: 116%;
  height: 116%;
  z-index: 4;
  mix-blend-mode: screen;
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

.shell,
.scaffold,
.core-ring,
.core-slice {
  position: absolute;
  display: block;
  border-radius: 999px;
  pointer-events: none;
}

.shell {
  inset: var(--shell-inset);
  border: 1px solid rgba(255, 191, 86, var(--shell-alpha, 0.18));
  background:
    repeating-conic-gradient(from var(--shell-angle, 0deg), rgba(255, 195, 91, 0.28) 0 1deg, transparent 1deg 7deg),
    radial-gradient(circle, transparent 58%, rgba(255, 130, 30, 0.12) 59% 61%, transparent 62%);
  clip-path: polygon(0 0, 100% 0, 100% 44%, 61% 44%, 61% 58%, 100% 58%, 100% 100%, 0 100%, 0 61%, 37% 61%, 37% 48%, 0 48%);
  filter: drop-shadow(0 0 12px rgba(255, 139, 36, 0.28));
  mix-blend-mode: screen;
  opacity: 0.86;
  animation: shellOrbit var(--shell-speed, 12s) linear infinite;
}

.shell-a { --shell-inset: -4%; --shell-angle: 5deg; --shell-speed: 18s; --shell-alpha: 0.2; }
.shell-b { --shell-inset: 7%; --shell-angle: 73deg; --shell-speed: 13s; --shell-alpha: 0.24; animation-direction: reverse; transform: rotateX(58deg); }
.shell-c { --shell-inset: 18%; --shell-angle: 132deg; --shell-speed: 9s; --shell-alpha: 0.28; clip-path: polygon(0 0, 56% 0, 56% 19%, 100% 19%, 100% 100%, 42% 100%, 42% 78%, 0 78%); }

.scaffold {
  left: 50%;
  top: 50%;
  width: 82%;
  height: 1px;
  background:
    linear-gradient(90deg, transparent 0 8%, rgba(255, 216, 122, 0.16) 8% 19%, transparent 19% 31%, rgba(255, 147, 45, 0.7) 31% 35%, transparent 35% 50%, rgba(255, 229, 160, 0.58) 50% 57%, transparent 57% 100%);
  box-shadow:
    0 0 10px rgba(255, 171, 64, 0.38),
    0 14px 0 rgba(255, 152, 48, 0.1),
    0 -18px 0 rgba(255, 195, 89, 0.08);
  transform-origin: 0 50%;
  mix-blend-mode: screen;
  animation: scaffoldFlicker 2.8s ease-in-out infinite;
  z-index: 3;
}

.scaffold-a { transform: rotate(6deg) translateX(-50%); }
.scaffold-b { transform: rotate(94deg) translateX(-50%); animation-delay: -0.7s; opacity: 0.62; }
.scaffold-c { transform: rotate(151deg) translateX(-50%); animation-delay: -1.6s; opacity: 0.52; }

.core-ring {
  inset: 36%;
  border: 1px solid rgba(255, 224, 143, 0.62);
  background:
    repeating-conic-gradient(from 16deg, transparent 0 8deg, rgba(255, 187, 76, 0.4) 8deg 10deg, transparent 10deg 18deg),
    radial-gradient(circle, transparent 52%, rgba(255, 111, 28, 0.22) 53% 60%, transparent 61%);
  box-shadow: 0 0 18px rgba(255, 166, 62, 0.48), inset 0 0 22px rgba(255, 97, 24, 0.28);
  mix-blend-mode: screen;
  z-index: 5;
}

.core-ring-a {
  animation: orbit 3.4s linear infinite;
}

.core-ring-b {
  inset: 39%;
  border-color: rgba(255, 132, 35, 0.52);
  transform: rotateX(62deg) rotate(18deg);
  animation: rotateSlow 2.9s linear infinite reverse;
}

.core-slice {
  left: 50%;
  top: 50%;
  width: 28%;
  height: 8%;
  border: 1px solid rgba(255, 196, 91, 0.34);
  background:
    linear-gradient(90deg, transparent, rgba(255, 232, 161, 0.2), rgba(255, 136, 38, 0.12), transparent),
    repeating-linear-gradient(0deg, rgba(255, 199, 91, 0.22) 0 1px, transparent 1px 6px);
  box-shadow: 0 0 20px rgba(255, 142, 39, 0.3);
  mix-blend-mode: screen;
  z-index: 4;
}

.core-slice-a { transform: translate(-30%, -78%) rotate(4deg); }
.core-slice-b { transform: translate(-69%, 18%) rotate(-12deg); opacity: 0.72; }

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
  inset: 42%;
  background:
    radial-gradient(circle at 47% 45%, #fffbe2 0 7%, #ffe08e 13%, #ff8a2d 34%, transparent 35%),
    conic-gradient(from 23deg, rgba(255, 244, 194, 0.95), transparent 18%, rgba(255, 126, 31, 0.92), transparent 44%, rgba(255, 215, 121, 0.78), transparent 71%, rgba(255, 106, 28, 0.88));
  box-shadow: 0 0 42px rgba(255, 218, 118, 0.98), 0 0 132px rgba(255, 89, 21, 0.78);
  animation: nucleus 1.9s ease-in-out infinite;
  z-index: 6;
}

.nucleus::before,
.nucleus::after {
  content: "";
  position: absolute;
  inset: -82%;
  border-radius: inherit;
  border: 1px solid rgba(255, 231, 155, 0.38);
  background: repeating-conic-gradient(from 18deg, rgba(255, 207, 104, 0.48) 0 5deg, transparent 5deg 16deg);
  mix-blend-mode: screen;
}

.nucleus::before {
  animation: orbit 2.2s linear infinite;
}

.nucleus::after {
  inset: -132%;
  opacity: 0.58;
  transform: rotateX(68deg);
  animation: orbit 3.2s linear infinite reverse;
}

.readout {
  position: absolute;
  padding: 10px 12px;
  border-left: 2px solid rgba(255, 159, 55, 0.7);
  background: rgba(18, 8, 2, 0.46);
  z-index: 3;
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
.readout-right { right: 52px; top: 176px; text-align: right; border-left: 0; border-right: 2px solid rgba(255, 159, 55, 0.7); }

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

.chat-panel {
  position: absolute;
  right: 48px;
  bottom: 116px;
  width: min(330px, calc(100% - 96px));
  display: grid;
  grid-template-rows: auto minmax(118px, 1fr) auto;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(255, 143, 45, 0.24);
  background: linear-gradient(180deg, rgba(23, 10, 3, 0.72), rgba(8, 4, 2, 0.62));
  box-shadow: inset 0 0 34px rgba(255, 110, 24, 0.08), 0 18px 44px rgba(0, 0, 0, 0.22);
  z-index: 3;
}

.chat-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 143, 45, 0.16);
  padding-bottom: 9px;
}

.chat-head span {
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
}

.chat-head strong {
  color: var(--amber);
  font-size: 13px;
}

.chat-log {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
  min-height: 118px;
  max-height: 166px;
}

.chat-message {
  max-width: 88%;
  border: 1px solid rgba(255, 143, 45, 0.18);
  padding: 8px 9px;
  color: #ffe0ad;
  background: rgba(8, 4, 2, 0.54);
  font-size: 13px;
  line-height: 1.35;
}

.chat-message.user {
  align-self: flex-end;
  color: #fff0d0;
  border-color: rgba(255, 191, 91, 0.28);
  background: rgba(96, 40, 9, 0.32);
}

.chat-message small {
  display: block;
  color: var(--muted);
  font-size: 10px;
  margin-bottom: 3px;
  text-transform: uppercase;
}

.chat-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px 58px;
  gap: 8px;
}

.chat-form input,
.chat-form button {
  min-height: 38px;
  border: 1px solid rgba(255, 143, 45, 0.26);
  background: rgba(8, 4, 2, 0.72);
  color: var(--text);
  font: inherit;
}

.chat-form input {
  min-width: 0;
  padding: 0 10px;
  outline: none;
}

.chat-form input:focus,
.chat-form button:focus-visible {
  border-color: rgba(255, 204, 116, 0.82);
  box-shadow: 0 0 0 2px rgba(255, 143, 45, 0.18);
}

.chat-form button {
  cursor: pointer;
}

.voice-button {
  position: relative;
  display: grid;
  place-items: center;
}

.voice-button span {
  width: 12px;
  height: 18px;
  border: 2px solid var(--amber);
  border-radius: 99px;
  position: relative;
}

.voice-button span::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -9px;
  width: 14px;
  height: 7px;
  border-bottom: 2px solid var(--amber);
  border-left: 2px solid transparent;
  border-right: 2px solid transparent;
  transform: translateX(-50%);
}

.voice-button.recording {
  background: rgba(255, 89, 21, 0.28);
  box-shadow: 0 0 24px rgba(255, 89, 21, 0.28);
}

.send-button {
  color: var(--amber);
  font-size: 13px;
  text-transform: uppercase;
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

.presence-canvas {
  position: absolute;
  inset: -18%;
  width: 136%;
  height: 136%;
  mix-blend-mode: screen;
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

@keyframes shellOrbit {
  from { transform: rotate(0deg) scaleX(1); }
  50% { transform: rotate(180deg) scaleX(0.94); }
  to { transform: rotate(360deg) scaleX(1); }
}

@keyframes scaffoldFlicker {
  0%, 100% { opacity: 0.3; filter: blur(0); }
  36% { opacity: 0.84; filter: blur(0.15px); }
  48% { opacity: 0.42; }
  62% { opacity: 0.72; }
}

@keyframes spherePulse {
  0%, 100% { opacity: 0.9; filter: saturate(0.92); }
  50% { opacity: 1; filter: saturate(1.14); }
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
  .framework { width: calc(100vw - 28px); min-height: 900px; height: auto; }
  .scope { inset: 96px 0 430px; }
  .sphere { width: min(78vmin, 82vw); }
  .status-panel { left: 22px; right: 22px; bottom: 354px; width: auto; }
  .transcript-panel { display: none; }
  .chat-panel { left: 22px; right: 22px; bottom: 90px; width: auto; padding: 10px; gap: 8px; }
  .chat-log { min-height: 48px; max-height: 54px; }
  .chat-message { padding: 7px 8px; font-size: 12px; }
  .chat-form { grid-template-columns: minmax(0, 1fr) 38px 54px; }
  .readout-left { left: 22px; top: 28px; }
  .readout-right { right: 22px; bottom: auto; top: 28px; }
  h1 { font-size: 62px; }
  .message { font-size: 24px; }
  .presence { display: none; }
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
const frameworkCanvas = document.getElementById("frameworkCanvas");
const presenceCanvas = document.getElementById("presenceCanvas");
const framework = document.querySelector(".framework");
const sphere = document.querySelector(".sphere");
const chatLog = document.getElementById("chatLog");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const voiceButton = document.getElementById("voiceButton");
let activeState = "idle";
let pointer = { x: 0, y: 0, tx: 0, ty: 0 };
let mediaRecorder = null;
let voiceChunks = [];

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
    activeState = name;
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

const palette = {
  idle: [255, 154, 53],
  listening: [255, 193, 92],
  thinking: [255, 143, 45],
  acting: [255, 111, 31],
  speaking: [255, 209, 124],
  error: [255, 102, 95]
};

function buildNodes() {
  const nodes = [];
  for (let lat = -60; lat <= 60; lat += 20) {
    const phi = lat * Math.PI / 180;
    const ringCount = Math.round(18 * Math.cos(phi)) + 8;
    for (let i = 0; i < ringCount; i++) {
      const theta = (i / ringCount) * Math.PI * 2;
      nodes.push({
        x: Math.cos(phi) * Math.cos(theta),
        y: Math.sin(phi),
        z: Math.cos(phi) * Math.sin(theta),
        ring: lat,
        index: i,
        ringCount
      });
    }
  }
  for (let i = 0; i < 38; i++) {
    const a = i * 2.399963;
    const z = 1 - (2 * i + 1) / 38;
    const r = Math.sqrt(1 - z * z);
    nodes.push({ x: Math.cos(a) * r, y: Math.sin(a) * r, z, ring: 999, index: i, ringCount: 38 });
  }
  return nodes;
}

const nodes = buildNodes();

function rotatePoint(point, time, compact) {
  const speed = compact ? 0.0018 : 0.0011;
  const ay = time * speed + (compact ? pointer.x * 0.6 : pointer.x * 1.45);
  const ax = Math.sin(time * 0.00042) * 0.42 + 0.22 + (compact ? pointer.y * 0.34 : pointer.y * 0.95);
  const az = Math.cos(time * 0.00031) * 0.18 + (compact ? pointer.x * pointer.y * 0.08 : pointer.x * pointer.y * 0.2);
  let x = point.x;
  let y = point.y;
  let z = point.z;

  let cy = Math.cos(ay), sy = Math.sin(ay);
  [x, z] = [x * cy - z * sy, x * sy + z * cy];
  let cx = Math.cos(ax), sx = Math.sin(ax);
  [y, z] = [y * cx - z * sx, y * sx + z * cx];
  let cz = Math.cos(az), sz = Math.sin(az);
  [x, y] = [x * cz - y * sz, x * sz + y * cz];
  return { x, y, z };
}

function projectOrbitPoint(point, time, compact, radius, focal) {
  const p = rotatePoint(point, time, compact);
  const depth = focal / (focal - p.z);
  return {
    x: p.x * radius * depth,
    y: p.y * radius * depth,
    z: p.z,
    depth
  };
}

function rgba(rgb, alpha) {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

function drawSigil(canvas, time, compact = false) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.floor(rect.width * dpr));
  const height = Math.max(1, Math.floor(rect.height * dpr));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(width / 2, height / 2);
  const rgb = palette[activeState] || palette.idle;
  const radius = Math.min(width, height) * (compact ? 0.3 : 0.34);
  const focal = compact ? 2.25 : 2.65;
  const projected = nodes.map((node) => {
    const p = projectOrbitPoint(node, time, compact, radius, focal);
    return {
      ...node,
      rx: p.x,
      ry: p.y,
      rz: p.z,
      depth: p.depth
    };
  });

  const shell = ctx.createRadialGradient(0, 0, radius * 0.05, 0, 0, radius * 1.22);
  shell.addColorStop(0, rgba(rgb, 0.18));
  shell.addColorStop(0.48, rgba(rgb, 0.05));
  shell.addColorStop(1, rgba(rgb, 0.0));
  ctx.fillStyle = shell;
  ctx.beginPath();
  ctx.arc(0, 0, radius * 1.24, 0, Math.PI * 2);
  ctx.fill();

  const edges = [];
  for (let i = 0; i < projected.length; i++) {
    const a = projected[i];
    for (let j = i + 1; j < projected.length; j++) {
      const b = projected[j];
      const sameRing = a.ring === b.ring && Math.abs(a.index - b.index) <= 1;
      const near = Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) < (compact ? 0.42 : 0.36);
      if (sameRing || near) {
        edges.push([a, b, (a.rz + b.rz) / 2]);
      }
    }
  }
  edges.sort((a, b) => a[2] - b[2]);

  for (const [a, b, z] of edges.slice(0, compact ? 220 : 360)) {
    const alpha = Math.max(0.05, Math.min(0.38, (z + 1.4) / 5));
    ctx.strokeStyle = rgba(rgb, alpha);
    ctx.lineWidth = Math.max(0.65, (compact ? 0.9 : 1.1) * Math.max(a.depth, b.depth));
    ctx.beginPath();
    ctx.moveTo(a.rx, a.ry);
    ctx.lineTo(b.rx, b.ry);
    ctx.stroke();
  }

  const sortedNodes = [...projected].sort((a, b) => a.rz - b.rz);
  for (const p of sortedNodes) {
    const alpha = Math.max(0.18, Math.min(0.95, (p.rz + 1.2) / 2.2));
    const nodeRadius = (compact ? 1.5 : 2.3) * p.depth;
    ctx.fillStyle = rgba(rgb, alpha);
    ctx.beginPath();
    ctx.arc(p.rx, p.ry, nodeRadius, 0, Math.PI * 2);
    ctx.fill();
  }

  drawProjectedRing(ctx, time, compact, radius, focal, rgb, 0.84, "xy", 0.24);
  drawProjectedRing(ctx, time + 420, compact, radius, focal, rgb, 0.68, "xz", 0.21);
  drawProjectedRing(ctx, time + 860, compact, radius, focal, rgb, 0.52, "yz", 0.18);

  if (!compact) {
    for (let i = 0; i < 5; i++) {
      const ringRadius = radius * (0.18 + i * 0.085);
      const segments = 7 + i * 2;
      ctx.save();
      ctx.rotate(time * (0.0008 - i * 0.00009) + i * 0.72);
      ctx.strokeStyle = rgba(rgb, 0.34 - i * 0.035);
      ctx.lineWidth = 1.2 + (i % 2) * 0.6;
      for (let s = 0; s < segments; s++) {
        const start = (s / segments) * Math.PI * 2;
        const span = 0.12 + ((s + i) % 3) * 0.08;
        ctx.beginPath();
        ctx.arc(0, 0, ringRadius, start, start + span);
        ctx.stroke();
      }
      ctx.restore();
    }

    for (let i = 0; i < 26; i++) {
      const angle = i * 0.73 + time * 0.00046;
      const distance = radius * (0.16 + (i % 9) * 0.044);
      const length = radius * (0.035 + (i % 4) * 0.018);
      const x = Math.cos(angle) * distance;
      const y = Math.sin(angle * 1.17) * distance * 0.72;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle + Math.PI / 2);
      ctx.strokeStyle = rgba(rgb, 0.18 + (i % 5) * 0.06);
      ctx.lineWidth = i % 6 === 0 ? 2.2 : 1.1;
      ctx.beginPath();
      ctx.moveTo(-length, 0);
      ctx.lineTo(length, 0);
      ctx.stroke();
      if (i % 4 === 0) {
        ctx.strokeRect(length * 0.35, -length * 0.28, length * 1.35, length * 0.56);
      }
      ctx.restore();
    }
  }

  drawProjectedCore(ctx, time, compact, radius, focal, rgb);
  ctx.restore();
}

function drawProjectedRing(ctx, time, compact, radius, focal, rgb, scale, plane, alpha) {
  const points = [];
  const count = compact ? 72 : 112;
  for (let i = 0; i <= count; i++) {
    const a = (i / count) * Math.PI * 2;
    const wobble = 0.04 * Math.sin(a * 3 + time * 0.001);
    const base = { x: 0, y: 0, z: 0 };
    if (plane === "xy") {
      base.x = Math.cos(a) * scale;
      base.y = Math.sin(a) * scale * (0.7 + wobble);
      base.z = Math.sin(a * 2 + time * 0.0007) * 0.08;
    } else if (plane === "xz") {
      base.x = Math.cos(a) * scale;
      base.y = Math.sin(a * 2 + time * 0.0005) * 0.08;
      base.z = Math.sin(a) * scale * (0.64 + wobble);
    } else {
      base.x = Math.sin(a * 2 + time * 0.0004) * 0.08;
      base.y = Math.cos(a) * scale * (0.66 + wobble);
      base.z = Math.sin(a) * scale;
    }
    points.push(projectOrbitPoint(base, time, compact, radius, focal));
  }
  ctx.strokeStyle = rgba(rgb, alpha);
  ctx.lineWidth = compact ? 0.9 : 1.25;
  ctx.beginPath();
  for (const [index, point] of points.entries()) {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  }
  ctx.stroke();
}

function drawProjectedCore(ctx, time, compact, radius, focal, rgb) {
  const orbit = {
    x: Math.sin(time * 0.0011) * 0.16 + 0.06,
    y: Math.cos(time * 0.00135) * 0.11,
    z: Math.sin(time * 0.0016) * 0.18
  };
  const core = projectOrbitPoint(orbit, time, compact, radius, focal);
  const coreRadius = radius * (compact ? 0.11 : 0.15) * core.depth;
  const glow = ctx.createRadialGradient(core.x, core.y, 0, core.x, core.y, coreRadius * 2.2);
  glow.addColorStop(0, "rgba(255, 253, 214, 0.98)");
  glow.addColorStop(0.22, rgba(rgb, 0.86));
  glow.addColorStop(1, rgba(rgb, 0));
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(core.x, core.y, coreRadius * 2.2, 0, Math.PI * 2);
  ctx.fill();

  for (let i = 0; i < (compact ? 5 : 9); i++) {
    const a = time * 0.002 + i * 0.72;
    const node = {
      x: orbit.x + Math.cos(a) * (0.09 + (i % 3) * 0.018),
      y: orbit.y + Math.sin(a * 1.21) * 0.07,
      z: orbit.z + Math.sin(a) * 0.08
    };
    const p = projectOrbitPoint(node, time + i * 80, compact, radius, focal);
    ctx.strokeStyle = rgba(rgb, 0.34);
    ctx.lineWidth = compact ? 0.8 : 1.2;
    ctx.beginPath();
    ctx.moveTo(core.x, core.y);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    ctx.fillStyle = i % 2 === 0 ? "#fff5bf" : rgba(rgb, 0.88);
    ctx.beginPath();
    ctx.arc(p.x, p.y, (compact ? 1.4 : 2.2) * p.depth, 0, Math.PI * 2);
    ctx.fill();
  }
}

function animateSigils(time) {
  pointer.x += (pointer.tx - pointer.x) * 0.08;
  pointer.y += (pointer.ty - pointer.y) * 0.08;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const t = reduced ? 1200 : time;
  if (sphere) {
    const pulse = reduced ? 1 : 1 + Math.sin(t * 0.0022) * 0.018;
    sphere.style.transform = `rotateX(${(-pointer.y * 13).toFixed(2)}deg) rotateY(${(pointer.x * 17).toFixed(2)}deg) scale(${pulse.toFixed(3)})`;
  }
  drawSigil(frameworkCanvas, t, false);
  drawSigil(presenceCanvas, t, true);
  if (!reduced) requestAnimationFrame(animateSigils);
}

function updatePointer(event) {
  if (!framework) return;
  const rect = framework.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
  const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
  pointer.tx = Math.max(-1, Math.min(1, x));
  pointer.ty = Math.max(-1, Math.min(1, y));
}

function resetPointer() {
  pointer.tx = 0;
  pointer.ty = 0;
}

async function refreshChat() {
  if (!chatLog) return;
  try {
    const response = await fetch("/chat", { cache: "no-store" });
    const payload = await response.json();
    const messages = payload.messages || [];
    chatLog.innerHTML = messages.map((item) => {
      const role = item.role === "user" ? "user" : "lumen";
      return `<div class="chat-message ${role}"><small>${item.time || ""} · ${role}</small>${escapeHtml(item.text || "")}</div>`;
    }).join("");
    chatLog.scrollTop = chatLog.scrollHeight;
  } catch {
    chatLog.innerHTML = `<div class="chat-message lumen"><small>offline</small>Chat bridge unavailable.</div>`;
  }
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[char]);
}

async function sendChatMessage(event) {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  refreshChat();
}

async function toggleVoiceMessage() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Voice message requested, but this browser cannot record audio." })
    });
    refreshChat();
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  voiceChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) voiceChunks.push(event.data);
  };
  mediaRecorder.onstop = async () => {
    voiceButton.classList.remove("recording");
    stream.getTracks().forEach((track) => track.stop());
    const blob = new Blob(voiceChunks, { type: mediaRecorder.mimeType || "audio/webm" });
    await fetch("/voice-note", { method: "POST", body: blob });
    refreshChat();
  };
  voiceButton.classList.add("recording");
  mediaRecorder.start();
}

refresh();
refreshChat();
setInterval(refresh, 650);
setInterval(refreshChat, 1800);
framework?.addEventListener("pointermove", updatePointer);
framework?.addEventListener("pointerleave", resetPointer);
chatForm?.addEventListener("submit", sendChatMessage);
voiceButton?.addEventListener("click", () => {
  toggleVoiceMessage().catch(async () => {
    voiceButton.classList.remove("recording");
    await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Voice message permission was denied or unavailable." })
    });
    refreshChat();
  });
});
requestAnimationFrame(animateSigils);
"""
