"""Appearance model: visual styles, accent color, and dark/light/system mode.

Replaces the old six-fixed-palette scheme with a MineUI-style split: a
handful of visual STYLES (each carrying its own shape/neutral personality and
a default accent color), a user-overridable ACCENT, and a MODE
(system/dark/light) applied independently of style. Pure Python — no PySide6
import here, so this is exercised directly in tests/test_appearance.py
without a QApplication.

``ThemeController`` (``protonshift/controllers/theme_controller.py``) is the
only consumer: it loads/saves settings.json through this module and exposes
the resolved values to QML, which reads them via ``Theme.qml``'s `style`,
`dark`, and `accent` inputs.
"""

from __future__ import annotations

import re

MODES: tuple[str, ...] = ("system", "dark", "light")

# Ordered registry of visual styles. `default_accent_dark`/`default_accent_light`
# are the accent used when the user hasn't overridden one, chosen per resolved
# mode since a style's default accent is tuned for contrast against that
# style's dark or light neutrals.
STYLES: list[dict[str, str]] = [
    {
        "id": "neon",
        "label": "Proton Neon",
        "tagline": "Ambient glow, gradient buttons — the ProtonShift look.",
        "default_accent_dark": "#22c3e6",
        "default_accent_light": "#0891b2",
    },
    {
        "id": "console",
        "label": "Phosphor Console",
        "tagline": "Near-black, hairline borders, zero shadows.",
        "default_accent_dark": "#ffb224",
        "default_accent_light": "#b45309",
    },
    {
        "id": "soft",
        "label": "Soft Glass",
        "tagline": "Calm, rounded, native-grade.",
        "default_accent_dark": "#ff9f5a",
        "default_accent_light": "#ea580c",
    },
    {
        "id": "slate",
        "label": "Deepslate",
        "tagline": "Flat, tight radius, emerald signal.",
        "default_accent_dark": "#3ddc84",
        "default_accent_light": "#15803d",
    },
]

_STYLE_IDS = {s["id"] for s in STYLES}
_DEFAULT_STYLE = "neon"

# Named accent swatches offered as one-tap presets in the Settings page.
ACCENT_PRESETS: list[dict[str, str]] = [
    {"name": "Cyan", "hex": "#22c3e6"},
    {"name": "Magenta", "hex": "#de3eb8"},
    {"name": "Violet", "hex": "#8b5cf6"},
    {"name": "Teal", "hex": "#2dd4bf"},
    {"name": "Emerald", "hex": "#3ddc84"},
    {"name": "Amber", "hex": "#ffb224"},
    {"name": "Apricot", "hex": "#ff9f5a"},
    {"name": "Rose", "hex": "#fb7185"},
]

_HEX3_RE = re.compile(r"^#([0-9a-fA-F]{3})$")
_HEX6_RE = re.compile(r"^#([0-9a-fA-F]{6})$")


def parse_accent(text: str | None) -> str | None:
    """Validate/normalize a user-typed accent color.

    Accepts `#rgb` or `#rrggbb` (case-insensitive) and returns a normalized
    lowercase `#rrggbb` string. Returns None for anything else (wrong shape,
    non-hex digits, empty/missing input) so the caller can reject the edit
    without guessing at a fallback color.
    """
    if not isinstance(text, str):
        return None
    value = text.strip()
    m3 = _HEX3_RE.match(value)
    if m3:
        r, g, b = m3.group(1)
        return f"#{r}{r}{g}{g}{b}{b}".lower()
    m6 = _HEX6_RE.match(value)
    if m6:
        return f"#{m6.group(1)}".lower()
    return None


# Legacy `theme` choice (a palette id, or "system") -> new (style, mode, accent).
# `accent` is None when the legacy palette's hue is now a style's own default
# (so the user keeps seeing "no override"); it's set explicitly only where the
# legacy palette's accent doesn't match any style default (violet/teal picks
# that used to be baked into their own palette).
_LEGACY_MAP: dict[str, tuple[str, str, str | None]] = {
    "proton-neon": ("neon", "dark", None),
    "violet-night": ("neon", "dark", "#8b5cf6"),
    "deep-sea": ("neon", "dark", "#2dd4bf"),
    "proton-day": ("neon", "light", None),
    "violet-day": ("neon", "light", "#8b5cf6"),
    "sandstone": ("soft", "light", None),
    "system": ("neon", "system", None),
}


def migrate_legacy(theme: str) -> dict:
    """Map a legacy `theme` setting to the new `{style, mode, accent}` model.

    Unknown/unrecognized values (including a corrupt or absent setting) fall
    back to the same default as "system": neon style, system mode, no accent
    override.
    """
    style, mode, accent = _LEGACY_MAP.get(theme, ("neon", "system", None))
    return {"style": style, "mode": mode, "accent": accent}


def normalize(settings: dict) -> dict:
    """Return a valid `{style, mode, accent}` dict loaded from settings.json.

    Prefers `settings["appearance"]` (the current shape); falls back to
    migrating the legacy `settings["theme"]` key when it's absent. Tolerant
    of missing/malformed input at every level: a corrupt or partial
    `appearance` block, an unknown style/mode id, or an unparseable accent
    all fall back to a sane default rather than raising.
    """
    appearance = settings.get("appearance") if isinstance(settings, dict) else None
    if isinstance(appearance, dict):
        style = appearance.get("style")
        mode = appearance.get("mode")
        accent = appearance.get("accent")
    else:
        legacy_choice = settings.get("theme") if isinstance(settings, dict) else "system"
        legacy = migrate_legacy(legacy_choice if isinstance(legacy_choice, str) else "system")
        style, mode, accent = legacy["style"], legacy["mode"], legacy["accent"]

    if style not in _STYLE_IDS:
        style = _DEFAULT_STYLE
    if mode not in MODES:
        mode = "system"
    accent = parse_accent(accent) if accent else None

    return {"style": style, "mode": mode, "accent": accent}
