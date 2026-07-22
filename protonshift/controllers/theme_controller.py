"""QObject bridge for theme selection.

Persists the user's choice (one of the concrete palettes, or "system") to
``~/.config/protonshift/settings.json`` and resolves "system" to a concrete
palette from the OS color scheme, updating live when the desktop flips between
light and dark.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ..core.fsutil import atomic_write_text

_SETTINGS = Path.home() / ".config" / "protonshift" / "settings.json"

# id -> (label, is_dark). "system" is handled separately in the picker.
_THEMES: list[dict] = [
    {"id": "proton-neon", "label": "Proton Neon", "dark": True},
    {"id": "violet-night", "label": "Violet Night", "dark": True},
    {"id": "deep-sea", "label": "Deep Sea", "dark": True},
    {"id": "proton-day", "label": "Proton Day", "dark": False},
    {"id": "violet-day", "label": "Violet Day", "dark": False},
    {"id": "sandstone", "label": "Sandstone", "dark": False},
]
_VALID = {t["id"] for t in _THEMES} | {"system"}
_DEFAULT_DARK = "proton-neon"
_DEFAULT_LIGHT = "proton-day"


class ThemeController(QObject):
    themeChanged = Signal()      # the raw choice changed
    resolvedChanged = Signal()   # the concrete palette changed (choice or OS)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._choice = self._load_choice()
        hints = QGuiApplication.styleHints()
        if hints is not None:
            hints.colorSchemeChanged.connect(self._on_scheme_changed)

    # --- persistence ----------------------------------------------------------

    def _load_choice(self) -> str:
        try:
            data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
            choice = data.get("theme", "system")
            return choice if choice in _VALID else "system"
        except (OSError, ValueError, TypeError):
            return "system"

    def _save_choice(self) -> None:
        try:
            existing = {}
            if _SETTINGS.exists():
                try:
                    existing = json.loads(_SETTINGS.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    existing = {}
            if not isinstance(existing, dict):
                existing = {}
            existing["theme"] = self._choice
            # L8: atomic replace (same contract as every other config write) —
            # a crash mid-write can't corrupt settings.json.
            atomic_write_text(_SETTINGS, json.dumps(existing, indent=2))
        except OSError:
            pass

    # --- system scheme --------------------------------------------------------

    def _system_is_dark(self) -> bool:
        hints = QGuiApplication.styleHints()
        if hints is None:
            return True
        try:
            return hints.colorScheme() != Qt.ColorScheme.Light
        except AttributeError:  # very old Qt without colorScheme()
            return True

    def _on_scheme_changed(self, _scheme) -> None:
        # Only the resolved palette changes when following the system.
        if self._choice == "system":
            self.resolvedChanged.emit()

    # --- properties -----------------------------------------------------------

    @Property("QVariantList", constant=True)
    def themes(self) -> list:
        return _THEMES

    @Property(str, notify=themeChanged)
    def choice(self) -> str:
        """The raw selection: a palette id or "system"."""
        return self._choice

    @Property(bool, notify=resolvedChanged)
    def systemIsDark(self) -> bool:  # noqa: N802
        return self._system_is_dark()

    @Property(str, notify=resolvedChanged)
    def resolvedTheme(self) -> str:  # noqa: N802
        """The concrete palette id Theme.qml should use."""
        if self._choice != "system":
            return self._choice
        return _DEFAULT_DARK if self._system_is_dark() else _DEFAULT_LIGHT

    # --- actions --------------------------------------------------------------

    @Slot(str)
    def setTheme(self, choice: str) -> None:  # noqa: N802
        if choice not in _VALID or choice == self._choice:
            return
        self._choice = choice
        self._save_choice()
        self.themeChanged.emit()
        self.resolvedChanged.emit()
