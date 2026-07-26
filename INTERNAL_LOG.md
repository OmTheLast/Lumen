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
