import pytest

from lumen.main import _parse_voice_seconds


def test_parse_default_voice_seconds():
    assert _parse_voice_seconds("/voice") == 5.0


def test_parse_voice_seconds_bounds():
    assert _parse_voice_seconds("/voice 0.2") == 1.0
    assert _parse_voice_seconds("/voice 45") == 30.0


def test_parse_voice_seconds_rejects_non_number():
    with pytest.raises(ValueError):
        _parse_voice_seconds("/voice now")

