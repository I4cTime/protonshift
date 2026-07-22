"""Parity checks between the QML design-token singleton and the Python
theme controller.

Pure-text tests — no Qt required:
  1. Every palette in Theme.qml defines the identical key set (a palette
     missing a token would silently resolve to black/undefined at runtime).
  2. The palette ids in Theme.qml match the ids the ThemeController offers
     in its picker model (`_THEMES`), so neither side can drift when a
     palette is added or renamed.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME_QML = REPO / "protonshift" / "qml" / "App" / "Theme.qml"
CONTROLLER = REPO / "protonshift" / "controllers" / "theme_controller.py"

# Matches a palette entry inside the `palettes` map:  "some-id": { ... }
# Palette bodies are flat (no nested braces), so a non-greedy brace match
# is sufficient and keeps the test independent of formatting.
_PALETTE_RE = re.compile(r'"([a-z0-9-]+)"\s*:\s*\{(.*?)\}', re.DOTALL)
# Matches a token key at the start of a `key: value` pair within a body.
_KEY_RE = re.compile(r"(?:^|[,{])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:")
# Matches the ids declared in theme_controller._THEMES.
_CONTROLLER_ID_RE = re.compile(r'\{\s*"id"\s*:\s*"([a-z0-9-]+)"')


def _palettes_block(qml: str) -> str:
    start = qml.index("palettes: ({")
    end = qml.index("})", start)
    return qml[start:end]


def _qml_palettes() -> dict[str, set[str]]:
    block = _palettes_block(THEME_QML.read_text(encoding="utf-8"))
    palettes: dict[str, set[str]] = {}
    for pid, body in _PALETTE_RE.findall(block):
        # strip comments so a commented-out `key:` can't count
        body = re.sub(r"//[^\n]*", "", body)
        palettes[pid] = set(_KEY_RE.findall(body))
    return palettes


def _controller_ids() -> list[str]:
    src = CONTROLLER.read_text(encoding="utf-8")
    # Slice from the opening bracket of the assignment (not the type
    # annotation's `list[dict]`) to the closing bracket at column 0.
    start = src.index("[", src.index("=", src.index("_THEMES")))
    end = src.index("\n]", start)
    return _CONTROLLER_ID_RE.findall(src[start:end])


def test_palettes_share_identical_key_sets() -> None:
    palettes = _qml_palettes()
    assert len(palettes) >= 2, "expected multiple palettes in Theme.qml"
    reference_id = next(iter(palettes))
    reference = palettes[reference_id]
    assert reference, "reference palette parsed as empty"
    for pid, keys in palettes.items():
        missing = reference - keys
        extra = keys - reference
        assert not missing and not extra, (
            f"palette {pid!r} diverges from {reference_id!r}: "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )


def test_required_tokens_present_in_every_palette() -> None:
    required = {
        # base
        "dark", "ambient", "bg", "bgDeep", "surface", "surfaceElevated",
        "border", "borderStrong",
        "primary", "primaryBright", "primaryDeep", "glow",
        "text", "muted", "faint",
        "success", "danger", "gradA", "gradB", "accent", "accentBright",
        # contract additions
        "onPrimary", "wordmark", "knob",
        "warning", "warningSurface", "warningBorder", "dangerSurface",
        "scrim", "shadow", "shadowOpacity",
    }
    for pid, keys in _qml_palettes().items():
        missing = required - keys
        assert not missing, f"palette {pid!r} missing tokens: {sorted(missing)}"


def test_controller_theme_ids_match_qml_palettes() -> None:
    qml_ids = set(_qml_palettes())
    controller_ids = _controller_ids()
    assert controller_ids, "no ids parsed from theme_controller._THEMES"
    assert len(controller_ids) == len(set(controller_ids)), (
        f"duplicate ids in _THEMES: {controller_ids}"
    )
    assert set(controller_ids) == qml_ids, (
        f"theme_controller._THEMES {sorted(controller_ids)} != "
        f"Theme.qml palettes {sorted(qml_ids)}"
    )
