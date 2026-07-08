"""Microphone recording for push-to-talk commands."""

from __future__ import annotations

import os
import tempfile
import time


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


def record_command_wav(
    *,
    max_seconds: float = 12.0,
    silence_seconds: float = 0.8,
    silence_threshold: float = 0.012,
    sample_rate: int = 16_000,
    block_seconds: float = 0.12,
) -> str:
    """Record until speech trails into silence, then return a WAV path.

    This is a lightweight voice activity detector based on RMS amplitude. It is
    intentionally simple: enough to stop waiting for a fixed five-second window
    during command capture, without adding another model dependency.
    """
    if max_seconds <= 0:
        raise ValueError("Maximum recording duration must be positive.")
    if silence_seconds <= 0:
        raise ValueError("Silence duration must be positive.")

    try:
        import numpy as np
        import sounddevice as sd
        from scipy.io.wavfile import write as write_wav
    except ImportError as exc:
        raise VoiceDependencyError(
            "Voice recording needs `sounddevice`, `numpy`, and `scipy`. Install with `uv sync --extra voice`."
        ) from exc

    block_size = max(1, int(sample_rate * block_seconds))
    max_blocks = max(1, int(max_seconds / block_seconds))
    silence_blocks_needed = max(1, int(silence_seconds / block_seconds))
    pre_roll_blocks = max(1, int(0.35 / block_seconds))

    frames: list[np.ndarray] = []
    pre_roll: list[np.ndarray] = []
    silence_blocks = 0
    heard_voice = False

    print(f"Listening for up to {max_seconds:g}s...")
    start = time.monotonic()
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", blocksize=block_size) as stream:
        for _ in range(max_blocks):
            block, _ = stream.read(block_size)
            rms = float(np.sqrt(np.mean(np.square(block))))

            if not heard_voice:
                pre_roll.append(block.copy())
                pre_roll = pre_roll[-pre_roll_blocks:]
                if rms >= silence_threshold:
                    heard_voice = True
                    frames.extend(pre_roll)
                    pre_roll.clear()
                elif time.monotonic() - start >= max_seconds:
                    break
                continue

            frames.append(block.copy())
            if rms < silence_threshold:
                silence_blocks += 1
                if silence_blocks >= silence_blocks_needed:
                    break
            else:
                silence_blocks = 0

    if not frames:
        raise VoiceDependencyError("No speech detected. Try again closer to the microphone.")

    audio = np.concatenate(frames, axis=0)
    fd, path = tempfile.mkstemp(prefix="lumen-voice-", suffix=".wav")
    os.close(fd)
    write_wav(path, sample_rate, audio)
    duration = len(audio) / sample_rate
    print(f"Captured {duration:.1f}s.")
    return path
