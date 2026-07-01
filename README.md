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
/voice 5
```

Lumen records five seconds from the microphone, transcribes with `mlx-whisper`, executes the command, and speaks the response with macOS `say`.

The first transcription may take longer while the Whisper model downloads.
