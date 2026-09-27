"""QObject bridge for configuration profiles.

A profile is a named snapshot of a game's launch options + compat tool plus the
system-wide gaming env vars and power profile. Capturing and applying both touch
several config files / tools, so they run on worker threads.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from ._worker import start_worker


def _local_path(url: QUrl):
    """QML FileDialog hands back a file:// QUrl; None when it isn't local."""
    from pathlib import Path

    if not isinstance(url, QUrl) or url.isEmpty():
        return None
    local = url.toLocalFile() if url.isLocalFile() else url.toString()
    if not local:
        return None
    return Path(local).expanduser()


class ProfilesController(QObject):
    appIdChanged = Signal()
    profilesChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()

    _listResult = Signal(list)
    _actionResult = Signal(str)
    _workError = Signal(str)  # unexpected worker exception (list path — no refresh loop)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._profiles: list[str] = []
        self._status = ""
        self._busy = False
        self._listResult.connect(self._on_list)
        self._actionResult.connect(self._on_action)
        self._workError.connect(self._on_work_error)
        self.refresh()

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:
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
        start_worker(self._list_work, on_error=self._workError.emit)

    @Slot(str)
    def saveCurrent(self, name: str) -> None:
        name = name.strip()
        if self._busy or not name or not self._app_id:
            return
        self._begin(f"Capturing “{name}”…")
        start_worker(
            self._save_work, name, self._app_id,
            on_error=lambda m: self._actionResult.emit(f"Capture failed: {m}"),
        )

    @Slot(str)
    def apply(self, name: str) -> None:
        if self._busy or not name or not self._app_id:
            return
        self._begin(f"Applying “{name}”…")
        start_worker(
            self._apply_work, name, self._app_id,
            on_error=lambda m: self._actionResult.emit(f"Apply failed: {m}"),
        )

    @Slot(QUrl)
    def exportAll(self, dest: QUrl) -> None:
        """Write every saved profile to a bundle file picked in the UI."""
        self._export(list(self._profiles), dest)

    @Slot(str, QUrl)
    def exportOne(self, name: str, dest: QUrl) -> None:
        self._export([name], dest)

    @Slot(QUrl, bool)
    def importFrom(self, src: QUrl, overwrite: bool) -> None:
        """Import profiles from a bundle file; existing names are kept unless ``overwrite``."""
        path = _local_path(src)
        if self._busy or path is None:
            return
        self._begin("Importing profiles…")
        start_worker(
            self._import_work, path, overwrite,
            on_error=lambda m: self._actionResult.emit(f"Import failed: {m}"),
        )

    @Slot(str)
    def deleteProfile(self, name: str) -> None:
        from ..core.profiles_storage import delete_profile

        ok = delete_profile(name)
        self._status = f"Deleted “{name}”." if ok else "Couldn't delete profile."
        self.statusChanged.emit()
        self.refresh()

    def _export(self, names: list[str], dest: QUrl) -> None:
        path = _local_path(dest)
        if self._busy or path is None or not names:
            return
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        self._begin("Exporting…")
        start_worker(
            self._export_work, names, path,
            on_error=lambda m: self._actionResult.emit(f"Export failed: {m}"),
        )

    # --- workers --------------------------------------------------------------

    def _export_work(self, names: list[str], path) -> None:
        from ..core.profiles_storage import export_profiles

        n = export_profiles(names, path)
        noun = "profile" if n == 1 else "profiles"
        self._actionResult.emit(f"Exported {n} {noun} to {path.name}.")

    def _import_work(self, path, overwrite: bool) -> None:
        from ..core.profiles_storage import BundleError, import_profiles

        try:
            result = import_profiles(path, overwrite=overwrite)
        except BundleError as exc:
            self._actionResult.emit(f"Couldn't import: {exc}")
            return
        self._actionResult.emit(result.summary)

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
            # M6 fix: a failed read must fail the capture, not silently store
            # "" — applying such a profile would blank the user's launch
            # options and clear their Proton pin.
            lc = get_localconfig_path(root)
            if lc:
                ok, launch_opts = read_launch_options(lc, app_id)
                if not ok:
                    self._actionResult.emit(
                        "Couldn't capture — localconfig.vdf unreadable; profile not saved."
                    )
                    return
            ok, compat = read_compat_tool(get_config_vdf_path(root), app_id)
            if not ok:
                self._actionResult.emit(
                    "Couldn't capture — config.vdf unreadable; profile not saved."
                )
                return
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
            # M6 fix: skip empty fields instead of applying them. Legacy
            # profiles captured before the failed-read guard may hold "" as a
            # failed-capture sentinel; an empty compat tool would otherwise
            # *delete* the game's Proton pin and empty launch options would
            # blank the user's options. (A deliberate "clear my Proton pin"
            # is done in the Launch editor, not via profiles.)
            lc = get_localconfig_path(root)
            if prof.launch_options and lc and set_launch_options(lc, app_id, prof.launch_options):
                applied.append("launch options")
            if prof.compat_tool and set_compat_tool(
                get_config_vdf_path(root), app_id, prof.compat_tool
            ):
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

    def _on_work_error(self, message: str) -> None:
        # List-worker failure: clear busy and surface status, but do NOT
        # refresh — that would retry the failing worker in a loop.
        self._busy = False
        self._status = f"Unexpected error: {message}"
        self.busyChanged.emit()
        self.statusChanged.emit()
