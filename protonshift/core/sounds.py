"""Interface sounds model: sound sets, sound types, and the stored settings.

Mirrors MineUI's App Settings -> Sounds: an on/off switch, a 0-100 volume and
a choice of sound set, stored on this machine. Pure Python - no PySide6 import
here, so this is exercised directly in tests/test_sounds.py without a
QApplication. ``SoundController`` (``controllers/sound_controller.py``) is the
only consumer: it loads/saves settings.json through this module and plays the
files with Qt Multimedia.

Every set ships the same files under ``qml/assets/sounds/<id>/<type>.wav`` at
matched loudness (``scripts/gen-ui-sounds.py`` synthesizes them), so the
per-sound volumes below hold for all sets and switching sets does not change
how loud the app is.
"""

from __future__ import annotations

import math
from pathlib import Path

SOUNDS_DIR = Path(__file__).resolve().parent.parent / "qml" / "assets" / "sounds"

# Ordered registry of sound sets offered in Settings.
SOUND_SETS: list[dict[str, str]] = [
    {
        "id": "pulse",
        "label": "Pulse",
        "description": "Short synth plucks, the ProtonShift default.",
    },
    {
        "id": "glass",
        "label": "Glass",
        "description": "Soft bells with gentle tails.",
    },
    {
        "id": "terminal",
        "label": "Terminal",
        "description": "Relay ticks and terse beeps.",
    },
]

_SET_IDS = {s["id"] for s in SOUND_SETS}
DEFAULT_SOUND_SET = "pulse"
DEFAULT_VOLUME = 70

# Sound type -> its own level (0..1), multiplied by the user's volume. Quiet
# for the sounds heard constantly (slider ticks), fuller for the rare ones.
SOUND_TYPES: dict[str, float] = {
    "click": 0.5,
    "back": 0.4,
    "toggle_on": 0.5,
    "toggle_off": 0.45,
    "slider": 0.25,
    "success": 0.55,
    "error": 0.5,
    "notification": 0.5,
}

# Minimum seconds between two plays of the same type, for the sounds a held
# key or a dragged slider would otherwise machine-gun.
THROTTLE_SECONDS: dict[str, float] = {
    "slider": 0.05,
    "click": 0.05,
    "back": 0.05,
}


def sound_path(set_id: str, sound_type: str) -> Path:
    """File of one sound in one set (unknown ids fall back to the default set)."""
    if set_id not in _SET_IDS:
        set_id = DEFAULT_SOUND_SET
    return SOUNDS_DIR / set_id / f"{sound_type}.wav"


def clamp_volume(value: object) -> int:
    """Coerce anything to a whole 0-100 volume (the default when unparseable)."""
    if isinstance(value, bool):
        return DEFAULT_VOLUME
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_VOLUME
    if not math.isfinite(number):
        return DEFAULT_VOLUME
    return int(min(100, max(0, round(number))))


def effective_volume(sound_type: str, volume: int) -> float:
    """The 0..1 gain to play ``sound_type`` at for a 0-100 user volume."""
    return SOUND_TYPES.get(sound_type, 0.0) * (clamp_volume(volume) / 100)


def normalize(settings: dict) -> dict:
    """Return a valid ``{enabled, volume, set}`` dict loaded from settings.json.

    Tolerant of missing/malformed input at every level: an absent or corrupt
    ``sounds`` block, a non-boolean switch, an out-of-range volume or a retired
    set id all fall back to the defaults rather than raising.
    """
    stored = settings.get("sounds") if isinstance(settings, dict) else None
    if not isinstance(stored, dict):
        stored = {}
    enabled = stored.get("enabled")
    set_id = stored.get("set")
    return {
        "enabled": enabled if isinstance(enabled, bool) else True,
        "volume": clamp_volume(stored.get("volume", DEFAULT_VOLUME)),
        "set": set_id if set_id in _SET_IDS else DEFAULT_SOUND_SET,
    }
