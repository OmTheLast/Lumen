"""Microphone recording for push-to-talk commands."""

from __future__ import annotations

import os
import tempfile


class VoiceDependencyError(RuntimeError):
    """Raised when optional voice dependencies are not installed."""


def record_wav(seconds: float = 5.0, sample_rate: int = 16_000) -> str:
    """Record microphone audio to a temporary WAV file and return the path."""
    if seconds <= 0:
        raise ValueError("Recording duration must be positive.")

    try:
        import sounddevice as sd
        from scipy.io.wavfile import write as write_wav
    except ImportError as exc:
        raise VoiceDependencyError(
            "Voice recording needs `sounddevice` and `scipy`. Install with `uv sync --extra voice`."
        ) from exc

    print(f"Recording for {seconds:g}s...")
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()

    fd, path = tempfile.mkstemp(prefix="lumen-voice-", suffix=".wav")
    os.close(fd)
    write_wav(path, sample_rate, audio)
    return path

