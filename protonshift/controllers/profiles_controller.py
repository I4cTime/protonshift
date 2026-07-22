"""QObject bridge for configuration profiles.

A profile is a named snapshot of a game's launch options + compat tool plus the
system-wide gaming env vars and power profile. Capturing and applying both touch
several config files / tools, so they run on worker threads.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Signal, Slot


class ProfilesController(QObject):
    appIdChanged = Signal()
    profilesChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()

    _listResult = Signal(list)
    _actionResult = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._profiles: list[str] = []
        self._status = ""
        self._busy = False
        self._listResult.connect(self._on_list)
        self._actionResult.connect(self._on_action)
        self.refresh()

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self.appIdChanged.emit()

    @Property("QStringList", notify=profilesChanged)
    def profiles(self) -> list:
        return self._profiles

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    # --- actions --------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        threading.Thread(target=self._list_work, daemon=True).start()

    @Slot(str)
    def saveCurrent(self, name: str) -> None:  # noqa: N802
        name = name.strip()
        if self._busy or not name or not self._app_id:
            return
        self._begin(f"Capturing “{name}”…")
        threading.Thread(target=self._save_work, args=(name, self._app_id), daemon=True).start()

    @Slot(str)
    def apply(self, name: str) -> None:
        if self._busy or not name or not self._app_id:
            return
        self._begin(f"Applying “{name}”…")
        threading.Thread(target=self._apply_work, args=(name, self._app_id), daemon=True).start()

    @Slot(str)
    def deleteProfile(self, name: str) -> None:  # noqa: N802
        from ..core.profiles_storage import delete_profile

        ok = delete_profile(name)
        self._status = f"Deleted “{name}”." if ok else "Couldn't delete profile."
        self.statusChanged.emit()
        self.refresh()

    # --- workers --------------------------------------------------------------

    def _list_work(self) -> None:
        from ..core.profiles_storage import list_profiles

        self._listResult.emit(list_profiles())

    def _save_work(self, name: str, app_id: str) -> None:
        from ..core.compat_tool import get_config_vdf_path, read_compat_tool
        from ..core.env_vars import read_gaming_env
        from ..core.gpu import get_current_power_profile
        from ..core.profiles_storage import ApplicationProfile, save_profile
        from ..core.steam import discover_games, get_localconfig_path
        from ..core.vdf_config import read_launch_options

        root, _ = discover_games()
        launch_opts = ""
        compat = ""
        if root:
            lc = get_localconfig_path(root)
            if lc:
                ok, val = read_launch_options(lc, app_id)
                launch_opts = val if ok else ""
            ok, compat = read_compat_tool(get_config_vdf_path(root), app_id)
        env = read_gaming_env()
        power = get_current_power_profile() or ""
        prof = ApplicationProfile(
            name=name,
            launch_options=launch_opts,
            compat_tool=compat,
            env_vars=env,
            power_profile=power,
        )
        ok = save_profile(prof)
        self._actionResult.emit(f"Saved “{name}”." if ok else "Couldn't save profile.")

    def _apply_work(self, name: str, app_id: str) -> None:
        from ..core.compat_tool import get_config_vdf_path, set_compat_tool
        from ..core.env_vars import write_gaming_env
        from ..core.gpu import set_power_profile
        from ..core.profiles_storage import load_profile
        from ..core.steam import discover_games, get_localconfig_path
        from ..core.vdf_config import set_launch_options

        prof = load_profile(name)
        if prof is None:
            self._actionResult.emit("Couldn't load profile.")
            return
        applied: list[str] = []
        root, _ = discover_games()
        if root:
            lc = get_localconfig_path(root)
            if lc and set_launch_options(lc, app_id, prof.launch_options):
                applied.append("launch options")
            if set_compat_tool(get_config_vdf_path(root), app_id, prof.compat_tool):
                applied.append("Proton")
        if prof.env_vars and write_gaming_env(prof.env_vars):
            applied.append("env vars")
        if prof.power_profile:
            ok, _ = set_power_profile(prof.power_profile)
            if ok:
                applied.append("power profile")
        msg = ("Applied " + ", ".join(applied) + " — quit Steam first.") if applied \
            else "Nothing applied (check permissions / Steam running)."
        self._actionResult.emit(msg)

    def _begin(self, msg: str) -> None:
        self._busy = True
        self._status = msg
        self.busyChanged.emit()
        self.statusChanged.emit()

    def _on_list(self, names: list) -> None:
        self._profiles = names
        self.profilesChanged.emit()

    def _on_action(self, msg: str) -> None:
        self._busy = False
        self._status = msg
        self.busyChanged.emit()
        self.statusChanged.emit()
        self.refresh()
