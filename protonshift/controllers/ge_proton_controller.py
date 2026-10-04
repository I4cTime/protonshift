"""QObject bridge for the GE-Proton manager page.

Everything that touches the network or disk (release listing, download,
extraction, removal) runs on a ``start_worker`` thread; results, progress and
errors come back through queued signals so the page never blocks. The
download's progress callback fires on the worker thread and only *emits*
``_installProgress`` - the connected handler mutates state on the GUI thread.

``toolsChanged`` fires after a successful install or remove so other
controllers (the per-game Proton picker in ``LaunchOptionsController``) can
re-read ``compatibilitytools.d``.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from ..core.fsutil import human_size
from ..core.ge_proton import (
    GeProtonCancelled,
    GeProtonError,
    GeRelease,
    download_and_install,
    fetch_releases,
    install_dir,
    list_installed,
    parse_installed_version,
    remove_tool,
    tool_usage,
)
from ._worker import start_worker


def _version_label(name: str) -> str:
    parts = parse_installed_version(name)
    return "-".join(str(p) for p in parts) if parts else ""


class GeProtonController(QObject):
    installedChanged = Signal()
    releasesChanged = Signal()
    busyChanged = Signal()
    progressChanged = Signal()
    statusChanged = Signal()
    errorChanged = Signal()
    toolsChanged = Signal()  # a build was installed or removed

    # worker -> GUI thread
    _refreshResult = Signal(list, list, str)  # installed dicts, release dicts, releases error
    _installProgress = Signal(int, int)  # downloaded, total (-1 unknown)
    _installDone = Signal(str)  # installed dir name
    _installFailed = Signal(str, bool)  # message, cancelled
    _removeDone = Signal(str, str)  # name, error ("" on success)
    _workError = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._installed: list[dict] = []
        self._releases: list[dict] = []
        self._release_objs: dict[str, GeRelease] = {}
        self._pending_release_objs: dict[str, GeRelease] = {}
        self._folder = ""
        self._busy = False
        self._installing_tag = ""
        self._progress = 0.0
        self._progress_label = ""
        self._status = ""
        self._error = ""
        self._cancel = threading.Event()
        self._refreshResult.connect(self._on_refreshed)
        self._installProgress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self._installDone.connect(self._on_installed)
        self._installFailed.connect(self._on_install_failed)
        self._removeDone.connect(self._on_removed)
        self._workError.connect(self._on_work_error)
        self.refresh()

    # --- read-only state ------------------------------------------------------

    @Property("QVariantList", notify=installedChanged)
    def installed(self) -> list:
        return self._installed

    @Property("QVariantList", notify=releasesChanged)
    def releases(self) -> list:
        return self._releases

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=busyChanged)
    def installing(self) -> bool:
        return bool(self._installing_tag)

    @Property(str, notify=busyChanged)
    def installingTag(self) -> str:
        return self._installing_tag

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    @Property(str, notify=progressChanged)
    def progressLabel(self) -> str:
        return self._progress_label

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=errorChanged)
    def error(self) -> str:
        return self._error

    @Property(str, notify=installedChanged)
    def folder(self) -> str:
        return self._folder

    # --- actions --------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        start_worker(self._refresh_work, on_error=self._workError.emit)

    @Slot(str)
    def install(self, tag: str) -> None:
        release = self._release_objs.get(tag)
        if self._busy or release is None:
            return
        self._cancel.clear()
        self._installing_tag = tag
        self._progress = 0.0
        self._progress_label = "Starting download…"
        self._error = ""
        self._status = ""
        self.progressChanged.emit()
        self.errorChanged.emit()
        self.statusChanged.emit()
        self._set_busy(True)
        start_worker(
            self._install_work, release,
            on_error=lambda m: self._installFailed.emit(m, False),
        )

    @Slot()
    def cancel(self) -> None:
        if self._installing_tag:
            self._cancel.set()

    @Slot(str)
    def remove(self, name: str) -> None:
        if self._busy:
            return
        self._error = ""
        self.errorChanged.emit()
        self._set_busy(True)
        start_worker(
            self._remove_work, name,
            on_error=lambda m: self._removeDone.emit(name, m),
        )

    @Slot()
    def openFolder(self) -> None:
        start_worker(self._open_folder_work, on_error=lambda _m: None)

    # --- worker ---------------------------------------------------------------

    def _refresh_work(self) -> None:
        from ..core.steam import discover_games

        tools = list_installed()
        usage: dict[str, list[str]] = {}
        try:
            root, games = discover_games()
            usage = tool_usage(games, root)
        except Exception:  # noqa: BLE001 - usage is a nicety; never block the list
            usage = {}
        installed = [
            {
                "name": t.name,
                "displayName": t.display_name or t.name,
                "path": str(t.path),
                "sizeLabel": human_size(t.size_bytes),
                "isGe": t.is_ge,
                "location": t.location,
                "removable": t.removable,
                "version": _version_label(t.version or t.name),
                "inUse": usage.get(t.name, []),
                "inUseCount": len(usage.get(t.name, [])),
            }
            for t in tools
        ]
        # a release counts as installed by internal name OR version tag, so a
        # distro package registered as 'Proton-GE' still marks GE-Proton11-7
        names = {t.name for t in tools} | {t.version for t in tools if t.version}
        error = ""
        releases: list[dict] = []
        objs: dict[str, GeRelease] = {}
        try:
            for r in fetch_releases():
                objs[r.tag] = r
                releases.append(
                    {
                        "tag": r.tag,
                        "name": r.name,
                        "published": r.published[:10],
                        "sizeLabel": human_size(r.size) if r.size else "",
                        "installed": r.tag in names,
                    }
                )
        except GeProtonError as exc:
            error = str(exc)
        # plain attribute swap: read on the GUI thread only after the queued
        # result signal below is delivered
        self._pending_release_objs = objs
        self._folder = str(install_dir())
        self._refreshResult.emit(installed, releases, error)

    def _install_work(self, release: GeRelease) -> None:
        try:
            path = download_and_install(
                release,
                progress=self._installProgress.emit,
                cancel=self._cancel.is_set,
            )
        except GeProtonCancelled:
            self._installFailed.emit("Install cancelled.", True)
            return
        except GeProtonError as exc:
            self._installFailed.emit(str(exc), False)
            return
        self._installDone.emit(path.name)

    def _remove_work(self, name: str) -> None:
        try:
            remove_tool(name)
        except GeProtonError as exc:
            self._removeDone.emit(name, str(exc))
            return
        self._removeDone.emit(name, "")

    def _open_folder_work(self) -> None:
        from ..core.system_open import open_path

        target = install_dir()
        target.mkdir(parents=True, exist_ok=True)
        open_path(str(target))

    # --- GUI-thread handlers --------------------------------------------------

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
        self.busyChanged.emit()

    def _on_refreshed(self, installed: list, releases: list, error: str) -> None:
        self._installed = installed
        # keep the last good release list when GitHub is unreachable
        if releases or not error:
            self._releases = releases
            self._release_objs = self._pending_release_objs
        if error:
            self._error = error
            self.errorChanged.emit()
        self._set_busy(False)
        self.installedChanged.emit()
        self.releasesChanged.emit()

    def _on_progress(self, downloaded: int, total: int) -> None:
        if not self._installing_tag:
            return
        if total > 0:
            self._progress = max(0.0, min(1.0, downloaded / total))
            self._progress_label = f"{human_size(downloaded)} of {human_size(total)}"
        else:
            self._progress = 0.0
            self._progress_label = human_size(downloaded)
        self.progressChanged.emit()

    def _on_installed(self, name: str) -> None:
        self._installing_tag = ""
        self._progress = 1.0
        self._progress_label = ""
        self._status = f"Installed {name}. Restart Steam to see it in the Proton picker."
        self.progressChanged.emit()
        self.statusChanged.emit()
        self._set_busy(False)
        self.toolsChanged.emit()
        self.refresh()

    def _on_install_failed(self, message: str, cancelled: bool) -> None:
        self._installing_tag = ""
        self._progress = 0.0
        self._progress_label = ""
        if cancelled:
            self._status = message
            self.statusChanged.emit()
        else:
            self._error = message
            self.errorChanged.emit()
        self.progressChanged.emit()
        self._set_busy(False)

    def _on_removed(self, name: str, error: str) -> None:
        if error:
            self._error = error
            self.errorChanged.emit()
            self._set_busy(False)
            return
        self._status = f"Removed {name}."
        self.statusChanged.emit()
        self._set_busy(False)
        self.toolsChanged.emit()
        self.refresh()

    def _on_work_error(self, message: str) -> None:
        self._installing_tag = ""
        self._error = message
        self.errorChanged.emit()
        self._set_busy(False)
