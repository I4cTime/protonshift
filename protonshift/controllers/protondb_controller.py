"""QObject bridge for the per-game ProtonDB rating.

Bind ``appid`` to the selected Steam game; after a short debounce (so arrowing
through the library doesn't fire a request per row) the controller looks the
summary up on a worker thread - disk cache first, network only when the cache
is missing or older than a day - and reports back through queued signals. A
late result for a game the user has already left is discarded.

Privacy: a lookup sends the Steam app id to protondb.com, so it sits behind the
``protondbLookups`` setting in ``~/.config/protonshift/settings.json``. While
disabled the controller does nothing and exposes ``enabled == false`` so the
page can show an explicit opt-in.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from ..core import protondb
from ..core.fsutil import atomic_write_text
from ._worker import start_worker

_SETTINGS = Path.home() / ".config" / "protonshift" / "settings.json"
_SETTING_KEY = "protondbLookups"
_DEBOUNCE_MS = 250


class ProtonDbController(QObject):
    appidChanged = Signal()
    stateChanged = Signal()    # tier / counts / loading / error / fetchedLabel
    enabledChanged = Signal()

    # worker -> GUI thread
    _result = Signal(int, dict, bool)  # appid, summary dict, served-stale-because-unreachable
    _failure = Signal(int, str)  # appid, message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._appid = 0
        self._enabled = self._load_enabled()
        self._loading = False
        self._error = ""
        self._summary: dict = {}
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._on_debounce)
        self._result.connect(self._on_result)
        self._failure.connect(self._on_failure)

    # --- settings persistence (same idiom as theme_controller) ---------------

    @staticmethod
    def _read_settings() -> dict:
        try:
            data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _load_enabled(self) -> bool:
        value = self._read_settings().get(_SETTING_KEY, True)
        return value if isinstance(value, bool) else True

    def _save_enabled(self) -> None:
        existing = self._read_settings()
        existing[_SETTING_KEY] = self._enabled
        try:
            atomic_write_text(_SETTINGS, json.dumps(existing, indent=2))
        except OSError:
            pass

    # --- selection -----------------------------------------------------------

    @Property(int, notify=appidChanged)
    def appid(self) -> int:
        return self._appid

    @appid.setter
    def appid(self, value: int) -> None:
        value = int(value or 0)
        if value == self._appid:
            return
        self._appid = value
        self._debounce.stop()
        self._reset_state()
        self.appidChanged.emit()
        if value > 0 and self._enabled:
            self._debounce.start()

    # --- read-only state ------------------------------------------------------

    @Property(bool, notify=enabledChanged)
    def enabled(self) -> bool:
        return self._enabled

    @Property(bool, notify=stateChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=stateChanged)
    def loaded(self) -> bool:
        return bool(self._summary)

    @Property(str, notify=stateChanged)
    def error(self) -> str:
        return self._error

    @Property(str, notify=stateChanged)
    def tier(self) -> str:
        return self._summary.get("tier", "")

    @Property(str, notify=stateChanged)
    def tierLabel(self) -> str:
        return protondb.tier_label(self.tier) if self._summary else ""

    @Property(str, notify=stateChanged)
    def tierColorKey(self) -> str:
        return protondb.tier_color_key(self.tier)

    @Property(str, notify=stateChanged)
    def confidence(self) -> str:
        return self._summary.get("confidence", "")

    @Property(int, notify=stateChanged)
    def total(self) -> int:
        return int(self._summary.get("total", 0))

    @Property(str, notify=stateChanged)
    def trendingTier(self) -> str:
        return self._summary.get("trending_tier", "")

    @Property(str, notify=stateChanged)
    def trendingLabel(self) -> str:
        """Label for the trending tier, empty when it matches the overall tier."""
        trending = self.trendingTier
        if not trending or trending == self.tier:
            return ""
        return protondb.tier_label(trending)

    @Property(str, notify=stateChanged)
    def trendingColorKey(self) -> str:
        return protondb.tier_color_key(self.trendingTier)

    @Property(str, notify=stateChanged)
    def pageUrl(self) -> str:
        return protondb.PROTONDB_PAGE_URL.format(appid=self._appid) if self._appid > 0 else ""

    @Property(str, notify=stateChanged)
    def fetchedLabel(self) -> str:
        return protondb.age_label(float(self._summary.get("fetched_at", 0.0)))

    # --- actions --------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        """Bypass the cache and re-fetch for the current game."""
        self._debounce.stop()
        self._start(force=True)

    @Slot()
    def openPage(self) -> None:
        url = self.pageUrl
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot(bool)
    def setEnabled(self, value: bool) -> None:
        value = bool(value)
        if value == self._enabled:
            return
        self._enabled = value
        self._save_enabled()
        self.enabledChanged.emit()
        if value:
            if self._appid > 0:
                self._start(force=False)
        else:
            self._debounce.stop()
            self._reset_state()

    # --- internals ------------------------------------------------------------

    def _on_debounce(self) -> None:
        self._start(force=False)

    def _reset_state(self) -> None:
        self._summary = {}
        self._error = ""
        self._loading = False
        self.stateChanged.emit()

    def _start(self, *, force: bool) -> None:
        appid = self._appid
        if not self._enabled or appid <= 0 or self._loading:
            return
        self._loading = True
        self._error = ""
        self.stateChanged.emit()
        start_worker(self._work, appid, force, on_error=lambda m: self._failure.emit(appid, m))

    def _work(self, appid: int, force: bool) -> None:
        started = time.time()
        summary = protondb.lookup(appid, force=force)
        # lookup() swallows a network error when it has a cached copy to fall
        # back on. A copy older than this request, when we expected a fetch
        # (forced, or the copy is past its TTL), means ProtonDB wasn't reached.
        served_from_cache = summary.fetched_at < started
        unreachable = served_from_cache and (force or summary.is_stale)
        self._result.emit(appid, summary.to_dict(), unreachable)

    def _on_result(self, appid: int, data: dict, unreachable: bool) -> None:
        if appid != self._appid:
            return  # user moved on - discard the stale result
        self._summary = dict(data)
        self._error = "ProtonDB unreachable" if unreachable else ""
        self._loading = False
        self.stateChanged.emit()

    def _on_failure(self, appid: int, _message: str) -> None:
        if appid != self._appid:
            return
        self._loading = False
        # Keep whatever we last showed (may be a stale cache hit) and flag it.
        self._error = "ProtonDB unreachable"
        self.stateChanged.emit()
