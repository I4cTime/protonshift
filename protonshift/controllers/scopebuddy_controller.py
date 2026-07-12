"""QObject bridge for the global ScopeBuddy scb.conf editor.

Manages the SCB_* keys; anything else in the file (comments, bash logic,
unrelated vars) is preserved by the core's line-merge write. Same safe RMW
contract as the other editors: read error distinguished from empty, save
refuses unless a load succeeded.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.scopebuddy import (
    SCB_KNOWN_KEYS,
    SCOPEBUDDY_PRESETS,
    scopebuddy_available_info,
)
from .env_controller import EnvVarsModel  # generic key/value list model


class ScopeBuddyController(QObject):
    loadingChanged = Signal()
    loadedChanged = Signal()
    dirtyChanged = Signal()
    statusChanged = Signal()

    _loadResult = Signal(bool, str, list)  # ok, error, rows

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        info = scopebuddy_available_info()
        self._available = bool(info["available"])
        self._binary = str(info["binary"])
        self._version = str(info["version"])
        self._model = EnvVarsModel(self)
        self._model.modified.connect(self._mark_dirty)
        self._loading = False
        self._loaded = False
        self._dirty = False
        self._error = ""
        self._status = ""
        self._known = list(SCB_KNOWN_KEYS)
        self._presets = list(SCOPEBUDDY_PRESETS.keys())
        self._loadResult.connect(self._on_loaded)
        self.reload()

    # --- static ---------------------------------------------------------------

    @Property(bool, constant=True)
    def available(self) -> bool:
        return self._available

    @Property(str, constant=True)
    def binaryName(self) -> str:  # noqa: N802
        return self._binary

    @Property(str, constant=True)
    def version(self) -> str:
        return self._version

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property("QStringList", constant=True)
    def knownKeys(self) -> list:  # noqa: N802
        return self._known

    @Property("QStringList", constant=True)
    def presetNames(self) -> list:  # noqa: N802
        return self._presets

    # --- reactive -------------------------------------------------------------

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=loadedChanged)
    def loaded(self) -> bool:
        return self._loaded

    @Property(str, notify=loadedChanged)
    def loadError(self) -> str:  # noqa: N802
        return self._error

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot(str)
    def addKey(self, key: str) -> None:  # noqa: N802
        key = key.strip()
        if key and key not in self._model.to_dict():
            self._model.merge({key: ""})

    @Slot(str)
    def applyPreset(self, name: str) -> None:  # noqa: N802
        preset = SCOPEBUDDY_PRESETS.get(name)
        if preset:
            self._model.merge(dict(preset))

    @Slot()
    def reload(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()
        threading.Thread(target=self._load_work, daemon=True).start()

    @Slot()
    def save(self) -> None:
        if not self._loaded:
            self._status = "Not saved — config was never loaded."
            self.statusChanged.emit()
            return
        from ..core.scopebuddy import write_global_config

        if write_global_config(self._model.to_dict()):
            self._dirty = False
            self._status = "Saved to scb.conf"
            self.dirtyChanged.emit()
        else:
            self._status = "Save failed — check permissions."
        self.statusChanged.emit()

    # --- internals ------------------------------------------------------------

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()
        if self._status:
            self._status = ""
            self.statusChanged.emit()

    def _load_work(self) -> None:
        from ..core.scopebuddy import SCOPEBUDDY_GLOBAL_CONF, parse_scb_conf

        path = SCOPEBUDDY_GLOBAL_CONF
        if path.exists():
            try:
                path.read_text(encoding="utf-8")  # probe readability
            except OSError as exc:
                self._loadResult.emit(False, str(exc), [])
                return
        cfg = {k: v for k, v in parse_scb_conf(path).items() if k.startswith("SCB_")}
        self._loadResult.emit(True, "", sorted(cfg.items()))

    def _on_loaded(self, ok: bool, error: str, rows: list) -> None:
        if ok:
            self._model.reset_rows(rows)
            self._loaded = True
            self._error = ""
            self._dirty = False
            self.dirtyChanged.emit()
        else:
            self._loaded = False
            self._error = error
        self._loading = False
        self._status = ""
        self.loadingChanged.emit()
        self.loadedChanged.emit()
        self.statusChanged.emit()
