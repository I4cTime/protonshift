"""QObject bridge for a per-game ScopeBuddy override (AppID/<id>.conf).

Driven by ``appId`` (set when the game-detail dialog opens); loads that game's
override, edits the SCB_* keys, saves (merge-preserving) or deletes the file.
Same safe contract as the global editor.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.env_vars import _valid_key
from ..core.scopebuddy import SCB_KNOWN_KEYS
from ._worker import start_worker
from .env_controller import EnvVarsModel


class PerAppScopeBuddyController(QObject):
    appIdChanged = Signal()
    loadingChanged = Signal()
    loadedChanged = Signal()
    dirtyChanged = Signal()
    existsChanged = Signal()
    statusChanged = Signal()

    _loadResult = Signal(str, bool, bool, list)  # app_id, ok, exists, rows
    _workError = Signal(str)  # unexpected worker exception -> clear flags + status

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._model = EnvVarsModel(self)
        self._model.modified.connect(self._mark_dirty)
        self._model.invalidKey.connect(self._on_invalid_key)
        self._loading = False
        self._loaded = False
        self._dirty = False
        self._exists = False
        self._status = ""
        self._known = list(SCB_KNOWN_KEYS)
        self._loadResult.connect(self._on_loaded)
        self._workError.connect(self._on_work_error)

    # --- static ---------------------------------------------------------------

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property("QStringList", constant=True)
    def knownKeys(self) -> list:  # noqa: N802
        return self._known

    # --- appId (drives load) --------------------------------------------------

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self._loaded = False
        self._dirty = False
        self._status = ""
        self.appIdChanged.emit()
        self.dirtyChanged.emit()
        self.statusChanged.emit()
        if value:
            self._reload()

    # --- reactive -------------------------------------------------------------

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=loadedChanged)
    def loaded(self) -> bool:
        return self._loaded

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

    @Slot(str)
    def addKey(self, key: str) -> None:  # noqa: N802
        key = key.strip()
        if not key:
            return
        if not _valid_key(key):
            self._status = f"Key “{key}” is invalid — letters, digits, underscore only."
            self.statusChanged.emit()
            return
        if key not in self._model.to_dict():
            self._model.merge({key: ""})

    @Slot()
    def save(self) -> None:
        if not self._loaded or not self._app_id:
            return
        cfg = self._model.to_dict()
        bad = next((k for k in cfg if not _valid_key(k)), None)
        if bad is not None:
            self._status = f"Not saved — key “{bad}” is invalid."
            self.statusChanged.emit()
            return
        from ..core.scopebuddy import write_per_app_config

        try:
            ok = write_per_app_config(self._app_id, cfg)
        except (ValueError, OSError) as exc:
            ok = False
            self._status = f"Save failed: {exc}"
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
        if not self._app_id:
            return
        from ..core.scopebuddy import delete_per_app_config

        if delete_per_app_config(self._app_id):
            self._model.reset_rows([])
            self._exists = False
            self._dirty = False
            self._status = "Override removed"
            self.existsChanged.emit()
            self.dirtyChanged.emit()
        else:
            self._status = "Couldn't remove override."
        self.statusChanged.emit()

    # --- internals ------------------------------------------------------------

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()
        if self._status:
            self._status = ""
            self.statusChanged.emit()

    def _on_invalid_key(self, key: str) -> None:
        self._status = f"Key “{key}” is invalid — letters, digits, underscore only."
        self.statusChanged.emit()

    def _on_work_error(self, message: str) -> None:
        self._loading = False
        self._status = f"Unexpected error: {message}"
        self.loadingChanged.emit()
        self.statusChanged.emit()

    def _reload(self) -> None:
        self._loading = True
        self.loadingChanged.emit()
        start_worker(self._load_work, self._app_id, on_error=self._workError.emit)

    def _load_work(self, app_id: str) -> None:
        from ..core.scopebuddy import read_per_app_config

        exists, cfg = read_per_app_config(app_id)
        scb = {k: v for k, v in cfg.items() if k.startswith("SCB_")}
        self._loadResult.emit(app_id, True, exists, sorted(scb.items()))

    def _on_loaded(self, app_id: str, ok: bool, exists: bool, rows: list) -> None:
        if app_id != self._app_id:
            return
        self._model.reset_rows(rows)
        self._exists = exists
        self._loaded = ok
        self._loading = False
        self._dirty = False
        self._status = ""
        self.loadingChanged.emit()
        self.loadedChanged.emit()
        self.existsChanged.emit()
        self.dirtyChanged.emit()
        self.statusChanged.emit()
