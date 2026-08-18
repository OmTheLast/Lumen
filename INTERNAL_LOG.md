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
