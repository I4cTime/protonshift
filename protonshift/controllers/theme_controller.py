"""QObject bridge for appearance: visual style, accent color, and mode.

Persists ``{style, mode, accent}`` under the ``appearance`` key in
``~/.config/protonshift/settings.json`` and resolves "system" mode to a
concrete dark/light choice from the OS color scheme, updating live when the
desktop flips between light and dark. A legacy ``theme`` key (six fixed
palette ids, or "system") is still read for migration on first load, but is
never written back — new saves only ever write ``appearance``.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ..core import appearance as appearance_core
from ..core.fsutil import atomic_write_text

_SETTINGS = Path.home() / ".config" / "protonshift" / "settings.json"


class ThemeController(QObject):
    styleChanged = Signal()
    modeChanged = Signal()
    accentChanged = Signal()    # the override (or lack of one) + accentError
    resolvedChanged = Signal()  # resolvedDark / resolvedAccent / styles (mode-dependent defaults)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        resolved = appearance_core.normalize(self._read_settings())
        self._style = resolved["style"]
        self._mode = resolved["mode"]
        self._accent = resolved["accent"] or ""
        self._accent_error = ""
        hints = QGuiApplication.styleHints()
        if hints is not None:
            hints.colorSchemeChanged.connect(self._on_scheme_changed)

    # --- persistence ------------------------------------------------------

    @staticmethod
    def _read_settings() -> dict:
        try:
            data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        existing = self._read_settings()
        existing["appearance"] = {
            "style": self._style,
            "mode": self._mode,
            "accent": self._accent or None,
        }
        try:
            # L8: atomic replace (same contract as every other config write) —
            # a crash mid-write can't corrupt settings.json.
            atomic_write_text(_SETTINGS, json.dumps(existing, indent=2))
        except OSError:
            pass

    # --- system scheme ------------------------------------------------------

    def _system_is_dark(self) -> bool:
        hints = QGuiApplication.styleHints()
        if hints is None:
            return True
        try:
            return hints.colorScheme() != Qt.ColorScheme.Light
        except AttributeError:  # very old Qt without colorScheme()
            return True

    def _on_scheme_changed(self, _scheme) -> None:
        # Only the resolved (mode == "system") dark/light + defaulted accent
        # can change when the OS scheme flips; the raw selection doesn't.
        if self._mode == "system":
            self.resolvedChanged.emit()

    def _style_dict(self, style_id: str) -> dict:
        for entry in appearance_core.STYLES:
            if entry["id"] == style_id:
                return entry
        return appearance_core.STYLES[0]

    # --- raw selection -------------------------------------------------------

    @Property(str, notify=styleChanged)
    def style(self) -> str:
        return self._style

    @Property(str, notify=modeChanged)
    def mode(self) -> str:
        return self._mode

    @Property(str, notify=accentChanged)
    def accent(self) -> str:
        """The accent override, or "" when following the style's default."""
        return self._accent

    @Property(str, notify=accentChanged)
    def accentError(self) -> str:
        return self._accent_error

    # --- resolved (mode + system scheme applied) ----------------------------

    @Property(bool, notify=resolvedChanged)
    def resolvedDark(self) -> bool:
        if self._mode == "system":
            return self._system_is_dark()
        return self._mode == "dark"

    @Property(str, notify=resolvedChanged)
    def resolvedAccent(self) -> str:
        if self._accent:
            # A bright override is shown darker in light mode so text and
            # icons in it stay readable; the stored pick is left untouched.
            return self._accent if self.resolvedDark else appearance_core.readable_on_light(self._accent)
        entry = self._style_dict(self._style)
        return entry["default_accent_dark"] if self.resolvedDark else entry["default_accent_light"]

    @Property(bool, notify=resolvedChanged)
    def accentAdjusted(self) -> bool:
        """True when light mode is showing the override darker than picked."""
        return bool(self._accent) and self.resolvedAccent != self._accent

    @Property("QVariantList", notify=resolvedChanged)
    def styles(self) -> list:
        """The style registry, each with `defaultAccent` for the current mode."""
        dark = self.resolvedDark
        return [
            {
                "id": entry["id"],
                "label": entry["label"],
                "tagline": entry["tagline"],
                "defaultAccent": entry["default_accent_dark"] if dark else entry["default_accent_light"],
            }
            for entry in appearance_core.STYLES
        ]

    @Property("QVariantList", constant=True)
    def accentPresets(self) -> list:
        return appearance_core.ACCENT_PRESETS

    # --- actions --------------------------------------------------------------

    @Slot(str)
    def setStyle(self, style_id: str) -> None:
        if style_id == self._style:
            return
        if style_id not in {entry["id"] for entry in appearance_core.STYLES}:
            return
        self._style = style_id
        self._save()
        self.styleChanged.emit()
        self.resolvedChanged.emit()

    @Slot(str)
    def setMode(self, mode_id: str) -> None:
        if mode_id == self._mode or mode_id not in appearance_core.MODES:
            return
        self._mode = mode_id
        self._save()
        self.modeChanged.emit()
        self.resolvedChanged.emit()

    @Slot(str)
    def setAccent(self, hex_text: str) -> None:
        parsed = appearance_core.parse_accent(hex_text)
        if parsed is None:
            self._accent_error = "Enter a hex color like #22c3e6."
            self.accentChanged.emit()
            return
        self._accent_error = ""
        if parsed == self._accent:
            self.accentChanged.emit()  # clear a stale error even if unchanged
            return
        self._accent = parsed
        self._save()
        self.accentChanged.emit()
        self.resolvedChanged.emit()

    @Slot()
    def resetAccent(self) -> None:
        self._accent_error = ""
        if not self._accent:
            self.accentChanged.emit()  # clear a stale error
            return
        self._accent = ""
        self._save()
        self.accentChanged.emit()
        self.resolvedChanged.emit()
