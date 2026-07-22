"""QObject bridge for the Displays page: outputs, modes, resolution switching.

Enumerating outputs shells out to xrandr/wlr-randr/kscreen-doctor (a second or
two), so discovery runs on a worker thread. Applying a mode also runs off the UI
thread and re-reads afterwards so the current-mode highlight reflects reality
(a compositor may reject or clamp the request).
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.display import list_outputs, set_mode
from ._worker import start_worker


class DisplayController(QObject):
    outputsChanged = Signal()
    backendChanged = Signal()
    loadingChanged = Signal()
    statusChanged = Signal()

    _listResult = Signal(str, list)  # backend, outputs
    _applyResult = Signal(bool, str)  # ok, message
    _workError = Signal(str)  # unexpected worker exception -> clear + status

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = ""
        self._outputs: list[dict] = []
        self._loading = False
        self._status = ""
        self._listResult.connect(self._on_list)
        self._applyResult.connect(self._on_apply)
        self._workError.connect(self._on_work_error)
        self.refresh()

    # --- reactive -------------------------------------------------------------

    @Property(str, notify=backendChanged)
    def backend(self) -> str:
        return self._backend

    @Property("QVariantList", notify=outputsChanged)
    def outputs(self) -> list:
        return self._outputs

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

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
        start_worker(self._list_work, on_error=self._workError.emit)

    @Slot(str, int, int, float)
    def applyMode(self, output: str, width: int, height: int, refresh: float) -> None:  # noqa: N802
        start_worker(
            self._apply_work, output, width, height, refresh,
            on_error=lambda m: self._applyResult.emit(False, f"Apply failed: {m}"),
        )

    # --- workers --------------------------------------------------------------

    def _list_work(self) -> None:
        backend, outputs = list_outputs()
        payload = [
            {
                "name": o.name,
                "connected": o.connected,
                "enabled": o.enabled,
                "primary": o.primary,
                "currentKey": o.current.key if o.current else "",
                "currentLabel": o.current.label if o.current else "",
                "modes": [
                    {
                        "key": m.key,
                        "label": m.label,
                        "width": m.width,
                        "height": m.height,
                        "refresh": m.refresh,
                    }
                    for m in o.modes
                ],
            }
            for o in outputs
            if o.connected
        ]
        self._listResult.emit(backend, payload)

    def _apply_work(self, output: str, width: int, height: int, refresh: float) -> None:
        ok, msg = set_mode(output, width, height, refresh)
        self._applyResult.emit(ok, msg)

    def _on_list(self, backend: str, outputs: list) -> None:
        self._backend = backend
        self._outputs = outputs
        self._loading = False
        self.backendChanged.emit()
        self.outputsChanged.emit()
        self.loadingChanged.emit()

    def _on_apply(self, ok: bool, msg: str) -> None:
        self._status = msg
        self.statusChanged.emit()
        # Re-read so the highlighted current mode reflects what actually stuck.
        self.refresh()

    def _on_work_error(self, message: str) -> None:
        # List-worker failure: clear loading, surface status, no auto-retry.
        self._loading = False
        self._status = f"Unexpected error: {message}"
        self.loadingChanged.emit()
        self.statusChanged.emit()
