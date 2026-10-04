"""Tests for the pure-Python appearance model (`core/appearance.py`).

Qt-free: no PySide6 import anywhere in `core/appearance.py`, so this runs
without a QApplication/display, same as every other test in this package.
"""

from __future__ import annotations

import pytest

from protonshift.core.appearance import (
    ACCENT_PRESETS,
    MODES,
    STYLES,
    migrate_legacy,
    normalize,
    parse_accent,
    readable_on_light,
)


def test_styles_registry_shape() -> None:
    assert [s["id"] for s in STYLES] == ["neon", "console", "soft", "slate"]
    for entry in STYLES:
        assert entry["label"]
        assert entry["tagline"]
        assert parse_accent(entry["default_accent_dark"]) == entry["default_accent_dark"]
        assert parse_accent(entry["default_accent_light"]) == entry["default_accent_light"]


def test_modes() -> None:
    assert MODES == ("system", "dark", "light")


def test_accent_presets() -> None:
    assert len(ACCENT_PRESETS) == 8
    for preset in ACCENT_PRESETS:
        assert parse_accent(preset["hex"]) == preset["hex"]


# --- parse_accent -----------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#22c3e6", "#22c3e6"),
        ("#22C3E6", "#22c3e6"),
        ("#2ce", "#22ccee"),
        ("#2CE", "#22ccee"),
        ("  #22c3e6  ", "#22c3e6"),
        ("#000000", "#000000"),
        ("#fff", "#ffffff"),
    ],
)
def test_parse_accent_valid(text: str, expected: str) -> None:
    assert parse_accent(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "red",
        "22c3e6",
        "#22c3e",
        "#22c3e60",
        "#gggggg",
        "#ggg",
        "",
        "   ",
        None,
        123,
        "#22c3e6ff",
    ],
)
def test_parse_accent_invalid(text) -> None:
    assert parse_accent(text) is None


# --- migrate_legacy -----------------------------------------------------------


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        ("proton-neon", {"style": "neon", "mode": "dark", "accent": None}),
        ("violet-night", {"style": "neon", "mode": "dark", "accent": "#8b5cf6"}),
        ("deep-sea", {"style": "neon", "mode": "dark", "accent": "#2dd4bf"}),
        ("proton-day", {"style": "neon", "mode": "light", "accent": None}),
        ("violet-day", {"style": "neon", "mode": "light", "accent": "#8b5cf6"}),
        ("sandstone", {"style": "soft", "mode": "light", "accent": None}),
        ("system", {"style": "neon", "mode": "system", "accent": None}),
        ("unknown-palette", {"style": "neon", "mode": "system", "accent": None}),
        ("", {"style": "neon", "mode": "system", "accent": None}),
    ],
)
def test_migrate_legacy(legacy: str, expected: dict) -> None:
    assert migrate_legacy(legacy) == expected


# --- normalize -----------------------------------------------------------------


def test_normalize_prefers_appearance_block() -> None:
    settings = {
        "appearance": {"style": "slate", "mode": "light", "accent": "#3ddc84"},
        "theme": "sandstone",  # should be ignored - appearance block wins
    }
    assert normalize(settings) == {"style": "slate", "mode": "light", "accent": "#3ddc84"}


def test_normalize_falls_back_to_legacy_theme() -> None:
    assert normalize({"theme": "violet-night"}) == {
        "style": "neon",
        "mode": "dark",
        "accent": "#8b5cf6",
    }


def test_normalize_no_settings_defaults_to_system() -> None:
    assert normalize({}) == {"style": "neon", "mode": "system", "accent": None}


def test_normalize_unknown_style_and_mode_fall_back() -> None:
    settings = {"appearance": {"style": "nope", "mode": "midnight", "accent": None}}
    assert normalize(settings) == {"style": "neon", "mode": "system", "accent": None}


def test_normalize_invalid_accent_becomes_none() -> None:
    settings = {"appearance": {"style": "console", "mode": "dark", "accent": "not-a-color"}}
    assert normalize(settings) == {"style": "console", "mode": "dark", "accent": None}


def test_normalize_accent_is_parsed_and_normalized() -> None:
    settings = {"appearance": {"style": "console", "mode": "dark", "accent": "#FFB"}}
    result = normalize(settings)
    assert result["accent"] == "#ffffbb"


def test_normalize_tolerates_malformed_appearance_block() -> None:
    assert normalize({"appearance": "not-a-dict", "theme": "deep-sea"}) == {
        "style": "neon",
        "mode": "dark",
        "accent": "#2dd4bf",
    }


def test_normalize_tolerates_non_dict_settings() -> None:
    assert normalize({}) == normalize({"garbage": True})


# --- readable_on_light --------------------------------------------------------


def _contrast_on_white(hex_color: str) -> float:
    def chan(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 1.05 / (0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b) + 0.05)


@pytest.mark.parametrize("preset", [p["hex"] for p in ACCENT_PRESETS] + ["#ffffff", "#ffff00"])
def test_readable_on_light_reaches_contrast(preset: str) -> None:
    assert _contrast_on_white(readable_on_light(preset)) >= 4.5


def test_readable_on_light_keeps_dark_colors_and_bad_input() -> None:
    assert readable_on_light("#15803d") == "#15803d"  # already readable: untouched
    assert readable_on_light("#000") == "#000000"
    assert readable_on_light("not-a-color") == "not-a-color"
