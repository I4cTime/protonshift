"""QObject bridge for the per-game launch check.

``run`` gathers what the pure check needs (launch options, the chosen Proton
build, installed tools and runtimes) on a worker thread and reports the
findings back through a queued signal.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from ._worker import start_worker


class LaunchCheckController(QObject):
    changed = Signal()  # running / findings / summary / appId

    _result = Signal(str, list, str)  # app_id, findings, summary

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._running = False
        self._findings: list[dict] = []
        self._summary = ""
        self._result.connect(self._on_result)

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return self._running

    @Property("QVariantList", notify=changed)
    def findings(self) -> list:
        return self._findings

    @Property(str, notify=changed)
    def summary(self) -> str:
        return self._summary

    @Property(bool, notify=changed)
    def hasProblems(self) -> bool:
        return any(f["level"] in ("error", "warn") for f in self._findings)

    @Slot(str, str, str, str, str)
    def run(self, app_id: str, install_path: str, prefix_path: str,
            shortcut_options: str, protondb_tier: str) -> None:
        """Check one game. ``shortcut_options`` carries a Non-Steam shortcut's
        launch options (Steam keeps those in the shortcut, not in localconfig);
        pass ``"\\x00"`` for a store game so they are read from Steam."""
        self._app_id = app_id
        self._running = True
        self._findings = []
        self._summary = ""
        self.changed.emit()
        start_worker(
            self._work, app_id, install_path, prefix_path, shortcut_options, protondb_tier,
            on_error=lambda m: self._result.emit(app_id, [], f"The check failed: {m}"),
        )

    def _work(self, app_id: str, install_path: str, prefix_path: str,
              shortcut_options: str, protondb_tier: str) -> None:
        from ..core.compat_tool import get_config_vdf_path, read_compat_tool
        from ..core.launch_check import check_launch, summarize
        from ..core.steam import discover_games, get_available_proton_tools, get_localconfig_path
        from ..core.tool_check import is_tool_available
        from ..core.vdf_config import read_launch_options

        root, _games = discover_games()
        if shortcut_options == "\x00":
            config = get_localconfig_path(root) if root else None
            readable, options = read_launch_options(config, app_id) if config else (False, "")
        else:
            readable, options = True, shortcut_options
        ok, tool = read_compat_tool(get_config_vdf_path(root), app_id) if root else (False, "")
        # Tools (Proton builds, runtimes) are hidden from the game list, so
        # look for their manifests directly.
        installed: list[str] = []
        if root:
            from ..core.launch_check import ANTICHEAT_RUNTIMES
            from ..core.steam import _find_libraryfolders

            for lib in _find_libraryfolders(root):
                for runtime_id, _name in ANTICHEAT_RUNTIMES.values():
                    if (lib / "steamapps" / f"appmanifest_{runtime_id}.acf").exists():
                        installed.append(runtime_id)
        findings = check_launch(
            launch_options=options,
            launch_options_readable=readable,
            compat_tool=tool if ok else "",
            available_tools=get_available_proton_tools(root),
            install_path=Path(install_path) if install_path else None,
            prefix_path=Path(prefix_path) if prefix_path else None,
            installed_app_ids=installed,
            tool_exists=is_tool_available,
            protondb_tier=protondb_tier,
        )
        self._result.emit(app_id, findings, summarize(findings))

    def _on_result(self, app_id: str, findings: list, summary: str) -> None:
        if app_id != self._app_id:
            return  # the user moved on to another game
        self._running = False
        self._findings = findings
        self._summary = summary
        self.changed.emit()
