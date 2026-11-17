"""QObject bridge for Diagnose: one ranked list of reasons a game may not start or run well.

``run`` gathers everything on a worker thread (``core.diagnose.collect``) and
keeps the :class:`~protonshift.core.diagnose.Report` and its findings here;
QML only ever sees plain rows (``to_row``) and maps. A result from an older run
(another game, or a run that was started again) is dropped, so switching games
never shows the previous game's findings.

A fix goes preview first, then apply: ``openPreview`` plans it on the GUI
thread (``fix_apply.plan`` is pure), ``apply`` plans it again from the same
report and writes it on a worker. ``apply_change`` itself refuses a plan made
from settings that changed on disk since, so the user is never surprised.
After a write that worked, ``settingsWritten`` fires (``app.py`` reloads the
launch options editor and plays the chime) and the diagnosis runs again.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ..core import diagnose, fix_apply
from ..core.snapshots import GameState, Snapshot
from ._worker import start_worker

_SEVERITIES = diagnose.SEVERITY_ORDER


def _when_label(taken_at: str) -> str:
    """A snapshot's ISO time as the user's local clock reads it ("today at 14:05")."""
    try:
        moment = datetime.fromisoformat(taken_at).astimezone()
    except (TypeError, ValueError):
        return ""
    clock = moment.strftime("%H:%M")
    today = datetime.now().astimezone().date()
    if moment.date() == today:
        return f"today at {clock}"
    if moment.date() == today - timedelta(days=1):
        return f"yesterday at {clock}"
    return f"{moment.day} {moment.strftime('%b %Y')} at {clock}"


def _checked_line(report: diagnose.Report, shortcut: bool, native: bool) -> str:
    parts = ["the shortcut's launch options" if shortcut else "the launch options saved in Steam"]
    if not native:
        parts.append("the Proton build")
    if any(f.id == "log-read" for f in report.findings):
        parts.append("the Proton log")
    parts.append("the problems ProtonShift knows about")
    parts.append("this PC")
    listed = ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Checked {listed}. Diagnose only reads; it does not start the game."


class DiagnoseController(QObject):
    runningChanged = Signal()
    reportChanged = Signal()  # findings / summary / counts / canApply / steamRunning / logPath / checked
    busyChanged = Signal()
    statusChanged = Signal()
    undoChanged = Signal()  # undoAvailable / undoLabel / undoWhen / undoConflict
    previewChanged = Signal()

    # A fix or its undo was written (app_id, ok). app.py chimes on it and, when
    # ok, reloads the launch options editor so it shows what Steam now has.
    settingsWritten = Signal(str, bool)

    _runResult = Signal(int, object, object)  # run token, Report, Snapshot | None
    _runError = Signal(int, str)  # run token, message
    _writeResult = Signal(str, object, object, bool)  # app_id, ApplyResult, Snapshot | None, undo conflict
    _writeError = Signal(str, str)  # app_id, message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._run_args: tuple | None = None
        self._run_token = 0
        self._running = False
        self._report: diagnose.Report | None = None
        self._findings: dict[str, diagnose.Finding] = {}
        self._rows: list[dict] = []
        self._summary = ""
        self._checked = ""
        self._error = ""
        self._shortcut_options: str | None = None
        self._busy = False
        self._status = ""
        self._status_ok = True
        self._undo: Snapshot | None = None
        self._undo_conflict = ""
        self._preview: dict = {}
        self._runResult.connect(self._on_run_result)
        self._runError.connect(self._on_run_error)
        self._writeResult.connect(self._on_write_result)
        self._writeError.connect(self._on_write_error)

    # --- state ------------------------------------------------------------------

    @Property(str, notify=reportChanged)
    def appId(self) -> str:
        return self._app_id

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._running

    @Property("QVariantList", notify=reportChanged)
    def findings(self) -> list:
        return self._rows

    @Property(str, notify=reportChanged)
    def summary(self) -> str:
        return self._summary

    @Property(str, notify=reportChanged)
    def checked(self) -> str:
        """A quiet line naming what the diagnosis looked at."""
        return self._checked

    @Property(str, notify=reportChanged)
    def error(self) -> str:
        """Why the diagnosis itself failed; "" when it ran."""
        return self._error

    @Property("QVariantMap", notify=reportChanged)
    def counts(self) -> dict:
        """Findings per severity, every severity present (0 when none)."""
        out = dict.fromkeys(_SEVERITIES, 0)
        for row in self._rows:
            out[row["severity"]] = out.get(row["severity"], 0) + 1
        return out

    @Property(bool, notify=reportChanged)
    def hasBlocking(self) -> bool:
        return any(row["severity"] == "blocking" for row in self._rows)

    @Property(bool, notify=reportChanged)
    def canApply(self) -> bool:
        """False for Non-Steam shortcuts and for Steam settings that could not be read."""
        return bool(self._report and self._report.can_apply)

    @Property(bool, notify=reportChanged)
    def isShortcut(self) -> bool:
        return self._shortcut_options is not None

    @Property(str, notify=reportChanged)
    def steamRunning(self) -> str:
        """``"yes"``, ``"no"`` or ``"unknown"``."""
        running = self._report.steam_running if self._report else None
        return "unknown" if running is None else ("yes" if running else "no")

    @Property(str, notify=reportChanged)
    def logPath(self) -> str:
        return self._report.log_path if self._report else ""

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        """An apply or an undo is being written."""
        return self._busy

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=statusChanged)
    def statusOk(self) -> bool:
        return self._status_ok

    @Property(bool, notify=undoChanged)
    def undoAvailable(self) -> bool:
        return self._undo is not None

    @Property(str, notify=undoChanged)
    def undoLabel(self) -> str:
        return self._undo.label if self._undo else ""

    @Property(str, notify=undoChanged)
    def undoWhen(self) -> str:
        return _when_label(self._undo.taken_at) if self._undo else ""

    @Property(str, notify=undoChanged)
    def undoConflict(self) -> str:
        """Why Undo refused (the settings changed after the fix); "" otherwise."""
        return self._undo_conflict

    @Property("QVariantMap", notify=previewChanged)
    def preview(self) -> dict:
        """The fix being previewed; empty when none is open."""
        return self._preview

    # --- running ------------------------------------------------------------------

    @Slot(str, str, str, bool, str, bool, str)
    def run(self, app_id: str, install_path: str, prefix_path: str, is_shortcut: bool,
            shortcut_options: str, native: bool, protondb_tier: str) -> None:
        """Diagnose one game. ``shortcut_options`` is used only for a Non-Steam shortcut."""
        self._start(app_id, (install_path, prefix_path, shortcut_options if is_shortcut else None,
                             native, protondb_tier))

    def _start(self, app_id: str, args: tuple) -> None:
        if app_id != self._app_id:
            # Another game: nothing from the previous one may stay on screen.
            self._report = None
            self._findings = {}
            self._rows = []
            self._summary = ""
            self._checked = ""
            self._undo = None
            self._undo_conflict = ""
            self._set_status("", True)
            self.undoChanged.emit()
        self._app_id = app_id
        self._run_args = args
        self._shortcut_options = args[2]
        self._error = ""
        self._run_token += 1
        token = self._run_token
        self._running = True
        self._clear_preview()
        self.runningChanged.emit()
        self.reportChanged.emit()
        if not app_id:
            self._on_run_error(token, "No game is selected.")
            return
        start_worker(self._run_work, token, app_id, *args,
                     on_error=lambda message: self._runError.emit(token, message))

    def _run_work(self, token: int, app_id: str, install_path: str, prefix_path: str,
                  shortcut_options: str | None, native: bool, protondb_tier: str) -> None:
        report = diagnose.collect(
            app_id,
            install_path=install_path,
            prefix_path=prefix_path,
            shortcut_options=shortcut_options,
            native=native,
            protondb_tier=protondb_tier,
        )
        undo = fix_apply.undo_available(app_id) if shortcut_options is None else None
        self._runResult.emit(token, report, undo)

    def _on_run_result(self, token: int, report: diagnose.Report, undo: Snapshot | None) -> None:
        if token != self._run_token or report.app_id != self._app_id:
            return  # an older run, or a game the user has moved on from
        args = self._run_args or ("", "", None, False, "")
        self._report = report
        self._findings = {f.id: f for f in report.findings}
        self._rows = [diagnose.to_row(f) for f in report.findings]
        self._summary = report.summary
        self._checked = _checked_line(report, shortcut=args[2] is not None, native=bool(args[3]))
        self._error = ""
        self._undo = undo
        self._running = False
        self.reportChanged.emit()
        self.undoChanged.emit()
        self.runningChanged.emit()

    def _on_run_error(self, token: int, message: str) -> None:
        if token != self._run_token:
            return
        self._report = None
        self._findings = {}
        self._rows = []
        self._summary = ""
        self._checked = ""
        self._error = f"Diagnose could not finish: {message}"
        self._running = False
        self.reportChanged.emit()
        self.runningChanged.emit()

    def _rerun(self) -> None:
        if self._run_args is not None and self._app_id:
            self._start(self._app_id, self._run_args)

    # --- preview ------------------------------------------------------------------

    def _planning_state(self) -> tuple[GameState | None, str]:
        """The settings a plan starts from, or ``(None, reason)`` when there are none to plan on."""
        if self._shortcut_options is not None:
            # Steam keeps a shortcut's launch options in the shortcut; its Proton
            # choice is not something ProtonShift can change for it.
            return GameState(launch_options=self._shortcut_options, compat_tool=""), ""
        if self._report is not None and self._report.state is not None:
            return self._report.state, ""
        return None, ("Steam's settings for this game could not be read, so ProtonShift cannot work out "
                      "the change. Follow the steps above by hand.")

    def _plan(self, finding_id: str) -> tuple[diagnose.Finding | None, fix_apply.Change | None, str]:
        finding = self._findings.get(finding_id)
        if finding is None:
            return None, None, ""
        state, reason = self._planning_state()
        if state is None:
            return finding, None, reason
        return finding, fix_apply.plan(finding.actions, state), ""

    @Slot(str)
    def openPreview(self, finding_id: str) -> None:
        """Work out what a fix would change and show it (pure: nothing is written)."""
        finding, change, reason = self._plan(finding_id)
        if finding is None:
            self._clear_preview()
            return
        manual = [a.text for a in finding.actions if a.type == "manual"]
        preview = {
            "findingId": finding.id,
            "title": finding.title,
            "beforeLaunch": "", "afterLaunch": "", "launchChanged": False,
            "beforeProton": "", "afterProton": "", "protonChanged": False,
            "manual": manual,
            "blocked": reason,
            "changed": False,
            "mode": "none",  # "apply" | "copy" | "none"
        }
        if change is not None:
            launch_changed = change.after.launch_options != change.before.launch_options
            proton_changed = change.after.compat_tool != change.before.compat_tool
            preview.update({
                "beforeLaunch": change.before.launch_options,
                "afterLaunch": change.after.launch_options,
                "launchChanged": launch_changed,
                "beforeProton": change.before.compat_tool,
                "afterProton": change.after.compat_tool,
                "protonChanged": proton_changed,
                "manual": list(change.manual),
                "blocked": change.blocked,
                "changed": change.changed,
            })
            if not change.blocked and change.changed:
                if self.canApply:
                    preview["mode"] = "apply"
                elif self._shortcut_options is not None and launch_changed:
                    preview["mode"] = "copy"
        self._preview = preview
        self.previewChanged.emit()

    @Slot()
    def clearPreview(self) -> None:
        self._clear_preview()

    def _clear_preview(self) -> None:
        if self._preview:
            self._preview = {}
            self.previewChanged.emit()

    @Slot(str, result=bool)
    def copyProposed(self, finding_id: str) -> bool:
        """Copy the launch options a fix would give (for shortcuts, which ProtonShift cannot write)."""
        _finding, change, _reason = self._plan(finding_id)
        clipboard = QGuiApplication.clipboard()
        if change is None or change.blocked or clipboard is None:
            self._set_status("There is nothing to copy for this fix.", False)
            return False
        clipboard.setText(change.after.launch_options)
        self._set_status("Copied the new launch options. Paste them into the shortcut's properties in Steam.",
                         True)
        return True

    # --- writing ------------------------------------------------------------------

    @Slot(str)
    def apply(self, finding_id: str) -> None:
        """Write one fix to Steam's files, after saving a snapshot so it can be undone."""
        if self._busy or self._running:
            return
        report = self._report
        finding = self._findings.get(finding_id)
        if report is None or finding is None or not report.can_apply or report.state is None:
            self._set_status("This fix cannot be applied here.", False)
            return
        localconfig, config_vdf = report.paths
        self._begin_write()
        app_id = report.app_id
        start_worker(self._apply_work, app_id, localconfig, config_vdf, finding, report.state,
                     on_error=lambda message: self._writeError.emit(app_id, message))

    def _apply_work(self, app_id, localconfig, config_vdf, finding, state) -> None:
        change = fix_apply.plan(finding.actions, state)
        result = fix_apply.apply_change(localconfig, config_vdf, app_id, change,
                                        label=finding.title, finding_id=finding.id)
        self._writeResult.emit(app_id, result, fix_apply.undo_available(app_id), False)

    @Slot(bool)
    def undo(self, force: bool) -> None:
        """Put back the settings from before the latest fix. ``force`` overwrites later changes."""
        if self._busy or self._running:
            return
        report = self._report
        if report is None or self._undo is None:
            self._set_status("There is no fix to undo for this game.", False)
            return
        localconfig, config_vdf = report.paths
        self._begin_write()
        app_id = report.app_id
        start_worker(self._undo_work, app_id, localconfig, config_vdf, force,
                     on_error=lambda message: self._writeError.emit(app_id, message))

    def _undo_work(self, app_id, localconfig, config_vdf, force: bool) -> None:
        snap = fix_apply.undo_available(app_id)
        current = fix_apply.read_state(localconfig, config_vdf, app_id)
        # The same test undo_latest refuses on: settings that are neither the
        # fix's before nor its after were changed by someone since.
        conflict = (not force and snap is not None and current is not None
                    and current not in (snap.before, snap.after))
        result = fix_apply.undo_latest(localconfig, config_vdf, app_id, force=force)
        self._writeResult.emit(app_id, result, fix_apply.undo_available(app_id), conflict and not result.ok)

    @Slot()
    def dismissUndoConflict(self) -> None:
        """Keep the settings as they are now; the fix stays undoable."""
        if self._undo_conflict:
            self._undo_conflict = ""
            self.undoChanged.emit()

    def _begin_write(self) -> None:
        self._busy = True
        self._undo_conflict = ""
        self.busyChanged.emit()
        self.undoChanged.emit()

    def _on_write_result(self, app_id: str, result: fix_apply.ApplyResult, undo: Snapshot | None,
                         conflict: bool) -> None:
        self._busy = False
        self.busyChanged.emit()
        if app_id == self._app_id:
            self._undo = undo
            self._undo_conflict = result.message if conflict else ""
            self.undoChanged.emit()
            if not conflict:
                self._set_status(result.message, result.ok)
        self.settingsWritten.emit(app_id, result.ok)
        # The list has to show the settings as they are now; a plan refused
        # because the settings moved needs a fresh report too.
        if app_id == self._app_id and not conflict and (result.ok or result.state is not None):
            self._rerun()

    def _on_write_error(self, app_id: str, message: str) -> None:
        self._busy = False
        self.busyChanged.emit()
        self.settingsWritten.emit(app_id, False)
        if app_id == self._app_id:
            self._set_status(f"Something went wrong, so the change may not be complete: {message}", False)
            self._rerun()

    def _set_status(self, text: str, ok: bool) -> None:
        if text != self._status or ok != self._status_ok:
            self._status = text
            self._status_ok = ok
            self.statusChanged.emit()
