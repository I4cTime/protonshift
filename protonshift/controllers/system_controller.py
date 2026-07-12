"""QObject bridge for the System dashboard: GPU, power profile, session info.

GPU discovery shells out to nvidia-smi / sysfs (up to a few seconds), so it runs
on a worker thread. Session/host info is cheap and read synchronously at init.
"""

from __future__ import annotations

import os
import platform
import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.gpu import (
    get_current_power_profile,
    get_gpu_info,
    get_power_profiles,
    set_power_profile,
)


def _os_release_pretty() -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or ""


def _system_info() -> dict:
    u = platform.uname()
    return {
        "kernel": u.release,
        "arch": u.machine,
        "hostname": u.node,
        "sessionType": os.environ.get("XDG_SESSION_TYPE", "") or "unknown",
        "desktop": (
            os.environ.get("XDG_CURRENT_DESKTOP", "")
            or os.environ.get("DESKTOP_SESSION", "")
            or "unknown"
        ),
        "distro": _os_release_pretty(),
        "cpu": _cpu_model(),
    }


class SystemController(QObject):
    gpusChanged = Signal()
    powerChanged = Signal()
    loadingChanged = Signal()
    statusChanged = Signal()

    _gpuResult = Signal(list, list, str)  # gpus, profiles, current
    _powerResult = Signal(bool, str, str)  # ok, msg, applied_profile

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._info = _system_info()
        self._gpus: list[dict] = []
        self._profiles: list[str] = []
        self._current = ""
        self._loading = False
        self._status = ""
        self._gpuResult.connect(self._on_gpu)
        self._powerResult.connect(self._on_power)
        self.refresh()

    # --- static-ish -----------------------------------------------------------

    @Property("QVariantMap", constant=True)
    def systemInfo(self) -> dict:  # noqa: N802
        return self._info

    # --- reactive -------------------------------------------------------------

    @Property("QVariantList", notify=gpusChanged)
    def gpus(self) -> list:
        return self._gpus

    @Property("QStringList", notify=powerChanged)
    def powerProfiles(self) -> list:  # noqa: N802
        return self._profiles

    @Property(str, notify=powerChanged)
    def currentProfile(self) -> str:  # noqa: N802
        return self._current

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
        threading.Thread(target=self._gpu_work, daemon=True).start()

    @Slot(str)
    def setPowerProfile(self, profile: str) -> None:  # noqa: N802
        if profile == self._current:
            return
        threading.Thread(target=self._power_work, args=(profile,), daemon=True).start()

    # --- workers --------------------------------------------------------------

    def _gpu_work(self) -> None:
        gpus = [
            {
                "name": g.name,
                "driver": g.driver,
                "vramMb": g.vram_mb if g.vram_mb is not None else -1,
                "temperature": g.temperature if g.temperature is not None else -1.0,
            }
            for g in get_gpu_info()
        ]
        profiles = get_power_profiles()
        current = get_current_power_profile() or ""
        self._gpuResult.emit(gpus, profiles, current)

    def _power_work(self, profile: str) -> None:
        ok, msg = set_power_profile(profile)
        applied = get_current_power_profile() or "" if ok else self._current
        self._powerResult.emit(ok, msg, applied)

    def _on_gpu(self, gpus: list, profiles: list, current: str) -> None:
        self._gpus = gpus
        self._profiles = profiles
        self._current = current
        self._loading = False
        self.gpusChanged.emit()
        self.powerChanged.emit()
        self.loadingChanged.emit()

    def _on_power(self, ok: bool, msg: str, applied: str) -> None:
        self._current = applied
        self._status = msg if msg else ("Power profile set" if ok else "Couldn't set power profile")
        self.powerChanged.emit()
        self.statusChanged.emit()
