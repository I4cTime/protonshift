"""QObject bridge for the About card: version, platform, app folders, and a
manual update check.

Nothing here contacts the network unless ``checkForUpdates`` is called (the
"Check for updates" button). The check runs on a worker thread and reports
back through a queued signal, like every other controller.
"""

from __future__ import annotations

import platform
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from .. import __version__
from ..core.host import in_flatpak
from ..core.system_open import open_path
from ..core.updates import UpdateError, check_for_update
from ._worker import start_worker

# Where ProtonShift keeps its own files. (Steam/MangoHud/ScopeBuddy configs it
# edits belong to those tools and are named on their own pages.)
_FOLDERS: list[dict[str, str]] = [
    {
        "id": "settings",
        "label": "Settings folder",
        "hint": "App settings, profiles, save backups",
        "path": str(Path.home() / ".config" / "protonshift"),
    },
    {
        "id": "restores",
        "label": "Restores folder",
        "hint": "Where restored save backups are unpacked",
        "path": str(Path.home() / "ProtonShift Restores"),
    },
]


class AboutController(QObject):
    updateChanged = Signal()   # checking / checked / newer / latest / url / error
    foldersChanged = Signal()  # a folder appeared (they are created on first use)
    noticeChanged = Signal()   # copy / open feedback

    _checkResult = Signal(bool, str, bool, str)  # ok, latest-or-error, newer, url

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._checking = False
        self._checked = False
        self._newer = False
        self._latest = ""
        self._url = ""
        self._error = ""
        self._notice = ""
        self._notice_ok = True
        self._checkResult.connect(self._on_check_result)

    # --- static info ----------------------------------------------------------

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def platformLabel(self) -> str:
        """e.g. ``Linux · x86_64 · Flatpak`` - what a bug report needs."""
        parts = [platform.system() or "Linux", platform.machine() or "unknown"]
        parts.append("Flatpak" if in_flatpak() else "native install")
        return " · ".join(parts)

    @Property("QVariantList", notify=foldersChanged)
    def folders(self) -> list:
        return [{**folder, "exists": Path(folder["path"]).is_dir()} for folder in _FOLDERS]

    # --- update check ---------------------------------------------------------

    @Property(bool, notify=updateChanged)
    def checking(self) -> bool:
        return self._checking

    @Property(bool, notify=updateChanged)
    def checked(self) -> bool:
        """True once a check has completed successfully."""
        return self._checked

    @Property(bool, notify=updateChanged)
    def updateAvailable(self) -> bool:
        return self._newer

    @Property(str, notify=updateChanged)
    def latestVersion(self) -> str:
        return self._latest

    @Property(str, notify=updateChanged)
    def updateUrl(self) -> str:
        return self._url

    @Property(str, notify=updateChanged)
    def updateError(self) -> str:
        return self._error

    @Slot()
    def checkForUpdates(self) -> None:
        if self._checking:
            return
        self._checking = True
        self._error = ""
        self.updateChanged.emit()
        start_worker(
            self._check_work,
            on_error=lambda _m: self._checkResult.emit(False, "Could not check for updates.", False, ""),
        )

    def _check_work(self) -> None:
        try:
            result = check_for_update()
        except UpdateError as exc:
            self._checkResult.emit(False, str(exc), False, "")
            return
        self._checkResult.emit(True, result.latest, result.newer, result.url)

    def _on_check_result(self, ok: bool, text: str, newer: bool, url: str) -> None:
        self._checking = False
        self._checked = ok
        self._newer = ok and newer
        self._latest = text if ok else ""
        self._url = url if ok else ""
        self._error = "" if ok else text
        self.updateChanged.emit()

    # --- folders ----------------------------------------------------------------

    @Property(str, notify=noticeChanged)
    def notice(self) -> str:
        return self._notice

    @Property(bool, notify=noticeChanged)
    def noticeOk(self) -> bool:
        return self._notice_ok

    def _set_notice(self, text: str, ok: bool) -> None:
        self._notice = text
        self._notice_ok = ok
        self.noticeChanged.emit()

    def _folder_path(self, folder_id: str) -> str:
        for folder in _FOLDERS:
            if folder["id"] == folder_id:
                return folder["path"]
        return ""

    @Slot(str, result=bool)
    def copyPath(self, folder_id: str) -> bool:
        path = self._folder_path(folder_id)
        clipboard = QGuiApplication.clipboard()
        if not path or clipboard is None:
            self._set_notice("Could not copy the path.", False)
            return False
        clipboard.setText(path)
        self._set_notice("Path copied to the clipboard.", True)
        return True

    @Slot(str, result=bool)
    def openFolder(self, folder_id: str) -> bool:
        path = self._folder_path(folder_id)
        self.foldersChanged.emit()  # re-check existence: folders are created on first use
        if not path or not Path(path).is_dir():
            self._set_notice("That folder doesn't exist yet. ProtonShift creates it the first time it is needed.", False)
            return False
        ok, message = open_path(path)
        self._set_notice("" if ok else (message or "Could not open the folder."), ok)
        return ok
