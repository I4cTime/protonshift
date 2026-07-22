"""QObject bridge for Steam game discovery.

Discovery walks the disk (library folders + appmanifest ACFs), so it runs on a
worker thread and reports back via a queued signal — the UI shows a loading
state instead of freezing. Selection is tracked by ``app_id``, not list index,
so a refresh that re-sorts or drops a game can't leave the detail pane pointed
at the wrong title (the stale-snapshot bug from the old React app, review #L4).
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.steam import SteamGame, discover_games, invalidate_discovery_cache
from ._worker import start_worker


def _to_dict(g: SteamGame) -> dict:
    return {
        "appId": g.app_id,
        "name": g.name,
        "source": "steam",
        "store": "steam",
        "installDir": g.install_dir,
        "lastPlayed": g.last_played,
        "hasPrefix": g.has_compatdata,
        "installPath": str(g.install_path) if g.install_path else "",
        "compatdataPath": str(g.compatdata_path) if g.compatdata_path else "",
        "libraryPath": str(g.library_path),
    }


def _heroic_to_dict(g) -> dict:
    prefix = str(g.prefix_path) if g.prefix_path else ""
    return {
        "appId": g.app_id,
        "name": g.name,
        "source": "heroic",
        "store": g.store,  # "epic" | "gog"
        "installDir": "",
        "lastPlayed": 0,
        "hasPrefix": bool(prefix),
        "installPath": str(g.install_path) if g.install_path else "",
        "compatdataPath": prefix,
        "libraryPath": "",
    }


def _lutris_to_dict(g) -> dict:
    prefix = str(g.prefix_path) if g.prefix_path else ""
    return {
        "appId": g.app_id,
        "name": g.name,
        "source": "lutris",
        "store": "lutris",
        "installDir": "",
        "lastPlayed": 0,
        "hasPrefix": bool(prefix),
        "installPath": str(g.install_path) if g.install_path else "",
        "compatdataPath": prefix,
        "libraryPath": "",
    }


class GamesController(QObject):
    gamesChanged = Signal()
    loadingChanged = Signal()
    selectedChanged = Signal()

    # emitted from the worker thread; delivered to _on_result on the GUI thread
    _resultReady = Signal(bool, list)
    _workError = Signal(str)  # unexpected worker exception -> clear loading

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._games: list[dict] = []
        self._loading = False
        self._steam_found = False
        self._selected_app_id = ""
        self._resultReady.connect(self._on_result)
        self._workError.connect(self._on_work_error)
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

    @Property("QVariantMap", notify=gamesChanged)
    def sourceCounts(self) -> dict:  # noqa: N802
        """Per-source game counts for the library filter (steam/heroic/lutris)."""
        counts: dict[str, int] = {"steam": 0, "heroic": 0, "lutris": 0}
        for g in self._games:
            counts[g.get("source", "steam")] = counts.get(g.get("source", "steam"), 0) + 1
        return counts

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
        start_worker(self._work, on_error=self._workError.emit)

    # --- worker ---------------------------------------------------------------

    def _work(self) -> None:
        from ..core.heroic import discover_heroic_games
        from ..core.lutris import discover_lutris_games

        invalidate_discovery_cache()
        root, games = discover_games()
        merged = [_to_dict(g) for g in games]
        # Heroic (Epic/GOG) and Lutris games sit alongside Steam ones, tagged by
        # source so the UI can filter and gate Steam-only actions.
        try:
            merged += [_heroic_to_dict(g) for g in discover_heroic_games()]
        except Exception:  # noqa: BLE001 — a broken Heroic install must not kill discovery
            pass
        try:
            merged += [_lutris_to_dict(g) for g in discover_lutris_games()]
        except Exception:  # noqa: BLE001
            pass
        self._resultReady.emit(root is not None, merged)

    def _on_result(self, steam_found: bool, games: list) -> None:
        self._steam_found = steam_found
        self._games = games
        self._loading = False
        self.loadingChanged.emit()
        self.gamesChanged.emit()
        # selection resolves by id against the new list, so just re-notify
        self.selectedChanged.emit()

    def _on_work_error(self, _message: str) -> None:
        # Keep the previous game list; just stop the spinner so the UI
        # (and any retry) isn't wedged behind a dead worker.
        self._loading = False
        self.loadingChanged.emit()
