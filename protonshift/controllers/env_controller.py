"""QObject bridge for the environment variables editor.

Two data-loss bugs from the old React page are fixed here by construction:

* #21 (empty-save wipe): ``save()`` refuses unless the config actually loaded,
  so a failed read can never be followed by an empty write over the real file.
* #22 (error looks like empty): a read error sets ``loadError`` and leaves
  ``loaded == False``; a genuinely empty/missing file loads fine with no error.

The rows live in a QAbstractListModel so editing one cell updates just that row
(no full-list remount, so no focus loss — the old ScbKvEditor bug).

1.2.0 (#47): the rows can be saved to one of several *targets* — the
environment.d conf, a managed block in ``~/.profile`` or in ``~/.xsessionrc`` —
because environment.d never reaches a desktop that systemd didn't start. The
chosen target persists in ``~/.config/protonshift/settings.json`` (``envTarget``).
"""

from __future__ import annotations

import json
from pathlib import Path

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
from PySide6.QtGui import QGuiApplication

from ..core import env_targets
from ..core.env_vars import ENV_PRESETS, _valid_key
from ..core.fsutil import atomic_write_text
from ._worker import start_worker

_SETTINGS = Path.home() / ".config" / "protonshift" / "settings.json"
_SETTINGS_KEY = "envTarget"


def _load_target_choice() -> str:
    """The persisted target id, tolerant of a missing/garbled settings file."""
    try:
        data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        choice = data.get(_SETTINGS_KEY) if isinstance(data, dict) else None
    except (OSError, ValueError, TypeError):
        return env_targets.ENV_D
    return choice if choice in env_targets.ENV_TARGETS else env_targets.ENV_D


def _save_target_choice(target: str) -> None:
    try:
        existing = {}
        if _SETTINGS.exists():
            try:
                existing = json.loads(_SETTINGS.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                existing = {}
        if not isinstance(existing, dict):
            existing = {}
        existing[_SETTINGS_KEY] = target
        # atomic replace, same contract as theme_controller — a crash mid-write
        # can't corrupt settings.json.
        atomic_write_text(_SETTINGS, json.dumps(existing, indent=2))
    except OSError:
        pass


class EnvVarsModel(QAbstractListModel):
    KeyRole = Qt.UserRole + 1
    ValueRole = Qt.UserRole + 2

    modified = Signal()
    # Emitted when an edited key is not a valid env identifier. The edit still
    # sticks (the user may be mid-typing) — controllers surface it as status
    # and refuse to save while any key is invalid.
    invalidKey = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[list[str]] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        key, value = self._rows[index.row()]
        if role == self.KeyRole:
            return key
        if role == self.ValueRole:
            return value
        return None

    def roleNames(self):
        return {self.KeyRole: QByteArray(b"key"), self.ValueRole: QByteArray(b"value")}

    @Slot(int, str)
    def setKey(self, row: int, value: str) -> None:
        if 0 <= row < len(self._rows) and self._rows[row][0] != value:
            self._rows[row][0] = value
            self.dataChanged.emit(self.index(row), self.index(row), [self.KeyRole])
            self.modified.emit()
            if value and not _valid_key(value):
                self.invalidKey.emit(value)

    @Slot(int, str)
    def setValue(self, row: int, value: str) -> None:
        if 0 <= row < len(self._rows) and self._rows[row][1] != value:
            self._rows[row][1] = value
            self.dataChanged.emit(self.index(row), self.index(row), [self.ValueRole])
            self.modified.emit()

    @Slot()
    def addRow(self) -> None:
        n = len(self._rows)
        self.beginInsertRows(QModelIndex(), n, n)
        self._rows.append(["", ""])
        self.endInsertRows()
        self.modified.emit()

    # QML's ✕ button calls `model.removeRow(i)`. Never define a Python method
    # named `removeRow` here: QAbstractItemModel already exposes an invokable
    # C++ removeRow(int, parent) convenience, and QML dispatches to that
    # built-in — a same-named Python slot is unreachable from QML (#52: the
    # ✕ button was a silent no-op). The convenience delegates to the
    # *virtual* removeRows(), so that is the hook to override.
    def removeRows(self, row: int, count: int, parent: QModelIndex | None = None) -> bool:
        if (parent is not None and parent.isValid()) or count < 1 or row < 0 or row + count > len(self._rows):
            return False
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        del self._rows[row : row + count]
        self.endRemoveRows()
        self.modified.emit()
        return True

    def reset_rows(self, rows: list[tuple[str, str]]) -> None:
        self.beginResetModel()
        self._rows = [[k, v] for k, v in rows]
        self.endResetModel()

    def merge(self, items: dict[str, str]) -> None:
        """Update existing keys, append new ones - used by preset apply."""
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
    targetChanged = Signal()
    launchPrefixChanged = Signal()

    # worker -> GUI thread: (target, ok, error_message, rows, session_warning, recommended)
    _loadResult = Signal(str, bool, str, list, str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model = EnvVarsModel(self)
        self._model.modified.connect(self._mark_dirty)
        self._model.invalidKey.connect(self._on_invalid_key)
        self._loading = False
        self._loaded = False
        self._dirty = False
        self._load_error = ""
        self._session_warning = ""
        self._status = ""
        self._status_ok = True
        self._target = _load_target_choice()
        self._recommended = env_targets.ENV_D
        # last session probe, cached so a target switch can re-derive the
        # banner without shelling out again
        self._support = ""
        self._desktop = ""
        self._presets = list(ENV_PRESETS.keys())
        self._loadResult.connect(self._on_loaded)
        self.reload()

    # --- exposed state --------------------------------------------------------

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property("QStringList", constant=True)
    def presetNames(self) -> list:
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
    def loadError(self) -> str:
        return self._load_error

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=statusChanged)
    def statusOk(self) -> bool:
        return self._status_ok

    @Property(str, notify=loadedChanged)
    def sessionWarning(self) -> str:
        """Non-empty when the selected target isn't what this desktop reads (#47)."""
        return self._session_warning

    # --- targets (#47) --------------------------------------------------------

    @Property("QVariantList", constant=True)
    def targetNames(self) -> list:
        """``[{id, label, description, path, readBy}]`` in picker order."""
        return [
            {
                "id": t.id,
                "label": t.label,
                "description": t.description,
                "path": env_targets.display_path(t.path),
                "readBy": t.read_by,
            }
            for t in env_targets.targets()
        ]

    def _get_target(self) -> str:
        return self._target

    @Slot(str)
    def setTarget(self, target: str) -> None:
        """Switch where variables are saved; reloads the rows from that target."""
        if target not in env_targets.ENV_TARGETS or target == self._target:
            return
        self._target = target
        _save_target_choice(target)
        self.targetChanged.emit()
        # Re-derive the banner from the cached probe right away; the reload
        # will refresh it again from a fresh probe.
        self._session_warning = env_targets.target_warning(
            self._support, self._desktop, self._target, self._recommended
        )
        self.loadedChanged.emit()
        self.reload()

    target = Property(str, _get_target, setTarget, notify=targetChanged)

    @Property(str, notify=loadedChanged)
    def recommendedTarget(self) -> str:
        return self._recommended

    @Property(str, notify=targetChanged)
    def targetPath(self) -> str:
        return env_targets.display_path(env_targets.target_path(self._target))

    @Property(str, notify=launchPrefixChanged)
    def launchPrefix(self) -> str:
        """The current rows as ``KEY=value … %command%`` for Steam launch options."""
        return env_targets.as_launch_prefix(self._model.to_dict())

    @Slot()
    def copyLaunchPrefix(self) -> None:
        prefix = self.launchPrefix
        if not prefix:
            self._status = "Nothing to copy - add a variable first."
            self._status_ok = False
        else:
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(prefix)
            self._status = "Launch options copied - paste into a game's Properties → Launch Options."
            self._status_ok = True
        self.statusChanged.emit()

    # --- actions --------------------------------------------------------------

    @Slot()
    def reload(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()
        target = self._target
        start_worker(
            self._load_work,
            target,
            on_error=lambda m: self._loadResult.emit(target, False, m, [], "", ""),
        )

    @Slot(str)
    def applyPreset(self, name: str) -> None:
        items = ENV_PRESETS.get(name)
        if items:
            self._model.merge(items)

    @Slot()
    def save(self) -> None:
        # #21 fix: never write over a config we failed to (or never) read.
        if not self._loaded:
            self._status = "Not saved - config was never loaded."
            self._status_ok = False
            self.statusChanged.emit()
            return
        # L3 fix: the core writer silently drops keys failing its identifier
        # check — validate here so "Saved" never lies about a dropped key.
        cfg = self._model.to_dict()
        bad = next((k for k in cfg if not _valid_key(k)), None)
        if bad is not None:
            self._status = (
                f"Not saved - key “{bad}” is invalid "
                "(letters, digits, underscore; can't start with a digit)."
            )
            self._status_ok = False
            self.statusChanged.emit()
            return
        try:
            ok = env_targets.write_target(self._target, cfg)
        except Exception as exc:  # noqa: BLE001 — a raising core writer must not kill the slot
            ok = False
            self._status = f"Save failed: {type(exc).__name__}: {exc}"
        else:
            if ok:
                self._dirty = False
                self._status = f"Saved to {self.targetPath}"
                self.dirtyChanged.emit()
            else:
                self._status = "Save failed - check permissions."
        self._status_ok = ok
        self.statusChanged.emit()

    # --- internals ------------------------------------------------------------

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()
        if self._status:
            self._status = ""
            self.statusChanged.emit()
        self.launchPrefixChanged.emit()

    def _on_invalid_key(self, key: str) -> None:
        self._status = f"Key “{key}” is invalid - letters, digits, underscore only."
        self._status_ok = False
        self.statusChanged.emit()

    def _load_work(self, target: str) -> None:
        from ..core.session import UNKNOWN, current_desktop, session_env_support

        # #47: the session probe is advisory — it must never break the load.
        try:
            support = session_env_support()
            desktop = current_desktop()
        except Exception:  # noqa: BLE001 — the probe shells out; any surprise just means "no banner"
            support, desktop = UNKNOWN, ""
        # Plain strings written once per load; read on the GUI thread only
        # after this load's result has been delivered.
        self._support, self._desktop = support, desktop
        recommended = env_targets.recommended_target(support, desktop)
        warning = env_targets.target_warning(support, desktop, target, recommended)
        try:
            data = env_targets.read_target(target)  # {} for a missing file/block is legit
            self._loadResult.emit(target, True, "", sorted(data.items()), warning, recommended)
        except OSError as exc:
            self._loadResult.emit(target, False, str(exc), [], warning, recommended)

    def _on_loaded(
        self, target: str, ok: bool, error: str, rows: list, session_warning: str, recommended: str
    ) -> None:
        self._loading = False
        if target != self._target:
            # The target was switched while this load ran: these rows belong
            # to the old target — drop them and load the current one instead.
            self.loadingChanged.emit()
            self.reload()
            return
        self._session_warning = session_warning
        self._recommended = recommended or env_targets.ENV_D
        if ok:
            self._model.reset_rows(rows)
            self._loaded = True
            self._load_error = ""
            self._dirty = False
            self.dirtyChanged.emit()
        else:
            self._loaded = False
            self._load_error = error
        self._status = ""
        self.loadingChanged.emit()
        self.loadedChanged.emit()
        self.statusChanged.emit()
        self.launchPrefixChanged.emit()
