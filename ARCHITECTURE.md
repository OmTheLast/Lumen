# Lumen Architecture Plan

Date: 2026-06-30
Machine: Mac Studio, Apple M4 Max, 16 CPU cores, 64 GB unified memory

## Goal

Build a local-first autonomous desktop agent that can listen for voice commands, reason about tasks, operate macOS applications and browsers, inspect the screen, manipulate files, and ask for confirmation before risky actions.

The current `legacy_phase2.py` is a useful Phase 2 prototype: terminal chat, Ollama backend, bounded history, and a small tool layer. The newer package code splits that prototype into services.

## Local Model Prerequisites

Models are runtime prerequisites, not repository assets. Do not commit Ollama, LM Studio, Hugging Face, Whisper, GGUF, safetensors, or checkpoint files.

### Recommended Ollama models

Ollama should be installed and running on `http://localhost:11434`.

| Model | Size | Params | Context | Quant | Capabilities | Recommended role |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `qwen3.6:27b` | 17 GB | 27.8B | 262K | Q4_K_M | completion, vision, tools, thinking | Primary planner/orchestrator |
| `qwen3.5:27b-q4_k_m` | 17 GB | 27.8B | 262K | Q4_K_M | completion, vision, tools, thinking | Backup planner |
| `qwq:32b-q4_k_m` | 19 GB | 32.8B | 40K | Q4_K_M | completion, tools, thinking | Deep reasoning fallback |
| `qwen2.5:7b` | 4.7 GB | 7.6B | 32K | Q4_K_M | completion, tools | Fast command parser/router |
| `qwen3:latest` | 5.2 GB | 8.2B | 40K | Q4_K_M | completion, tools, thinking | Fast everyday assistant |

### Optional LM Studio models

LM Studio is installed, but its local server is not currently running and no LM Studio models are loaded.

| Model | Size | Recommended role |
| --- | ---: | --- |
| `qwen/qwen3.6-35b-a3b` GGUF | 22.07 GB | Alternative high-quality local planner |
| `openai/gpt-oss-20b` MLX | 12.10 GB | MLX backend experiments |
| `text-embedding-nomic-embed-text-v1.5` | 84 MB | Local semantic memory/search embeddings |

## Current Dependency Inventory

Installed:

- `uv`
- Python 3.13.11
- `mlx`
- `mlx_lm`
- `sounddevice`
- PyObjC pieces: `AppKit`, `Quartz`, `Foundation`
- Homebrew `ffmpeg`
- Homebrew `tesseract`
- Node 25.2.1

Installed in the project voice environment:

- `mlx-whisper`
- `numpy`
- `scipy`
- `sounddevice`

Still missing or not implemented:

- Wake-word engine
- `playwright`
- `pyautogui` or `pynput`
- Durable memory database
- Permission-aware macOS automation wrapper

## Recommended High-Level Architecture

```text
Voice / Hotkey
    |
    v
Wake Word + STT
    |
    v
Intent Router
    |
    v
Planner LLM <----> Memory / App State / Screen State
    |
    v
Tool Broker / Safety Gate
    |
    +--> macOS Controller: AppleScript, Shortcuts, Accessibility, shell
    +--> Browser Controller: Playwright
    +--> Screen Controller: screenshots, OCR, vision model
    +--> File Controller: read/write/search/summarize
    +--> App Connectors: Mail, Calendar, Notes, Finder, Terminal, VS Code
    |
    v
Observation Log
    |
    v
Planner continues or reports completion
```

## Core Design Principles

1. Local-first by default, cloud-optional only for tasks that need it.
2. Separate planning from execution. The LLM proposes actions; a tool broker validates and runs them.
3. Use structured tool calls, not regex-parsed free text.
4. Every tool returns structured observations.
5. Risky actions require confirmation: shell commands, file overwrite/delete, sending messages, purchases, password/keychain access, network posts.
6. Keep a persistent audit log of every action and observation.
7. Prefer app-native APIs before screen clicking. Use GUI automation only when APIs are unavailable.
8. Use a small fast model for routing and a stronger model for planning.

## Recommended Model Roles

### Primary planner

Use `qwen3.6:27b`.

Reason: it is already local, runs through Ollama, advertises tool support, vision support, thinking, and a long context window.

### Fast router

Use `qwen3:latest` or `qwen2.5:7b`.

Reason: simple commands such as "open Chrome", "summarize this file", or "start a timer" should not pay the latency cost of a 27B model.

### Deep reasoning fallback

Use `qwq:32b-q4_k_m`.

Reason: useful for difficult planning, code reasoning, and multi-step decomposition. It has a smaller context than Qwen3.6, so it should not be the default for long workspace tasks.

### Embeddings and memory

Use LM Studio's `text-embedding-nomic-embed-text-v1.5` if served through LM Studio, or install an Ollama embedding model such as `nomic-embed-text`.

Reason: Lumen needs memory search over notes, files, previous tasks, app usage, and user preferences.

### Vision

Start with `qwen3.6:27b` screenshots if Ollama handles image input reliably in the local API.

Add a dedicated vision model later if screenshot understanding becomes slow or inaccurate.

## Additional Models / Tools To Add

### Required for voice

- Local STT: `mlx-whisper` or `lightning-whisper-mlx`
- Wake word: `openwakeword` or a small always-listening hotkey-first mode
- TTS: macOS `say` first; later Kokoro/Piper/KittenTTS or another local neural voice
- Audio I/O: existing `sounddevice` is enough for first prototype

Recommended first choice: `mlx-whisper`, because this machine is Apple Silicon and MLX is already installed.

### Required for browser control

- `playwright`
- Playwright browser binaries

Use Playwright for tabs, forms, scraping, logins where a browser session is already authenticated, and deterministic web automation.

### Required for desktop control

- AppleScript through `osascript`
- macOS Shortcuts integration
- PyObjC Accessibility wrappers
- Screenshot capture through `screencapture` or Quartz
- OCR through existing `tesseract`

Use this order for desktop actions:

1. App API or URL scheme
2. AppleScript / Shortcuts
3. Accessibility tree
4. OCR + click coordinates

### Required for memory

- SQLite for action log and task state
- Vector store: sqlite-vss, LanceDB, Chroma, or a simple NumPy index to start
- Embedding model served locally

### Required for safety

- Tool allowlist
- Path allowlist / protected path denylist
- Confirmation policy by risk level
- Dry-run previews for destructive or external actions
- Emergency stop hotkey

## Proposed Repository Structure

```text
Lumen/
  legacy_phase2.py          # legacy prototype
  pyproject.toml
  README.md
  ARCHITECTURE.md
  lumen/
    __init__.py
    main.py                  # CLI/service entrypoint
    config.py
    llm/
      ollama_client.py
      lmstudio_client.py
      router.py
    agent/
      planner.py
      tool_broker.py
      schemas.py
      safety.py
    tools/
      shell.py
      apps.py
      browser.py
      files.py
      screen.py
      memory.py
      voice.py
    voice/
      wake.py
      stt.py
      tts.py
    memory/
      db.py
      embeddings.py
    ui/
      tray.py
  tests/
```

## Build Phases

### Phase 3: Stabilize the agent core

- Replace regex tool parsing with JSON/schema tool calls.
- Split the one-file script into modules.
- Add `pyproject.toml` and dependency management with `uv`.
- Add structured logs and action history.
- Add tests for tool parsing, safety policy, and history trimming.

### Phase 4: Desktop and browser control

- Add app opening/window focusing through AppleScript.
- Add browser automation through Playwright.
- Add screenshot + OCR + vision observation.
- Add a permission checklist for Accessibility, Screen Recording, Microphone, and Automation.

### Phase 5: Voice loop

- Push-to-talk first.
- Add streaming microphone capture.
- Add local STT.
- Add wake word only after the push-to-talk voice path is reliable.
- Add TTS responses with macOS `say`.

### Phase 6: Memory and preferences

- Add SQLite action/task log.
- Add semantic memory.
- Store user preferences, recurring workflows, app aliases, and common paths.

### Phase 7: Autonomy

- Add task queue.
- Add monitors and scheduled checks.
- Add background execution with notifications.
- Add long-running task resume.
- Add a visible audit dashboard.

## First Implementation Target

The next concrete milestone should be:

> "Lumen, open Safari and search for X" from terminal or push-to-talk.

That requires:

- Structured agent loop
- `open_app`
- Playwright browser control
- Basic safety broker
- Optional TTS

Voice wake-word autonomy should come after this works reliably with text and push-to-talk.
