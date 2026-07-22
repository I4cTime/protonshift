"""QObject bridge for the global MangoHud.conf editor.

Same safe read-modify-write contract as the env editor: read errors are
distinguished from empty (loadError), and save() refuses unless a load
succeeded, so a failed read can't be followed by an empty overwrite.

State is a single ``config`` map (QVariantMap) exposed reactively; toggles read
membership, value fields read the mapped value. A toggle present with an empty
value is "on" — MangoHud's own convention.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.mangohud import MANGOHUD_PARAMS, MANGOHUD_PRESETS
from ._worker import start_worker


class MangoHudController(QObject):
    availableChanged = Signal()
    configChanged = Signal()
    loadingChanged = Signal()
    loadedChanged = Signal()
    dirtyChanged = Signal()
    statusChanged = Signal()

    _loadResult = Signal(bool, str, dict)  # ok, error, config
    _availResult = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config: dict[str, str] = {}
        self._loading = False
        self._loaded = False
        self._dirty = False
        self._error = ""
        self._status = ""
        # M4: availability lookup can shell out inside a Flatpak — probed on
        # the load worker, delivered via _availResult.
        self._available = False
        self._toggle_params = [p for p in MANGOHUD_PARAMS if p["type"] == "toggle"]
        self._value_params = [p for p in MANGOHUD_PARAMS if p["type"] == "value"]
        self._presets = list(MANGOHUD_PRESETS.keys())
        self._loadResult.connect(self._on_loaded)
        self._availResult.connect(self._on_avail)
        self.reload()

    # --- static metadata ------------------------------------------------------

    @Property(bool, notify=availableChanged)
    def available(self) -> bool:
        return self._available

    @Property("QVariantList", constant=True)
    def toggleParams(self) -> list:  # noqa: N802
        return self._toggle_params

    @Property("QVariantList", constant=True)
    def valueParams(self) -> list:  # noqa: N802
        return self._value_params

    @Property("QStringList", constant=True)
    def presetNames(self) -> list:  # noqa: N802
        return self._presets

    # --- reactive state -------------------------------------------------------

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
        if not preset:
            return
        self._config = dict(preset)
        self._touch()

    @Slot()
    def reload(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()
        start_worker(
            self._load_work,
            on_error=lambda m: self._loadResult.emit(False, m, {}),
        )

    @Slot()
    def save(self) -> None:
        if not self._loaded:
            self._status = "Not saved — config was never loaded."
            self.statusChanged.emit()
            return
        from ..core.mangohud import write_mangohud_config

        try:
            ok = write_mangohud_config(dict(self._config))
        except Exception as exc:  # noqa: BLE001 — a raising core writer must not kill the slot
            ok = False
            self._status = f"Save failed: {type(exc).__name__}: {exc}"
        else:
            if ok:
                self._dirty = False
                self._status = "Saved to MangoHud.conf"
                self.dirtyChanged.emit()
            else:
                self._status = "Save failed — check permissions."
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

    def _load_work(self) -> None:
        from ..core.mangohud import is_mangohud_available, read_mangohud_config

        self._availResult.emit(is_mangohud_available())
        try:
            self._loadResult.emit(True, "", read_mangohud_config())
        except (OSError, UnicodeDecodeError) as exc:
            self._loadResult.emit(False, str(exc), {})

    def _on_avail(self, available: bool) -> None:
        self._available = available
        self.availableChanged.emit()

    def _on_loaded(self, ok: bool, error: str, config: dict) -> None:
        if ok:
            self._config = dict(config)
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
        self.configChanged.emit()
        self.statusChanged.emit()
