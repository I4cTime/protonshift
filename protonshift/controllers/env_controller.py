"""QObject bridge for the environment.d editor.

Two data-loss bugs from the old React page are fixed here by construction:

* #21 (empty-save wipe): ``save()`` refuses unless the config actually loaded,
  so a failed read can never be followed by an empty write over the real file.
* #22 (error looks like empty): a read error sets ``loadError`` and leaves
  ``loaded == False``; a genuinely empty/missing file loads fine with no error.

The rows live in a QAbstractListModel so editing one cell updates just that row
(no full-list remount, so no focus loss — the old ScbKvEditor bug).
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)

from ..core.env_vars import ENV_PRESETS, _valid_key
from ._worker import start_worker


class EnvVarsModel(QAbstractListModel):
    KeyRole = Qt.UserRole + 1
    ValueRole = Qt.UserRole + 2

    modified = Signal()
    # Emitted when an edited key is not a valid env identifier. The edit still
    # sticks (the user may be mid-typing) — controllers surface it as status
    # and refuse to save while any key is invalid.
    invalidKey = Signal(str)  # noqa: N815 (QML-facing camelCase)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[list[str]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        key, value = self._rows[index.row()]
        if role == self.KeyRole:
            return key
        if role == self.ValueRole:
            return value
        return None

    def roleNames(self):  # noqa: N802
        return {self.KeyRole: QByteArray(b"key"), self.ValueRole: QByteArray(b"value")}

    @Slot(int, str)
    def setKey(self, row: int, value: str) -> None:  # noqa: N802
        if 0 <= row < len(self._rows) and self._rows[row][0] != value:
            self._rows[row][0] = value
            self.dataChanged.emit(self.index(row), self.index(row), [self.KeyRole])
            self.modified.emit()
            if value and not _valid_key(value):
                self.invalidKey.emit(value)

    @Slot(int, str)
    def setValue(self, row: int, value: str) -> None:  # noqa: N802
        if 0 <= row < len(self._rows) and self._rows[row][1] != value:
            self._rows[row][1] = value
            self.dataChanged.emit(self.index(row), self.index(row), [self.ValueRole])
            self.modified.emit()

    @Slot()
    def addRow(self) -> None:  # noqa: N802
        n = len(self._rows)
        self.beginInsertRows(QModelIndex(), n, n)
        self._rows.append(["", ""])
        self.endInsertRows()
        self.modified.emit()

    # Properly overrides the QAbstractItemModel::removeRow(int, QModelIndex)
    # virtual (compatible signature + bool return) instead of shadowing it with
    # an incompatible Slot. QML's existing `model.removeRow(i)` calls still
    # work — the extra parent argument defaults and the return is ignorable.
    @Slot(int, result=bool)
    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:  # noqa: N802
        if parent.isValid() or not (0 <= row < len(self._rows)):
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._rows[row]
        self.endRemoveRows()
        self.modified.emit()
        return True

    def reset_rows(self, rows: list[tuple[str, str]]) -> None:
        self.beginResetModel()
        self._rows = [[k, v] for k, v in rows]
        self.endResetModel()

    def merge(self, items: dict[str, str]) -> None:
        """Update existing keys, append new ones — used by preset apply."""
        index_by_key = {k: i for i, (k, _) in enumerate(self._rows)}
        for k, v in items.items():
            if k in index_by_key:
                self.setValue(index_by_key[k], v)
            else:
                n = len(self._rows)
                self.beginInsertRows(QModelIndex(), n, n)
                self._rows.append([k, v])
                self.endInsertRows()
        self.modified.emit()

    def to_dict(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, v in self._rows:
            k = k.strip()
            if k:
                out[k] = v
        return out


class EnvController(QObject):
    loadingChanged = Signal()
    loadedChanged = Signal()
    dirtyChanged = Signal()
    statusChanged = Signal()

    # worker -> GUI thread: (ok, error_message, rows)
    _loadResult = Signal(bool, str, list)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model = EnvVarsModel(self)
        self._model.modified.connect(self._mark_dirty)
        self._model.invalidKey.connect(self._on_invalid_key)
        self._loading = False
        self._loaded = False
        self._dirty = False
        self._load_error = ""
        self._status = ""
        self._presets = list(ENV_PRESETS.keys())
        self._loadResult.connect(self._on_loaded)
        self.reload()

    # --- exposed state --------------------------------------------------------

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property("QStringList", constant=True)
    def presetNames(self) -> list:  # noqa: N802
        return self._presets

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=loadedChanged)
    def loaded(self) -> bool:
        return self._loaded

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(str, notify=loadedChanged)
    def loadError(self) -> str:  # noqa: N802
        return self._load_error

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot()
    def reload(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()
        start_worker(
            self._load_work,
            on_error=lambda m: self._loadResult.emit(False, m, []),
        )

    @Slot(str)
    def applyPreset(self, name: str) -> None:  # noqa: N802
        items = ENV_PRESETS.get(name)
        if items:
            self._model.merge(items)

    @Slot()
    def save(self) -> None:
        # #21 fix: never write over a config we failed to (or never) read.
        if not self._loaded:
            self._status = "Not saved — config was never loaded."
            self.statusChanged.emit()
            return
        # L3 fix: the core writer silently drops keys failing its identifier
        # check — validate here so "Saved" never lies about a dropped key.
        cfg = self._model.to_dict()
        bad = next((k for k in cfg if not _valid_key(k)), None)
        if bad is not None:
            self._status = (
                f"Not saved — key “{bad}” is invalid "
                "(letters, digits, underscore; can't start with a digit)."
            )
            self.statusChanged.emit()
            return
        from ..core.env_vars import write_gaming_env

        try:
            ok = write_gaming_env(cfg)
        except Exception as exc:  # noqa: BLE001 — a raising core writer must not kill the slot
            ok = False
            self._status = f"Save failed: {type(exc).__name__}: {exc}"
        else:
            if ok:
                self._dirty = False
                self._status = "Saved to 70-protonshift.conf"
                self.dirtyChanged.emit()
            else:
                self._status = "Save failed — check permissions."
        self.statusChanged.emit()

    # --- internals ------------------------------------------------------------

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()
        if self._status:
            self._status = ""
            self.statusChanged.emit()

    def _on_invalid_key(self, key: str) -> None:
        self._status = f"Key “{key}” is invalid — letters, digits, underscore only."
        self.statusChanged.emit()

    def _load_work(self) -> None:
        from ..core.env_vars import get_gaming_conf_path, read_conf

        try:
            data = read_conf(get_gaming_conf_path())  # {} for a missing file is legit
            self._loadResult.emit(True, "", sorted(data.items()))
        except OSError as exc:
            self._loadResult.emit(False, str(exc), [])

    def _on_loaded(self, ok: bool, error: str, rows: list) -> None:
        if ok:
            self._model.reset_rows(rows)
            self._loaded = True
            self._load_error = ""
            self._dirty = False
            self.dirtyChanged.emit()
        else:
            self._loaded = False
            self._load_error = error
        self._loading = False
        self._status = ""
        self.loadingChanged.emit()
        self.loadedChanged.emit()
        self.statusChanged.emit()
