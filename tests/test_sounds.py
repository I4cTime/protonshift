"""Tests for the pure-Python interface-sounds model (`core/sounds.py`).

Qt-free, like the rest of this package. Also checks that every sound set
ships every sound file, so a missing asset fails here rather than as a silent
click in the app.
"""

from __future__ import annotations

import wave

import pytest

from protonshift.core.sounds import (
    DEFAULT_SOUND_SET,
    DEFAULT_VOLUME,
    SOUND_SETS,
    SOUND_TYPES,
    THROTTLE_SECONDS,
    clamp_volume,
    effective_volume,
    normalize,
    sound_path,
)


def test_registry_shape() -> None:
    ids = [s["id"] for s in SOUND_SETS]
    assert ids[0] == DEFAULT_SOUND_SET
    assert len(ids) == len(set(ids))
    for entry in SOUND_SETS:
        assert entry["label"]
        assert entry["description"]
    assert set(THROTTLE_SECONDS) <= set(SOUND_TYPES)
    for level in SOUND_TYPES.values():
        assert 0 < level <= 1


@pytest.mark.parametrize("set_id", [s["id"] for s in SOUND_SETS])
def test_every_set_ships_every_sound(set_id: str) -> None:
    for sound_type in SOUND_TYPES:
        path = sound_path(set_id, sound_type)
        assert path.is_file(), path
        with wave.open(str(path), "rb") as wav:  # QSoundEffect needs plain PCM WAV
            assert wav.getsampwidth() == 2
            assert wav.getnframes() > 0


def test_sound_path_unknown_set_falls_back() -> None:
    assert sound_path("../etc", "click") == sound_path(DEFAULT_SOUND_SET, "click")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0), (100, 100), (70.4, 70), (-5, 0), (250, 100), ("35", 35),
     ("loud", DEFAULT_VOLUME), (None, DEFAULT_VOLUME), (True, DEFAULT_VOLUME), (float("nan"), DEFAULT_VOLUME),
     (float("inf"), DEFAULT_VOLUME)],
)
def test_clamp_volume(value: object, expected: int) -> None:
    assert clamp_volume(value) == expected


def test_effective_volume() -> None:
    assert effective_volume("click", 100) == SOUND_TYPES["click"]
    assert effective_volume("click", 0) == 0
    assert effective_volume("click", 50) == pytest.approx(SOUND_TYPES["click"] / 2)
    assert effective_volume("no-such-sound", 100) == 0


def test_normalize_defaults() -> None:
    expected = {"enabled": True, "volume": DEFAULT_VOLUME, "set": DEFAULT_SOUND_SET}
    assert normalize({}) == expected
    assert normalize({"sounds": "corrupt"}) == expected
    assert normalize(None) == expected  # type: ignore[arg-type]


def test_normalize_keeps_valid_and_repairs_invalid() -> None:
    assert normalize({"sounds": {"enabled": False, "volume": 35, "set": "glass"}}) == {
        "enabled": False, "volume": 35, "set": "glass",
    }
    assert normalize({"sounds": {"enabled": "yes", "volume": 900, "set": "retired"}}) == {
        "enabled": True, "volume": 100, "set": DEFAULT_SOUND_SET,
    }
