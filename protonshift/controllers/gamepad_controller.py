"""QObject bridge for the Controllers page: detection, SDL mapping, live tester.

Detection runs on a worker thread. The live tester opens the selected joystick
and polls its event stream on a daemon thread, pushing button/axis state back to
QML via a queued signal so the visualiser updates in real time.
"""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ..core.input_devices import (
    ControllerInfo,
    get_controllers,
    get_sdl_mapping,
    js_counts,
    open_js,
    read_js_events,
    rumble,
)


class GamepadController(QObject):
    controllersChanged = Signal()
    loadingChanged = Signal()
    testChanged = Signal()
    stateChanged = Signal()
    statusChanged = Signal()

    _listResult = Signal(list)
    _stateResult = Signal(list, list)  # buttons, axes

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controllers: list[dict] = []
        self._loading = False
        self._status = ""
        # live test state
        self._test_path = ""
        self._test_name = ""
        self._buttons: list[bool] = []
        self._axes: list[float] = []
        self._test_fd: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._infos: dict[str, ControllerInfo] = {}
        self._listResult.connect(self._on_list)
        self._stateResult.connect(self._on_state)
        self.refresh()

    # --- reactive -------------------------------------------------------------

    @Property("QVariantList", notify=controllersChanged)
    def controllers(self) -> list:
        return self._controllers

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(str, notify=testChanged)
    def testingPath(self) -> str:  # noqa: N802
        return self._test_path

    @Property(str, notify=testChanged)
    def testingName(self) -> str:  # noqa: N802
        return self._test_name

    @Property("QVariantList", notify=stateChanged)
    def buttons(self) -> list:
        return self._buttons

    @Property("QVariantList", notify=stateChanged)
    def axes(self) -> list:
        return self._axes

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()
        threading.Thread(target=self._list_work, daemon=True).start()

    @Slot(str)
    def copyMapping(self, controller_id: str) -> None:  # noqa: N802
        info = self._infos.get(controller_id)
        if not info:
            return
        mapping = get_sdl_mapping(info)
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(mapping)
        self._status = "SDL mapping copied to clipboard."
        self.statusChanged.emit()

    @Slot(str)
    def rumble(self, device_path: str) -> None:
        ok, msg = rumble(device_path)
        self._status = msg
        self.statusChanged.emit()

    @Slot(str, str)
    def startTest(self, device_path: str, name: str) -> None:  # noqa: N802
        self.stopTest()
        fd = open_js(device_path)
        if fd is None:
            self._status = f"Couldn't open {device_path} (permissions?)."
            self.statusChanged.emit()
            return
        naxes, nbtn = js_counts(device_path)
        self._test_fd = fd
        self._test_path = device_path
        self._test_name = name
        self._buttons = [False] * max(nbtn, 1)
        self._axes = [0.0] * max(naxes, 1)
        self._stop.clear()
        self._thread = threading.Thread(target=self._test_loop, args=(fd, device_path), daemon=True)
        self._thread.start()
        self.testChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def stopTest(self) -> None:  # noqa: N802
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)
        self._thread = None
        if self._test_fd is not None:
            import os

            try:
                os.close(self._test_fd)
            except OSError:
                pass
            self._test_fd = None
        if self._test_path:
            self._test_path = ""
            self._test_name = ""
            self.testChanged.emit()

    # --- workers --------------------------------------------------------------

    def _list_work(self) -> None:
        infos = get_controllers()
        self._infos = {c.id: c for c in infos}
        rows = [
            {
                "id": c.id, "name": c.name, "devicePath": c.device_path,
                "type": c.controller_type, "vendor": c.vendor_id, "product": c.product_id,
            }
            for c in infos
        ]
        self._listResult.emit(rows)

    def _test_loop(self, fd: int, path: str) -> None:
        buttons = list(self._buttons)
        axes = list(self._axes)
        while not self._stop.is_set():
            changed = False
            for kind, num, val in read_js_events(fd):
                if kind == "button" and num < len(buttons):
                    buttons[num] = val > 0.5
                    changed = True
                elif kind == "axis" and num < len(axes):
                    axes[num] = val
                    changed = True
            if changed:
                self._stateResult.emit(list(buttons), list(axes))
            time.sleep(0.016)

    def _on_list(self, rows: list) -> None:
        self._controllers = rows
        self._loading = False
        self.controllersChanged.emit()
        self.loadingChanged.emit()

    def _on_state(self, buttons: list, axes: list) -> None:
        self._buttons = buttons
        self._axes = axes
        self.stateChanged.emit()
