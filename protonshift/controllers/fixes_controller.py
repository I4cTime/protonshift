"""QObject bridge for the game-specific fixes database.

Surfaces built-in + user fixes for a game. Each fix carries a ready-made
``snippet`` (``KEY=value`` for env fixes, the raw value for launch args); the UI
applies it by appending to the launch-options editor, so the user reviews and
saves through the same fail-closed path as any hand-typed option.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Signal, Slot


class FixesController(QObject):
    appIdChanged = Signal()
    fixesChanged = Signal()
    statusChanged = Signal()

    _listResult = Signal(str, list)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = ""
        self._fixes: list[dict] = []
        self._status = ""
        self._listResult.connect(self._on_list)

    @Property(str, notify=appIdChanged)
    def appId(self) -> str:  # noqa: N802
        return self._app_id

    @appId.setter
    def appId(self, value: str) -> None:  # noqa: N802
        if value == self._app_id:
            return
        self._app_id = value
        self.appIdChanged.emit()
        if value:
            self.refresh()

    @Property("QVariantList", notify=fixesChanged)
    def fixes(self) -> list:
        return self._fixes

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Slot(str)
    def addUserFix(self, args_json: str) -> None:  # noqa: N802
        """Add a user fix from a JSON blob {title,description,type,key,value}."""
        import json

        from ..core.fixes import add_user_fix

        try:
            d = json.loads(args_json)
        except (ValueError, TypeError):
            self._status = "Invalid fix."
            self.statusChanged.emit()
            return
        ok = add_user_fix(
            self._app_id,
            d.get("title", ""),
            d.get("description", ""),
            d.get("type", "env"),
            d.get("key", ""),
            d.get("value", ""),
        )
        self._status = "Fix added." if ok else "Couldn't add fix."
        self.statusChanged.emit()
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        if not self._app_id:
            return
        threading.Thread(target=self._list_work, args=(self._app_id,), daemon=True).start()

    def _list_work(self, app_id: str) -> None:
        from ..core.fixes import get_fixes

        rows = []
        for f in get_fixes(app_id):
            snippet = f"{f.key}={f.value}" if f.fix_type == "env" and f.key else f.value
            rows.append({
                "title": f.title,
                "description": f.description,
                "source": f.source,
                "snippet": snippet,
            })
        self._listResult.emit(app_id, rows)

    def _on_list(self, app_id: str, rows: list) -> None:
        if app_id != self._app_id:
            return
        self._fixes = rows
        self.fixesChanged.emit()
