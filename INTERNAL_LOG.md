# Lumen Internal Log

This log is for Om and Codex to keep implementation context across sessions. Do not put secrets, tokens, private files, or model weights here.

## 2026-07-26

### Current Direction

Lumen should become a local-first desktop agent framework rather than a single hardcoded model demo.

### Implemented In This Checkpoint

- Added persistent runtime model settings.
- Added local model discovery for Ollama and LM Studio-compatible servers.
- Added web UI selectors for planner, router, and voice STT models.
- Added live browser speech recognition for lower-latency web voice commands when supported.
- Kept the existing browser audio upload path as fallback.

### Runtime Config

Saved model choices live at:

```text
~/.lumen/config.json
```

Environment variables still override saved values:

```text
LUMEN_PLANNER_MODEL
LUMEN_ROUTER_MODEL
LUMEN_VOICE_STT_MODEL
```

### Current Constraints

- Browser live speech recognition depends on browser support and microphone permission.
- Terminal `/voice` still records then transcribes locally with `mlx-whisper`; true streaming STT is not implemented yet.
- LM Studio model discovery requires its local server to be running at `http://localhost:1234`.
- Ollama discovery requires Ollama to be running at `http://localhost:11434`.

### Next Engineering Step

Build a proper tool registry and permission policy layer:

- Define tool capabilities and risk levels.
- Show pending risky actions in the web UI.
- Allow per-tool approval modes.
- Add audit logging for executed tools and rejected actions.

## 2026-08-17

### macOS App Packaging

- Added `--app` / `--no-stdin` mode so Lumen can run from Finder without terminal stdin.
- Added `scripts/build_macos_app.sh` to build `dist/macos/Lumen.app`.
- The app wrapper launches `uv run python -m lumen.main --app`, opens the local web console, enables the overlay, and writes logs to `~/Library/Logs/Lumen/lumen.log`.

### Packaging Boundary

This is a repo-backed app wrapper, not a fully self-contained signed/notarized `.dmg`. It still requires `uv`, the local repo checkout, and separate local model installation.

### Native App Window

- Added a Swift/AppKit `lumen-window` helper that opens the local `http://127.0.0.1:8765` interface inside a native macOS window.
- Updated `Lumen.app` launch defaults to stop opening a browser tab and enable the native app window.
- Added a Swift/AppKit `lumen-overlay` helper for a transparent bottom-right desktop orb; Tk remains fallback only.
- Closing the native Lumen window now shuts down the app-mode backend.

### GitHub Presentation

- Reframed `README.md` as the public-facing GitHub page for Lumen as a local macOS desktop agent.
- Removed Cloudflare deployment/install-hub language from the public README.
- Documented the Lumen image asset at `assets/lumen-icon.png` with editable source at `assets/lumen-icon.svg`.

## 2026-08-28

### Voice Latency

- Tightened local command recording defaults: 8 second maximum and 0.45 second silence cutoff.
- Tuned `mlx-whisper` decoding for short command latency with deterministic single-pass settings.
- Added native macOS speech recognition to the `Lumen.app` window through a WebKit message bridge.
- The app-window mic button now prefers native streaming speech recognition; terminal `/voice` keeps using local Whisper.
- Added first-pass wake-word mode in the native app window: macOS speech recognition listens for "Lumen," then captures and posts the following command.
- Added `Lumen.icns` generation from `assets/lumen-icon.png` during app packaging and declared `CFBundleIconFile` for Dock/app-switcher identity.
- Changed `Lumen.app` so the Swift native window is the actual bundle executable; it starts the Python backend itself and gives macOS speech recognition the app `Info.plist` privacy keys it requires.
- Fixed a native-window crash caused by encoding plain Swift strings through `JSONSerialization` without fragment support.

### App Icon Refinement

- Replaced the overly simple lens-style app icon with a code-drawn framework orb based on the bottom-right desktop overlay.
- Kept the selected icon source in `assets/lumen-icon.svg` and regenerated `assets/lumen-icon.png` for macOS `.icns` packaging.

### Wake Command Follow-Through

- Diagnosed native voice commands showing in the UI without action: macOS speech recognition can keep emitting partial transcripts without promptly marking them final.
- Added a short native debounce timer so stable wake/manual transcripts are submitted to `/chat` after the user pauses.
- Added a simple planner rule for plain `open youtube` so it opens `https://www.youtube.com` instead of trying to launch a nonexistent macOS app named YouTube.

### Browser Control And Voice Presets

- Added AppleScript-backed browser tools for new tab, close tab, reload tab, tab switching, and active tab inspection.
- Added simple planner routes for natural commands like `new tab`, `close tab`, `next tab`, `reload tab`, and `what tab am I on`.
- Smoke-tested Safari control by opening `https://example.com`, reading the active tab title/URL, and closing the tab.
- Exposed stronger `mlx-whisper` voice presets in the model picker while keeping `whisper-tiny` as the default latency-first terminal model.
- Current recommended terminal voice experiment: `mlx-community/whisper-large-v3-turbo-q4`.

## 2026-08-31

### Background Task Engine

- Added a persistent task store at `~/.lumen/tasks.json`.
- Added a background task worker that requeues unfinished tasks after restart and runs objectives through Lumen's existing planner/tool loop.
- Added `/tasks` API support for listing and creating local background tasks.
- Added a compact task panel to the app window with a task input and recent task statuses.
- Added chat command routing for `task ...`, `start task ...`, and `start background task ...` so voice/chat can queue work without blocking the console response.

### In-App Approval Queue

- Added an `ApprovalBroker` for pending risky actions with approve/reject/expire states.
- Wired app-mode and background-task executors to pause on the shared approval broker instead of prompting terminal stdin.
- Added `/approvals` API support for listing and resolving pending approvals.
- Added a compact approval panel in the app window with action reason, risk, arguments, and Approve/Reject buttons.
- Added a deterministic screenshot planner route so screenshot approval requests appear quickly without waiting for the LLM.
- Smoke-tested by requesting a screenshot, rejecting the pending approval through `/approvals`, and confirming Lumen reported `Cancelled screenshot.`

## 2026-09-23

### Distribution And Startup Reliability

- Raised the package and native app version to `0.4.0` for the first Homebrew release.
- Added `https://lumen.ompatnaik.com` to the public project presentation.
- Captured the real native app window at `assets/lumen-app.jpg` for the GitHub README.
- Added a Homebrew installation path that packages Lumen without model weights.
- Changed the native launcher to find `uv` through `LUMEN_UV_PATH`, `~/.local/bin`, Homebrew, and the inherited `PATH`.
- Added support for a packaged Python runtime so Homebrew installs do not require `uv` at launch.
- Added a visible native startup-error page with the backend log path.
- Fixed native app port drift: the wrapper now reserves a free localhost port and passes the same port to the backend, window, voice bridge, and overlay.

### Verification

- Swift native window and overlay helpers compile.
- Python suite passes: 33 tests.
- Finder-style launch found `/Users/ompatnaik/.local/bin/uv` and started Lumen on a reserved port while port 8765 was occupied by another project.
- Native app state and screenshot were verified from the running `Lumen.app` window.

### Next Action

- Release `v0.4.0` was tagged and published. Its source checksum is recorded in `Formula/lumen-local.rb`.
- Homebrew 7 rejected direct path formulas, so the existing repository is used as the custom `OmTheLast/lumen` tap instead of creating a second repository.
- Push and register the tap, test `brew install lumen-local` end to end, then set the GitHub repository homepage.
