# Lumen

Local-first macOS desktop agent prototype.

The legacy Phase 2 prototype is still in `legacy_phase2.py`. The newer modular agent lives in the `lumen/` package.

## Prerequisites

- macOS on Apple Silicon
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) running locally
- A local planner model, recommended:

```sh
ollama pull qwen3.6:27b
ollama pull qwen3:latest
```

Model weights are intentionally not stored in this repository. Keep Ollama, LM Studio, Whisper, and other model caches outside git.

## Run

```sh
cd /Users/ompatnaik/Documents/Code/Lumen
uv run python -m lumen.main
```

Lumen starts a local presence page at `http://127.0.0.1:8765` and opens it in your browser. The page shows Lumen's current state and a bottom-right icon that animates while it listens, thinks, acts, or speaks.

Lumen also starts a native always-on-top orb at the bottom-right of your screen. It uses the same state as the web page, so it stays visible even when the browser is behind other windows.

The native orb reads from the local presence server, so disabling the UI also disables the orb.

To run without opening the browser:

```sh
LUMEN_UI_OPEN_BROWSER=0 uv run python -m lumen.main
```

To disable the UI entirely:

```sh
LUMEN_UI_ENABLED=0 uv run python -m lumen.main
```

To disable only the native orb:

```sh
LUMEN_OVERLAY_ENABLED=0 uv run python -m lumen.main
```

Try:

```text
open Safari
search the web for Apple Silicon MLX Whisper
open Chrome and search for local LLM agents
take a screenshot called desktop
```

Riskier tools such as shell commands and file writes ask for confirmation.

## Voice

Voice is optional. Install the voice dependencies with:

```sh
uv sync --extra voice
```

Then run Lumen and use:

```text
/voice
```

Lumen records until you stop speaking, transcribes with `mlx-whisper`, executes the command, and speaks the response with macOS `say`.

To force a fixed recording window:

```text
/voice 5
```

The default speech-to-text model is `mlx-community/whisper-tiny` for speed. You can override it:

```sh
LUMEN_VOICE_STT_MODEL=mlx-community/whisper-small-mlx uv run python -m lumen.main
```

The first transcription may take longer while the Whisper model downloads.
