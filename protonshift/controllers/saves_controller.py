"""QObject bridge for game save backup & restore.

Discovers likely save locations (Proton prefix + native userdata), zips them to
a timestamped backup, and restores a backup into a safe folder the user can then
inspect (we never overwrite live saves in place). All disk work is threaded.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.fsutil import human_size
from ._worker import start_worker


class SavesController(QObject):
    appIdChanged = Signal()
    prefixPathChanged = Signal()
    dataChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()

    _listResult = Signal(str, list, list)  # app_id, saves, backups
    _actionResult = Signal(str, str)  # app_id, message (L1: gate stale results)
    _workError = Signal(str)  # unexpected worker exception -> clear busy + status

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._prefix_path = ""
        self._saves: list[dict] = []
        self._backups: list[dict] = []
        self._status = ""
        self._busy = False
        self._listResult.connect(self._on_list)
        self._actionResult.connect(self._on_action)
        self._workError.connect(self._on_work_error)

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self._saves = []
        self._backups = []
        self._status = ""
        self.appIdChanged.emit()
        self.dataChanged.emit()
        self.statusChanged.emit()

    @Property(str, notify=prefixPathChanged)
    def prefixPath(self) -> str:  # noqa: N802
        return self._prefix_path

    @prefixPath.setter
    def prefixPath(self, value: str) -> None:  # noqa: N802
        if value != self._prefix_path:
            self._prefix_path = value
            self.prefixPathChanged.emit()

    @Property("QVariantList", notify=dataChanged)
    def saves(self) -> list:
        return self._saves

    @Property("QVariantList", notify=dataChanged)
    def backups(self) -> list:
        return self._backups

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    # --- actions --------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        if self._busy or not self._app_id:
            return
        self._busy = True
        self.busyChanged.emit()
        start_worker(
            self._list_work, self._app_id, self._prefix_path,
            on_error=self._workError.emit,
        )

    @Slot()
    def backup(self) -> None:
        if self._busy or not self._app_id or not self._saves:
            return
        paths = [s["path"] for s in self._saves]
        self._begin("Backing up…")
        app_id = self._app_id
        start_worker(
            self._backup_work, app_id, paths,
            on_error=lambda m: self._actionResult.emit(app_id, f"Backup failed: {m}"),
        )

    @Slot(str)
    def restore(self, backup_path: str) -> None:
        if self._busy or not backup_path:
            return
        self._begin("Restoring…")
        app_id = self._app_id
        start_worker(
            self._restore_work, app_id, backup_path,
            on_error=lambda m: self._actionResult.emit(app_id, f"Restore failed: {m}"),
        )

    # --- workers --------------------------------------------------------------

    def _list_work(self, app_id: str, prefix_path: str) -> None:
        from ..core.saves import find_save_paths, list_backups

        locs = find_save_paths(app_id, prefix_path or None)
        saves = [
            {"path": s.path, "label": s.label, "size": human_size(s.size_bytes)}
            for s in locs
        ]
        backups = [
            {"path": b.path, "filename": b.filename, "size": human_size(b.size_bytes),
             "created": b.created[:16].replace("T", " ")}
            for b in list_backups(app_id)
        ]
        self._listResult.emit(app_id, saves, backups)

    def _backup_work(self, app_id: str, paths: list) -> None:
        from ..core.saves import backup_saves

        result = backup_saves(app_id, paths)
        self._actionResult.emit(app_id, "Backup created." if result else "Backup failed.")

    def _restore_work(self, app_id: str, backup_path: str) -> None:
        from ..core.saves import restore_backup
        from ..core.system_open import open_path

        stem = Path(backup_path).stem
        target = Path.home() / "ProtonShift Restores" / (app_id or "unknown") / stem
        ok = restore_backup(backup_path, str(target))
        if ok:
            open_path(str(target))
            self._actionResult.emit(app_id, f"Restored to {target} (opened).")
        else:
            self._actionResult.emit(app_id, "Restore failed.")

    def _begin(self, msg: str) -> None:
        self._busy = True
        self._status = msg
        self.busyChanged.emit()
        self.statusChanged.emit()

    def _on_list(self, app_id: str, saves: list, backups: list) -> None:
        if app_id != self._app_id:
            return
        self._saves = saves
        self._backups = backups
        self._busy = False
        self.dataChanged.emit()
        self.busyChanged.emit()

    def _on_action(self, app_id: str, msg: str) -> None:
        # Always clear busy (a wedged flag blocks all future actions), but
        # only surface status / refresh when the result matches the current
        # game (L1: no stale cross-game status).
        self._busy = False
        self.busyChanged.emit()
        if app_id != self._app_id:
            return
        self._status = msg
        self.statusChanged.emit()
        self.refresh()

    def _on_work_error(self, message: str) -> None:
        # List-worker failure: clear busy, surface status, do NOT refresh
        # (refreshing would retry the failing worker in a loop).
        self._busy = False
        self._status = f"Unexpected error: {message}"
        self.busyChanged.emit()
        self.statusChanged.emit()
