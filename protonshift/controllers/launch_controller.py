"""QObject bridge for per-game Steam launch options.

Bind ``appId`` to the selected game; the controller loads that game's
LaunchOptions from ``localconfig.vdf`` on a worker thread and saves them back
fail-closed (the underlying core refuses to overwrite an unparseable file —
review #20). A late load result for a game the user already navigated away from
is discarded, so switching games can't strand the editor on stale text
(review #8, the old app's cross-game bleed).
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Signal, Slot


class LaunchOptionsController(QObject):
    appIdChanged = Signal()
    stateChanged = Signal()  # loaded / loading / text / error
    dirtyChanged = Signal()
    statusChanged = Signal()

    _loadResult = Signal(str, bool, str)  # app_id, ok, value
    _saveResult = Signal(str, bool)  # app_id, ok

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._text = ""
        self._loaded = False
        self._loading = False
        self._dirty = False
        self._status = ""
        self._error = ""
        self._loadResult.connect(self._on_loaded)
        self._saveResult.connect(self._on_saved)

    # --- selection ------------------------------------------------------------

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self._dirty = False
        self._status = ""
        self.appIdChanged.emit()
        self.dirtyChanged.emit()
        self.statusChanged.emit()
        self._reload()

    # --- editable / state -----------------------------------------------------

    @Property(str, notify=stateChanged)
    def text(self) -> str:
        return self._text

    @Slot(str)
    def setText(self, value: str) -> None:  # noqa: N802
        if value != self._text:
            self._text = value
            if not self._dirty:
                self._dirty = True
                self.dirtyChanged.emit()
            if self._status:
                self._status = ""
                self.statusChanged.emit()

    @Property(bool, notify=stateChanged)
    def loaded(self) -> bool:
        return self._loaded

    @Property(bool, notify=stateChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(str, notify=stateChanged)
    def loadError(self) -> str:  # noqa: N802
        return self._error

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot()
    def save(self) -> None:
        if not self._loaded or not self._app_id:
            self._status = "Not saved — launch options weren't loaded."
            self.statusChanged.emit()
            return
        threading.Thread(
            target=self._save_work, args=(self._app_id, self._text), daemon=True
        ).start()

    # --- internals ------------------------------------------------------------

    def _reload(self) -> None:
        if not self._app_id:
            self._text = ""
            self._loaded = False
            self._loading = False
            self._error = ""
            self.stateChanged.emit()
            return
        self._loading = True
        self._loaded = False
        self._error = ""
        self.stateChanged.emit()
        threading.Thread(target=self._load_work, args=(self._app_id,), daemon=True).start()

    @staticmethod
    def _config_path():
        from ..core.steam import discover_games, get_localconfig_path

        root, _ = discover_games()
        return get_localconfig_path(root) if root else None

    def _load_work(self, app_id: str) -> None:
        from ..core.vdf_config import read_launch_options

        path = self._config_path()
        if not path:
            self._loadResult.emit(app_id, False, "")
            return
        ok, val = read_launch_options(path, app_id)
        self._loadResult.emit(app_id, ok, val)

    def _save_work(self, app_id: str, text: str) -> None:
        from ..core.vdf_config import set_launch_options

        path = self._config_path()
        ok = bool(path) and set_launch_options(path, app_id, text)
        self._saveResult.emit(app_id, ok)

    def _on_loaded(self, app_id: str, ok: bool, value: str) -> None:
        if app_id != self._app_id:
            return  # user switched games mid-load — discard the stale result
        self._loading = False
        if ok:
            self._loaded = True
            self._text = value
            self._error = ""
        else:
            self._loaded = False
            self._error = "Couldn't read localconfig.vdf — editing is disabled so nothing gets overwritten."
        self._dirty = False
        self.stateChanged.emit()
        self.dirtyChanged.emit()

    def _on_saved(self, app_id: str, ok: bool) -> None:
        if app_id != self._app_id:
            return
        if ok:
            self._dirty = False
            self._status = "Saved. Quit Steam first — it rewrites this file on exit."
            self.dirtyChanged.emit()
        else:
            self._status = "Save failed — localconfig.vdf unreadable or unwritable."
        self.statusChanged.emit()
