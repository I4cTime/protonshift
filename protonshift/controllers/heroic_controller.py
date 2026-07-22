"""QObject bridge for Heroic Games Launcher per-game config.

Driven by ``appId`` (set when a Heroic game is selected). Reads that game's
GamesConfig JSON, exposes the wine/proton toggles + version, writes changes back
(merge-preserving), and can launch the game through the ``heroic://`` URI. All
disk work is threaded.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ._worker import start_worker


class HeroicController(QObject):
    appIdChanged = Signal()
    configChanged = Signal()
    versionsChanged = Signal()
    loadingChanged = Signal()
    statusChanged = Signal()

    _loadResult = Signal(str, "QVariantMap", list)  # app_id, config, versions
    # M7 fix: toggle/version writes report back via queued signals so all
    # GUI-read state is mutated on the GUI thread and gated by app_id — the
    # workers no longer touch self._config/_status or emit notifies directly.
    _toggleResult = Signal(str, str, bool, bool)  # app_id, key, value, ok
    _versionResult = Signal(str, bool, str)  # app_id, ok, name
    _workError = Signal(str)  # unexpected worker exception -> clear + status

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._config: dict = {}
        self._versions: list[dict] = []
        self._loading = False
        self._status = ""
        self._loadResult.connect(self._on_loaded)
        self._toggleResult.connect(self._on_toggle)
        self._versionResult.connect(self._on_version)
        self._workError.connect(self._on_work_error)

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self._config = {}
        self._status = ""
        self.appIdChanged.emit()
        self.configChanged.emit()
        self.statusChanged.emit()
        if value:
            self._reload()

    @Property("QVariantMap", notify=configChanged)
    def config(self) -> dict:
        return self._config

    @Property("QVariantList", notify=versionsChanged)
    def wineVersions(self) -> list:  # noqa: N802
        return self._versions

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot(str, bool)
    def setToggle(self, key: str, value: bool) -> None:  # noqa: N802
        """Persist one boolean toggle (e.g. enableEsync) immediately."""
        if not self._app_id:
            return
        start_worker(
            self._toggle_work, self._app_id, key, value, on_error=self._workError.emit
        )

    @Slot(str, str, str)
    def setWineVersion(self, name: str, bin_path: str, wine_type: str) -> None:  # noqa: N802
        if not self._app_id:
            return
        start_worker(
            self._version_work, self._app_id, name, bin_path, wine_type,
            on_error=self._workError.emit,
        )

    @Slot()
    def launch(self) -> None:
        if not self._app_id:
            return
        from ..core.system_open import open_uri

        ok, msg = open_uri(f"heroic://launch/{self._app_id}")
        self._status = msg or ("Launching via Heroic…" if ok else "Couldn't launch.")
        self.statusChanged.emit()

    # --- workers --------------------------------------------------------------

    def _reload(self) -> None:
        self._loading = True
        self.loadingChanged.emit()
        start_worker(self._load_work, self._app_id, on_error=self._workError.emit)

    def _load_work(self, app_id: str) -> None:
        from ..core.heroic_config import get_heroic_game_config, list_heroic_wine_versions

        cfg = get_heroic_game_config(app_id)
        config = {
            "exists": cfg.exists,
            "winePrefix": cfg.wine_prefix,
            "wineName": cfg.wine_version.name,
            "wineType": cfg.wine_version.wine_type,
            "enableEsync": cfg.enable_esync,
            "enableFsync": cfg.enable_fsync,
            "autoInstallDxvk": cfg.auto_install_dxvk,
            "autoInstallVkd3d": cfg.auto_install_vkd3d,
            "showMangohud": cfg.show_mangohud,
            "useGameMode": cfg.use_game_mode,
            "nvidiaPrime": cfg.nvidia_prime,
            "otherOptions": cfg.other_options,
        }
        versions = [
            {"name": v.name, "bin": v.bin, "type": v.wine_type}
            for v in list_heroic_wine_versions()
        ]
        self._loadResult.emit(app_id, config, versions)

    def _toggle_work(self, app_id: str, key: str, value: bool) -> None:
        from ..core.heroic_config import set_heroic_toggles

        ok = set_heroic_toggles(app_id, **{_TOGGLE_ARG[key]: value}) if key in _TOGGLE_ARG else False
        self._toggleResult.emit(app_id, key, value, ok)

    def _version_work(self, app_id: str, name: str, bin_path: str, wine_type: str) -> None:
        from ..core.heroic_config import set_heroic_wine_version

        ok = set_heroic_wine_version(app_id, name, bin_path, wine_type)
        self._versionResult.emit(app_id, ok, name)

    # --- GUI-thread handlers ----------------------------------------------------

    def _on_loaded(self, app_id: str, config: dict, versions: list) -> None:
        if app_id != self._app_id:
            return
        self._config = config
        self._versions = versions
        self._loading = False
        self.configChanged.emit()
        self.versionsChanged.emit()
        self.loadingChanged.emit()

    def _on_toggle(self, app_id: str, key: str, value: bool, ok: bool) -> None:
        if app_id != self._app_id:
            return
        if ok:
            # optimistic local update; the next reload keeps it authoritative
            self._config[key] = value
            self.configChanged.emit()
        self._status = "Saved." if ok else "Couldn't save toggle."
        self.statusChanged.emit()

    def _on_version(self, app_id: str, ok: bool, name: str) -> None:
        if app_id != self._app_id:
            return
        self._status = f"Wine version set to {name}." if ok else "Couldn't set wine version."
        self.statusChanged.emit()
        if ok:
            self._reload()

    def _on_work_error(self, message: str) -> None:
        self._loading = False
        self._status = f"Unexpected error: {message}"
        self.loadingChanged.emit()
        self.statusChanged.emit()


# QML toggle key -> set_heroic_toggles keyword argument
_TOGGLE_ARG = {
    "enableEsync": "enable_esync",
    "enableFsync": "enable_fsync",
    "autoInstallDxvk": "auto_install_dxvk",
    "autoInstallVkd3d": "auto_install_vkd3d",
    "showMangohud": "show_mangohud",
    "useGameMode": "use_game_mode",
    "nvidiaPrime": "nvidia_prime",
}
