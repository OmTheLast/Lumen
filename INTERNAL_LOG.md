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

## 2026-08-12

### Cloudflare Website Checkpoint

- Installed Wrangler globally.
- Authenticated Wrangler with Cloudflare account `omexp99@gmail.com`.
- Accepted Wrangler's Cloudflare agent-skill setup for Codex and other local coding agents.
- Added Worker configuration for `lumen.ompatnaik.com`.
- Added a public static site in `public/`.
- Added Worker API route `/api/health`.
- Added local npm scripts for Worker development, dry-run validation, and deploy.
- Deployed Worker version `384c5971-1dea-4384-8ed8-95c8cee17c22`.

### DNS Note

Cloudflare DNS returned A records for `lumen.ompatnaik.com` through `1.1.1.1`, and forced-resolution curl successfully reached the Worker. The local resolver initially still returned NXDOMAIN, likely cached during propagation.

## 2026-08-15

### Public Hub Upgrade

- Reworked `lumen.ompatnaik.com` from a static project page into a Lumen install/run hub.
- Added copyable local run, model, voice, clone, and install commands.
- Added `/install.sh` for a guided macOS repo install/update path.
- Added browser-side local health detection for `http://127.0.0.1:8765/state`.
- Added CORS and Private Network Access headers to the local Lumen UI server so the public hub can detect the local console.

### Boundary

The public Worker cannot run Lumen's desktop automation directly. It can guide installation and open a locally running console. Actual tool execution remains on the user's Mac.

## 2026-08-16

### Hero Visual Direction

- Reworked the public site's main canvas from a geometric orb into a neural lattice visual.
- Added deterministic neuron clusters, curved synapse links, signal pulses, and a moving bright core.
- Kept the orange Lumen visual language while avoiding a direct copy of any film UI asset.

## 2026-08-17

### macOS App Packaging

- Added `--app` / `--no-stdin` mode so Lumen can run from Finder without terminal stdin.
- Added `scripts/build_macos_app.sh` to build `dist/macos/Lumen.app`.
- The app wrapper launches `uv run python -m lumen.main --app`, opens the local web console, enables the overlay, and writes logs to `~/Library/Logs/Lumen/lumen.log`.
- Updated the hosted installer to install `Lumen.app` into `~/Applications`.

### Packaging Boundary

This is a repo-backed app wrapper, not a fully self-contained signed/notarized `.dmg`. It still requires `uv`, the local repo checkout, and separate local model installation.

### Public Download Boundary

- Added `/download` on the Cloudflare Worker as the user-facing installer download route.
- `/download` serves the same shell installer as `/install.sh`, but names it `lumen-installer.sh`.
- Updated the public Lumen site to show an installer manifest: it clones or updates the repo, runs `uv sync`, builds `Lumen.app`, and installs it into `~/Applications`.
- Made the page explicit that the download is not a signed DMG yet and does not include models, secrets, Ollama, LM Studio, or Whisper model weights.
