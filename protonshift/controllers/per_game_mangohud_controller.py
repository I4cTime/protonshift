"""QObject bridge for a per-game MangoHud override (wine-<game>.conf).

Driven by ``gameName`` (set when the game-detail dialog opens). Mirrors the
global MangoHud editor's reactive config-map, plus a delete. Same safe RMW.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.mangohud import MANGOHUD_PARAMS, MANGOHUD_PRESETS
from ._worker import start_worker


class PerGameMangoHudController(QObject):
    gameNameChanged = Signal()
    configChanged = Signal()
    loadingChanged = Signal()
    loadedChanged = Signal()
    dirtyChanged = Signal()
    existsChanged = Signal()
    statusChanged = Signal()

    _loadResult = Signal(str, bool, str, bool, dict)  # name, ok, error, exists, config

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._name = ""
        self._config: dict[str, str] = {}
        self._loading = False
        self._loaded = False
        self._dirty = False
        self._exists = False
        self._error = ""
        self._status = ""
        self._toggle_params = [p for p in MANGOHUD_PARAMS if p["type"] == "toggle"]
        self._value_params = [p for p in MANGOHUD_PARAMS if p["type"] == "value"]
        self._presets = list(MANGOHUD_PRESETS.keys())
        self._loadResult.connect(self._on_loaded)

    # --- static ---------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def toggleParams(self) -> list:  # noqa: N802
        return self._toggle_params

    @Property("QVariantList", constant=True)
    def valueParams(self) -> list:  # noqa: N802
        return self._value_params

    @Property("QStringList", constant=True)
    def presetNames(self) -> list:  # noqa: N802
        return self._presets

    # --- gameName (drives load) ----------------------------------------------

    @Property(str, notify=gameNameChanged)
    def gameName(self) -> str:  # noqa: N802
        return self._name

    @gameName.setter
    def gameName(self, value: str) -> None:  # noqa: N802
        if value == self._name:
            return
        self._name = value
        self._loaded = False
        self._dirty = False
        self._status = ""
        self.gameNameChanged.emit()
        self.dirtyChanged.emit()
        self.statusChanged.emit()
        if value:
            self._reload()

    # --- reactive -------------------------------------------------------------

    @Property("QVariantMap", notify=configChanged)
    def config(self) -> dict:
        return dict(self._config)

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=loadedChanged)
    def loaded(self) -> bool:
        return self._loaded

    @Property(str, notify=loadedChanged)
    def loadError(self) -> str:  # noqa: N802
        return self._error

    @Property(bool, notify=existsChanged)
    def exists(self) -> bool:
        return self._exists

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot(str, bool)
    def setToggle(self, key: str, on: bool) -> None:  # noqa: N802
        present = key in self._config
        if on and not present:
            self._config[key] = ""
        elif not on and present:
            del self._config[key]
        else:
            return
        self._touch()

    @Slot(str, str)
    def setValue(self, key: str, value: str) -> None:  # noqa: N802
        value = value.strip()
        if value:
            if self._config.get(key) == value:
                return
            self._config[key] = value
        elif key in self._config:
            del self._config[key]
        else:
            return
        self._touch()

    @Slot(str)
    def applyPreset(self, name: str) -> None:  # noqa: N802
        preset = MANGOHUD_PRESETS.get(name)
        if preset:
            self._config = dict(preset)
            self._touch()

    @Slot()
    def save(self) -> None:
        if not self._loaded or not self._name:
            return
        from ..core.mangohud import write_per_game_config

        try:
            ok = write_per_game_config(self._name, dict(self._config))
        except Exception as exc:  # noqa: BLE001 — a raising core writer must not kill the slot
            ok = False
            self._status = f"Save failed: {type(exc).__name__}: {exc}"
        else:
            if ok:
                self._dirty = False
                self._exists = True
                self._status = "Saved override"
                self.dirtyChanged.emit()
                self.existsChanged.emit()
            else:
                self._status = "Save failed — check permissions."
        self.statusChanged.emit()

    @Slot()
    def deleteOverride(self) -> None:  # noqa: N802
        if not self._name:
            return
        from ..core.mangohud import delete_per_game_config

        if delete_per_game_config(self._name):
            self._config = {}
            self._exists = False
            self._dirty = False
            self._status = "Override removed"
            self.configChanged.emit()
            self.existsChanged.emit()
            self.dirtyChanged.emit()
        else:
            self._status = "Couldn't remove override."
        self.statusChanged.emit()

    # --- internals ------------------------------------------------------------

    def _touch(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()
        if self._status:
            self._status = ""
            self.statusChanged.emit()
        self.configChanged.emit()

    def _reload(self) -> None:
        self._loading = True
        self.loadingChanged.emit()
        name = self._name
        start_worker(
            self._load_work, name,
            on_error=lambda m: self._loadResult.emit(name, False, m, True, {}),
        )

    def _load_work(self, name: str) -> None:
        from ..core.mangohud import read_per_game_config

        try:
            exists, cfg = read_per_game_config(name)
            self._loadResult.emit(name, True, "", exists, cfg)
        except (OSError, UnicodeDecodeError) as exc:
            self._loadResult.emit(name, False, str(exc), True, {})

    def _on_loaded(self, name: str, ok: bool, error: str, exists: bool, config: dict) -> None:
        if name != self._name:
            return
        if ok:
            self._config = dict(config)
            self._loaded = True
            self._error = ""
        else:
            self._loaded = False
            self._error = error
        self._exists = exists
        self._loading = False
        self._dirty = False
        self._status = ""
        self.loadingChanged.emit()
        self.loadedChanged.emit()
        self.existsChanged.emit()
        self.dirtyChanged.emit()
        self.configChanged.emit()
        self.statusChanged.emit()
