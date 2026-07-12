"""QObject bridge for Steam game discovery.

Discovery walks the disk (library folders + appmanifest ACFs), so it runs on a
worker thread and reports back via a queued signal — the UI shows a loading
state instead of freezing. Selection is tracked by ``app_id``, not list index,
so a refresh that re-sorts or drops a game can't leave the detail pane pointed
at the wrong title (the stale-snapshot bug from the old React app, review #L4).
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.steam import SteamGame, discover_games, invalidate_discovery_cache


def _to_dict(g: SteamGame) -> dict:
    return {
        "appId": g.app_id,
        "name": g.name,
        "installDir": g.install_dir,
        "lastPlayed": g.last_played,
        "hasPrefix": g.has_compatdata,
        "installPath": str(g.install_path) if g.install_path else "",
        "compatdataPath": str(g.compatdata_path) if g.compatdata_path else "",
        "libraryPath": str(g.library_path),
    }


class GamesController(QObject):
    gamesChanged = Signal()
    loadingChanged = Signal()
    selectedChanged = Signal()

    # emitted from the worker thread; delivered to _on_result on the GUI thread
    _resultReady = Signal(bool, list)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._games: list[dict] = []
        self._loading = False
        self._steam_found = False
        self._selected_app_id = ""
        self._resultReady.connect(self._on_result)
        self.refresh()

    # --- read-only state ------------------------------------------------------

    @Property("QVariantList", notify=gamesChanged)
    def games(self) -> list:
        return self._games

    @Property(int, notify=gamesChanged)
    def count(self) -> int:
        return len(self._games)

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=gamesChanged)
    def steamFound(self) -> bool:  # noqa: N802
        return self._steam_found

    @Property(str, notify=selectedChanged)
    def selectedAppId(self) -> str:  # noqa: N802
        return self._selected_app_id

    @Property("QVariantMap", notify=selectedChanged)
    def selected(self) -> dict:
        """The selected game, resolved live by app_id. Empty if it's gone."""
        for g in self._games:
            if g["appId"] == self._selected_app_id:
                return g
        return {}

    # --- actions --------------------------------------------------------------

    @Slot(str)
    def select(self, app_id: str) -> None:
        if app_id != self._selected_app_id:
            self._selected_app_id = app_id
            self.selectedChanged.emit()

    @Slot()
    def refresh(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()
        threading.Thread(target=self._work, daemon=True).start()

    # --- worker ---------------------------------------------------------------

    def _work(self) -> None:
        invalidate_discovery_cache()
        root, games = discover_games()
        self._resultReady.emit(root is not None, [_to_dict(g) for g in games])

    def _on_result(self, steam_found: bool, games: list) -> None:
        self._steam_found = steam_found
        self._games = games
        self._loading = False
        self.loadingChanged.emit()
        self.gamesChanged.emit()
        # selection resolves by id against the new list, so just re-notify
        self.selectedChanged.emit()
