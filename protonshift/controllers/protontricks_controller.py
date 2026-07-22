"""QObject bridge for per-game protontricks (winetricks) actions.

Driven by ``appId`` (set when the game-detail dialog opens). Exposes the curated
verb shortlist, kicks off a batched verb install on a worker thread, and can
open the interactive GUI. Verb runs can take minutes and stream a lot of output,
so ``running`` gates the UI and ``output`` carries the tail of the log.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.protontricks import (
    COMMON_VERBS,
    is_available,
    launch_gui,
    run_verbs,
)


class ProtontricksController(QObject):
    appIdChanged = Signal()
    gameNameChanged = Signal()
    runningChanged = Signal()
    statusChanged = Signal()
    outputChanged = Signal()

    _runResult = Signal(str, bool, str)  # app_id, ok, output

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._game_name = ""
        self._running = False
        self._status = ""
        self._output = ""
        self._available = is_available()
        self._verbs = [{"verb": v, "label": lbl} for v, lbl in COMMON_VERBS]
        self._runResult.connect(self._on_run)

    # --- static ---------------------------------------------------------------

    @Property(bool, constant=True)
    def available(self) -> bool:
        return self._available

    @Property("QVariantList", constant=True)
    def verbs(self) -> list:
        return self._verbs

    # --- inputs ---------------------------------------------------------------

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self._status = ""
        self._output = ""
        self.appIdChanged.emit()
        self.statusChanged.emit()
        self.outputChanged.emit()

    @Property(str, notify=gameNameChanged)
    def gameName(self) -> str:  # noqa: N802
        return self._game_name

    @gameName.setter
    def gameName(self, value: str) -> None:  # noqa: N802
        if value == self._game_name:
            return
        self._game_name = value
        self.gameNameChanged.emit()

    # --- reactive -------------------------------------------------------------

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._running

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=outputChanged)
    def output(self) -> str:
        return self._output

    # --- actions --------------------------------------------------------------

    @Slot("QStringList")
    def installVerbs(self, verbs: list) -> None:  # noqa: N802
        if self._running or not self._app_id:
            return
        clean = [str(v) for v in verbs if str(v).strip()]
        if not clean:
            self._status = "Pick at least one component."
            self.statusChanged.emit()
            return
        self._running = True
        self._status = "Installing " + ", ".join(clean) + "…"
        self._output = ""
        self.runningChanged.emit()
        self.statusChanged.emit()
        self.outputChanged.emit()
        threading.Thread(
            target=self._run_work, args=(self._app_id, clean), daemon=True
        ).start()

    @Slot()
    def openGui(self) -> None:  # noqa: N802
        ok, msg = launch_gui(self._app_id)
        self._status = msg
        self.statusChanged.emit()

    # --- worker ---------------------------------------------------------------

    def _run_work(self, app_id: str, verbs: list) -> None:
        ok, output = run_verbs(app_id, verbs)
        self._runResult.emit(app_id, ok, output)

    def _on_run(self, app_id: str, ok: bool, output: str) -> None:
        if app_id != self._app_id:
            return
        self._running = False
        # Keep only the tail — winetricks logs are enormous.
        lines = output.splitlines()
        self._output = "\n".join(lines[-40:])
        self._status = "Done." if ok else "Install failed — see log below."
        self.runningChanged.emit()
        self.outputChanged.emit()
        self.statusChanged.emit()
