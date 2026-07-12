"""QObject bridge between the gamescope core and QML.

This is the entire IPC story in the new architecture: a QObject with
``Property``/``Signal``/``Slot`` members. QML binds directly to these; there is
no HTTP server, no bearer token, no serialization boundary, no localhost port —
so the whole class of transport bugs from the old FastAPI layer cannot exist.

The pattern here (a single shared ``changed`` signal driving every option
property plus the computed ``command``) is deliberately compact so that adding
an option is one line, not a getter/setter/signal triple.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ..core.gamescope import (
    GamescopeOptions,
    build_gamescope_cmd,
    is_gamescope_available,
)


def _opt_property(name: str, type_: type, notify: Signal) -> Property:
    """Build a QML-facing property backed by a field on ``self._opts``.

    All option properties share one ``changed`` notify signal, so any edit
    re-evaluates the ``command`` binding in QML. Writes are guarded so setting a
    property to its current value does not churn the preview.
    """

    def getter(self):  # noqa: ANN001
        return getattr(self._opts, name)

    def setter(self, value):  # noqa: ANN001
        if getattr(self._opts, name) != value:
            setattr(self._opts, name, value)
            self.changed.emit()

    return Property(type_, getter, setter, notify=notify)


class GamescopeController(QObject):
    """Reactive wrapper around :class:`GamescopeOptions`."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._opts = GamescopeOptions()
        self._available = is_gamescope_available()

    # --- computed / read-only -------------------------------------------------

    @Property(str, notify=changed)
    def command(self) -> str:
        """The shell-safe launch prefix, rebuilt on every edit."""
        return build_gamescope_cmd(self._opts) or "gamescope --"

    @Property(bool, constant=True)
    def gamescopeAvailable(self) -> bool:  # noqa: N802 (QML camelCase)
        return self._available

    # --- editable options (bound two-way from QML) ---------------------------

    outputWidth = _opt_property("output_width", int, changed)
    outputHeight = _opt_property("output_height", int, changed)
    gameWidth = _opt_property("game_width", int, changed)
    gameHeight = _opt_property("game_height", int, changed)
    fpsLimit = _opt_property("fps_limit", int, changed)

    fsr = _opt_property("fsr", bool, changed)
    fsrSharpness = _opt_property("fsr_sharpness", int, changed)
    integerScale = _opt_property("integer_scale", bool, changed)
    hdr = _opt_property("hdr", bool, changed)
    fullscreen = _opt_property("fullscreen", bool, changed)
    borderless = _opt_property("borderless", bool, changed)
    extraArgs = _opt_property("extra_args", str, changed)

    wrapWithScopebuddy = _opt_property("wrap_with_scopebuddy", bool, changed)
    scbAutoRes = _opt_property("scb_auto_res", bool, changed)
    scbAutoHdr = _opt_property("scb_auto_hdr", bool, changed)
    scbAutoVrr = _opt_property("scb_auto_vrr", bool, changed)
    scbAutoRefresh = _opt_property("scb_auto_refresh", bool, changed)
    scbAutoFrameLimit = _opt_property("scb_auto_frame_limit", bool, changed)
    scbNoscope = _opt_property("scb_noscope", bool, changed)

    # --- actions -------------------------------------------------------------

    @Slot()
    def copyCommand(self) -> None:
        """Copy the current command to the system clipboard."""
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.command)
