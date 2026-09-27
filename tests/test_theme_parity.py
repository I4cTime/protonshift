"""Parity checks between the QML design-token singleton and the Python
appearance model.

`core/appearance.py` is pure Python (no PySide6 import), so its STYLES
registry can be imported directly — no Qt needed. Theme.qml itself is parsed
as text/regex (same approach as before this file's rewrite), since it can't
be imported without a QML engine.

Checks:
  1. Every style id in `core/appearance.STYLES` has a matching entry in
     Theme.qml's `styles` table, and vice versa (neither side can drift when
     a style is added/renamed).
  2. Every style entry in Theme.qml defines both a `dark` and a `light`
     neutral sub-palette, and both hold the identical token key set.
"""

from __future__ import annotations

import re
from pathlib import Path

from protonshift.core.appearance import STYLES

REPO = Path(__file__).resolve().parent.parent
THEME_QML = REPO / "protonshift" / "qml" / "App" / "Theme.qml"

# Matches a style entry inside the `styles` map:  "some-id": { ... }
# Style bodies (including their nested dark/light sub-objects) are balanced
# on braces, so a manual brace-counting scan (rather than a single non-greedy
# regex) is needed to capture the whole entry, nested objects included.
_STYLE_START_RE = re.compile(r'"([a-z0-9-]+)"\s*:\s*\{')
# Matches a `dark: { ... }` or `light: { ... }` sub-object's opening brace.
_SUBPALETTE_START_RE = re.compile(r"\b(dark|light)\s*:\s*\{")
# Matches a token key at the start of a `key: value` pair within a body.
_KEY_RE = re.compile(r"(?:^|[,{])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:")


def _extract_braced_block(text: str, open_brace_index: int) -> str:
    """Return the `{...}` block starting at `open_brace_index` (inclusive)."""
    depth = 0
    for i in range(open_brace_index, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace_index : i + 1]
    raise AssertionError("unbalanced braces while parsing Theme.qml")


def _styles_block() -> str:
    qml = THEME_QML.read_text(encoding="utf-8")
    start = qml.index("readonly property var styles: ({")
    open_brace = qml.index("{", start)
    return _extract_braced_block(qml, open_brace)


def _qml_styles() -> dict[str, dict[str, set[str]]]:
    """id -> {"dark": token keys, "light": token keys}."""
    block = _styles_block()
    # strip comments so a commented-out entry/key can't count
    block = re.sub(r"//[^\n]*", "", block)
    styles: dict[str, dict[str, set[str]]] = {}
    for m in _STYLE_START_RE.finditer(block):
        style_id = m.group(1)
        body = _extract_braced_block(block, m.end() - 1)
        sub: dict[str, set[str]] = {}
        for sm in _SUBPALETTE_START_RE.finditer(body):
            mode = sm.group(1)
            sub_body = _extract_braced_block(body, sm.end() - 1)
            sub[mode] = set(_KEY_RE.findall(sub_body))
        styles[style_id] = sub
    return styles


def test_qml_styles_parsed() -> None:
    styles = _qml_styles()
    assert len(styles) >= 2, "expected multiple styles in Theme.qml"


def test_every_style_has_dark_and_light_subpalettes() -> None:
    for style_id, sub in _qml_styles().items():
        assert "dark" in sub, f"style {style_id!r} missing a dark sub-palette"
        assert "light" in sub, f"style {style_id!r} missing a light sub-palette"
        assert sub["dark"], f"style {style_id!r} dark sub-palette parsed as empty"
        assert sub["light"], f"style {style_id!r} light sub-palette parsed as empty"


def test_dark_and_light_subpalettes_share_identical_key_sets() -> None:
    for style_id, sub in _qml_styles().items():
        missing = sub["dark"] - sub["light"]
        extra = sub["light"] - sub["dark"]
        assert not missing and not extra, (
            f"style {style_id!r} dark/light sub-palettes diverge: "
            f"missing_from_light={sorted(missing)} extra_in_light={sorted(extra)}"
        )


def test_required_tokens_present_in_every_subpalette() -> None:
    required = {
        "bg", "bgDeep", "surface", "surfaceElevated", "border", "borderStrong",
        "text", "muted", "faint", "success", "danger",
        "warning", "warningSurface", "warningBorder", "dangerSurface",
        "scrim", "shadow", "shadowOpacity", "knob",
    }
    for style_id, sub in _qml_styles().items():
        for mode in ("dark", "light"):
            missing = required - sub[mode]
            assert not missing, f"style {style_id!r} {mode} sub-palette missing tokens: {sorted(missing)}"


def test_style_ids_match_core_appearance_styles() -> None:
    qml_ids = set(_qml_styles())
    core_ids = [s["id"] for s in STYLES]
    assert core_ids, "no styles found in core/appearance.STYLES"
    assert len(core_ids) == len(set(core_ids)), f"duplicate ids in STYLES: {core_ids}"
    assert set(core_ids) == qml_ids, (
        f"core/appearance.STYLES {sorted(core_ids)} != Theme.qml styles {sorted(qml_ids)}"
    )
