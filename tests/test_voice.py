import pytest

from lumen.config import Config
from lumen.main import _parse_voice_command, _parse_voice_seconds


def test_parse_default_voice_seconds_compatibility():
    assert _parse_voice_seconds("/voice") == 5.0


def test_parse_default_voice_command_uses_auto_mode():
    mode = _parse_voice_command("/voice")

    assert mode.seconds is None
    assert mode.max_seconds == Config().voice_auto_max_seconds


def test_parse_auto_voice_command():
    mode = _parse_voice_command("/voice auto")

    assert mode.seconds is None


def test_parse_voice_seconds_bounds():
    assert _parse_voice_seconds("/voice 0.2") == 1.0
    assert _parse_voice_seconds("/voice 45") == 30.0


def test_parse_voice_seconds_rejects_non_number():
    with pytest.raises(ValueError):
        _parse_voice_seconds("/voice now")
