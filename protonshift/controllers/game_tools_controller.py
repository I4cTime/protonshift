"""Per-game maintenance: prefix details, shader cache, and open/launch actions.

Driven by the selected game (``appId`` + ``prefixPath`` + ``installPath``, set
from the Library detail pane). Sizing a prefix or shader cache walks the tree,
so discovery runs on a worker thread. Destructive actions (delete prefix, clear
shader cache) re-read afterwards so the UI reflects reality.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.fsutil import human_size
from ..core.prefix import delete_prefix, get_prefix_info
from ..core.shader_cache import (
    clear_shader_cache,
    get_shader_cache_info,
    get_total_shader_cache_size,
)
from ..core.steam import get_steam_root
from ..core.system_open import open_path, open_uri
from ._worker import start_worker


class GameToolsController(QObject):
    appIdChanged = Signal()
    prefixPathChanged = Signal()
    installPathChanged = Signal()
    infoChanged = Signal()
    loadingChanged = Signal()
    busyChanged = Signal()
    statusChanged = Signal()

    _infoResult = Signal(str, "QVariantMap")  # app_id, info
    _actionResult = Signal(str, str, str)  # app_id, message, kind ("ok"/"err") — L1 gating
    _workError = Signal(str)  # unexpected worker exception -> clear flags + status

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._prefix_path = ""
        self._install_path = ""
        self._info: dict = {}
        self._loading = False
        self._busy = False
        self._status = ""
        self._infoResult.connect(self._on_info)
        self._actionResult.connect(self._on_action)
        self._workError.connect(self._on_work_error)

    # --- inputs ---------------------------------------------------------------

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self.appIdChanged.emit()

    @Property(str, notify=prefixPathChanged)
    def prefixPath(self) -> str:  # noqa: N802
        return self._prefix_path

    @prefixPath.setter
    def prefixPath(self, value: str) -> None:  # noqa: N802
        if value != self._prefix_path:
            self._prefix_path = value
            self.prefixPathChanged.emit()

    @Property(str, notify=installPathChanged)
    def installPath(self) -> str:  # noqa: N802
        return self._install_path

    @installPath.setter
    def installPath(self, value: str) -> None:  # noqa: N802
        if value != self._install_path:
            self._install_path = value
            self.installPathChanged.emit()

    # --- reactive -------------------------------------------------------------

    @Property("QVariantMap", notify=infoChanged)
    def info(self) -> dict:
        return self._info

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        if self._loading or not self._app_id:
            return
        self._loading = True
        self._status = ""
        self.loadingChanged.emit()
        self.statusChanged.emit()
        start_worker(
            self._info_work, self._app_id, self._prefix_path,
            on_error=self._workError.emit,
        )

    @Slot()
    def deletePrefix(self) -> None:  # noqa: N802
        if self._busy or not self._prefix_path:
            return
        self._begin()
        app_id = self._app_id
        start_worker(
            self._delete_work, app_id, self._prefix_path,
            on_error=lambda m: self._actionResult.emit(app_id, f"Delete failed: {m}", "err"),
        )

    @Slot()
    def clearShaderCache(self) -> None:  # noqa: N802
        if self._busy or not self._app_id:
            return
        self._begin()
        app_id = self._app_id
        start_worker(
            self._clear_work, app_id,
            on_error=lambda m: self._actionResult.emit(app_id, f"Clear failed: {m}", "err"),
        )

    @Slot(str)
    def openFolder(self, path: str) -> None:  # noqa: N802
        ok, msg = open_path(path)
        self._status = msg or ("Opened" if ok else "Couldn't open folder.")
        self.statusChanged.emit()

    @Slot()
    def openInSteam(self) -> None:  # noqa: N802
        if not self._app_id:
            return
        ok, msg = open_uri(f"steam://nav/games/details/{self._app_id}")
        self._status = msg or ("Opening in Steam…" if ok else "Couldn't open Steam.")
        self.statusChanged.emit()

    @Slot()
    def launchGame(self) -> None:  # noqa: N802
        if not self._app_id:
            return
        ok, msg = open_uri(f"steam://rungameid/{self._app_id}")
        self._status = msg or ("Launching…" if ok else "Couldn't launch.")
        self.statusChanged.emit()

    # --- workers --------------------------------------------------------------

    def _info_work(self, app_id: str, prefix_path: str) -> None:
        pinfo = get_prefix_info(prefix_path) if prefix_path else None
        steam_root = get_steam_root()
        sinfo = get_shader_cache_info(steam_root, app_id) if steam_root else None
        total = get_total_shader_cache_size(steam_root) if steam_root else 0
        info = {
            "prefixExists": bool(pinfo and pinfo.exists),
            "prefixSize": human_size(pinfo.size_bytes) if pinfo and pinfo.exists else "",
            "created": (pinfo.created[:10] if pinfo and pinfo.created else ""),
            "dxvk": pinfo.dxvk_version if pinfo else "",
            "vkd3d": pinfo.vkd3d_version if pinfo else "",
            "shaderExists": bool(sinfo and sinfo.exists),
            "shaderSize": human_size(sinfo.size_bytes) if sinfo and sinfo.exists else "",
            "shaderTotal": human_size(total) if total else "",
        }
        self._infoResult.emit(app_id, info)

    def _delete_work(self, app_id: str, prefix_path: str) -> None:
        ok = delete_prefix(prefix_path)
        self._actionResult.emit(
            app_id,
            "Prefix deleted — Steam will recreate it on next launch." if ok
            else "Couldn't delete the prefix.",
            "ok" if ok else "err",
        )

    def _clear_work(self, app_id: str) -> None:
        steam_root = get_steam_root()
        ok = clear_shader_cache(steam_root, app_id) if steam_root else False
        self._actionResult.emit(
            app_id,
            "Shader cache cleared." if ok else "Couldn't clear the shader cache.",
            "ok" if ok else "err",
        )

    def _begin(self) -> None:
        self._busy = True
        self._status = ""
        self.busyChanged.emit()
        self.statusChanged.emit()

    def _on_info(self, app_id: str, info: dict) -> None:
        if app_id != self._app_id:
            return
        self._info = info
        self._loading = False
        self.infoChanged.emit()
        self.loadingChanged.emit()

    def _on_action(self, app_id: str, message: str, kind: str) -> None:
        # Always clear busy, but only surface status / refresh for the game
        # the action belonged to (L1: no stale cross-game status).
        self._busy = False
        self.busyChanged.emit()
        if app_id != self._app_id:
            return
        self._status = message
        self.statusChanged.emit()
        # reflect the new on-disk state
        self.refresh()

    def _on_work_error(self, message: str) -> None:
        # Info-worker failure: clear loading, surface status, no auto-retry.
        self._loading = False
        self._status = f"Unexpected error: {message}"
        self.loadingChanged.emit()
        self.statusChanged.emit()
