"""Speech-to-text adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SpeechToTextError(RuntimeError):
    """Raised when transcription cannot run."""


@dataclass(frozen=True)
class Transcription:
    text: str
    backend: str
    raw: dict[str, Any]


class MlxWhisperTranscriber:
    def __init__(
        self,
        model: str = "mlx-community/whisper-tiny",
        language: str | None = "en",
    ) -> None:
        self.model = model
        self.language = language

    def transcribe(self, audio_path: str) -> Transcription:
        try:
            import mlx_whisper
        except ImportError as exc:
            raise SpeechToTextError(
                "Speech-to-text needs `mlx-whisper`. Install with `uv sync --extra voice`."
            ) from exc

        kwargs: dict[str, Any] = {"path_or_hf_repo": self.model}
        if self.language:
            kwargs["language"] = self.language

        try:
            result = mlx_whisper.transcribe(audio_path, **kwargs)
        except Exception as exc:
            raise SpeechToTextError(f"Transcription failed: {exc}") from exc

        if not isinstance(result, dict):
            raise SpeechToTextError(f"Unexpected transcription result: {type(result).__name__}")

        text = result.get("text")
        if not isinstance(text, str) or not text.strip():
            raise SpeechToTextError("No speech detected.")

        return Transcription(text=text.strip(), backend=f"mlx-whisper:{self.model}", raw=result)
