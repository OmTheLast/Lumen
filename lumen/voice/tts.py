"""Text-to-speech output."""

from __future__ import annotations

import subprocess


def speak(text: str, voice: str | None = None) -> None:
    """Speak text using macOS `say`."""
    text = text.strip()
    if not text:
        return

    cmd = ["say"]
    if voice:
        cmd.extend(["-v", voice])
    cmd.append(text)
    subprocess.run(cmd, check=False)

