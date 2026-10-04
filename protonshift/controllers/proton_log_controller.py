"""QObject bridge for the Proton log viewer.

Shows the tail of ``steam-<appid>.log`` (written when ``PROTON_LOG=1`` is in
the launch options). Reading runs on a worker thread: the file can be large.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ..core import proton_log
from ..core.fsutil import human_size
from ..core.system_open import open_path
from ._worker import start_worker


class ProtonLogController(QObject):
    changed = Signal()  # everything shown

    _result = Signal(str, bool, str, str, str, bool, int)
    # app_id, exists, text-or-error, size label, modified label, truncated, problem count

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._loading = False
        self._exists = False
        self._text = ""
        self._error = ""
        self._size = ""
        self._modified = ""
        self._truncated = False
        self._problems = 0
        self._problems_only = False
        self._notice = ""
        self._result.connect(self._on_result)

    @Property(str, notify=changed)
    def path(self) -> str:
        path = proton_log.log_path(self._app_id)
        return str(path) if path else ""

    @Property(bool, notify=changed)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=changed)
    def exists(self) -> bool:
        return self._exists

    @Property(str, notify=changed)
    def text(self) -> str:
        return self._text

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Property(str, notify=changed)
    def sizeLabel(self) -> str:
        return self._size

    @Property(str, notify=changed)
    def modifiedLabel(self) -> str:
        return self._modified

    @Property(bool, notify=changed)
    def truncated(self) -> bool:
        return self._truncated

    @Property(int, notify=changed)
    def problemCount(self) -> int:
        return self._problems

    @Property(bool, notify=changed)
    def problemsOnly(self) -> bool:
        return self._problems_only

    @Property(str, notify=changed)
    def notice(self) -> str:
        return self._notice

    @Slot(str, result=bool)
    def loggingEnabled(self, launch_options: str) -> bool:
        return proton_log.logging_enabled(launch_options)

    @Slot(str)
    def open(self, app_id: str) -> None:
        """Point the viewer at a game and read its log."""
        self._app_id = app_id
        self._problems_only = False
        self._notice = ""
        self.refresh()

    @Slot(bool)
    def setProblemsOnly(self, value: bool) -> None:
        if value != self._problems_only:
            self._problems_only = value
            self.refresh()

    @Slot()
    def refresh(self) -> None:
        self._loading = True
        self.changed.emit()
        app_id = self._app_id
        start_worker(
            self._work, app_id, self._problems_only,
            on_error=lambda m: self._result.emit(app_id, True, f"Couldn't read the log: {m}", "", "", False, -1),
        )

    def _work(self, app_id: str, problems_only: bool) -> None:
        path = proton_log.log_path(app_id)
        if path is None or not path.is_file():
            self._result.emit(app_id, False, "", "", "", False, 0)
            return
        try:
            tail = proton_log.read_tail(path, problems_only=problems_only)
        except OSError as exc:
            self._result.emit(app_id, True, f"Couldn't read the log: {exc}", "", "", False, -1)
            return
        self._result.emit(app_id, True, tail.text, human_size(tail.total_bytes),
                          proton_log.modified_label(path), tail.truncated, tail.problem_count)

    def _on_result(self, app_id: str, exists: bool, text: str, size: str, modified: str,
                   truncated: bool, problems: int) -> None:
        if app_id != self._app_id:
            return
        failed = problems < 0
        self._loading = False
        self._exists = exists
        self._text = "" if failed else text
        self._error = text if failed else ""
        self._size = size
        self._modified = modified
        self._truncated = truncated
        self._problems = max(problems, 0)
        self.changed.emit()

    @Slot(result=bool)
    def copy(self) -> bool:
        clipboard = QGuiApplication.clipboard()
        if clipboard is None or not self._text:
            return False
        clipboard.setText(self._text)
        self._notice = "Copied what is shown to the clipboard."
        self.changed.emit()
        return True

    @Slot(result=bool)
    def openFile(self) -> bool:
        ok, message = open_path(self.path) if self.path else (False, "No log file.")
        self._notice = "" if ok else (message or "Couldn't open the file.")
        self.changed.emit()
        return ok
