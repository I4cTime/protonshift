"""QObject bridge for ScopeBuddy named env-var snippets (envvars/<name>.conf).

These are reusable SCB_* / env snippets you keep by name and point ScopeBuddy at
per game. This manages the list plus a KV editor for the currently-selected
snippet, with the same merge-preserving save as the global editor.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.env_vars import _valid_key
from ..core.scopebuddy import SCB_KNOWN_KEYS
from ._worker import start_worker
from .env_controller import EnvVarsModel


class ScopeBuddyEnvvarsController(QObject):
    snippetsChanged = Signal()
    nameChanged = Signal()
    loadedChanged = Signal()
    dirtyChanged = Signal()
    existsChanged = Signal()
    statusChanged = Signal()

    _listResult = Signal(list)
    _loadResult = Signal(str, bool, bool, list)  # name, ok, exists, rows
    _workError = Signal(str)  # unexpected worker exception -> status

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._snippets: list[str] = []
        self._name = ""
        self._model = EnvVarsModel(self)
        self._model.modified.connect(self._mark_dirty)
        self._model.invalidKey.connect(self._on_invalid_key)
        self._loaded = False
        self._dirty = False
        self._exists = False
        self._status = ""
        self._known = list(SCB_KNOWN_KEYS)
        self._listResult.connect(self._on_list)
        self._loadResult.connect(self._on_loaded)
        self._workError.connect(self._on_work_error)
        self.refresh()

    # --- static ---------------------------------------------------------------

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property("QStringList", constant=True)
    def knownKeys(self) -> list:  # noqa: N802
        return self._known

    # --- reactive -------------------------------------------------------------

    @Property("QStringList", notify=snippetsChanged)
    def snippets(self) -> list:
        return self._snippets

    @Property(str, notify=nameChanged)
    def name(self) -> str:
        return self._name

    @Property(bool, notify=loadedChanged)
    def loaded(self) -> bool:
        return self._loaded

    @Property(bool, notify=existsChanged)
    def exists(self) -> bool:
        return self._exists

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        start_worker(self._list_work, on_error=self._workError.emit)

    @Slot(str)
    def select(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        self._name = name
        self._loaded = False
        self._dirty = False
        self.nameChanged.emit()
        self.dirtyChanged.emit()
        start_worker(self._load_work, name, on_error=self._workError.emit)

    @Slot(str)
    def create(self, name: str) -> None:
        """Start a new (empty) snippet under this name."""
        name = name.strip()
        if not name:
            return
        self._name = name
        self._model.reset_rows([])
        self._loaded = True
        self._exists = False
        self._dirty = False
        self._status = f"New snippet “{name}” — add keys and save."
        self.nameChanged.emit()
        self.loadedChanged.emit()
        self.existsChanged.emit()
        self.dirtyChanged.emit()
        self.statusChanged.emit()

    @Slot(str)
    def addKey(self, key: str) -> None:  # noqa: N802
        key = key.strip()
        if not key:
            return
        if not _valid_key(key):
            self._status = f"Key “{key}” is invalid — letters, digits, underscore only."
            self.statusChanged.emit()
            return
        if key not in self._model.to_dict():
            self._model.merge({key: ""})

    @Slot()
    def save(self) -> None:
        if not self._loaded or not self._name:
            return
        cfg = self._model.to_dict()
        bad = next((k for k in cfg if not _valid_key(k)), None)
        if bad is not None:
            self._status = f"Not saved — key “{bad}” is invalid."
            self.statusChanged.emit()
            return
        from ..core.scopebuddy import write_envvars

        try:
            ok = write_envvars(self._name, cfg)
        except (ValueError, OSError) as exc:
            ok = False
            self._status = f"Save failed: {exc}"
        else:
            if ok:
                self._dirty = False
                self._exists = True
                self._status = "Saved snippet"
                self.dirtyChanged.emit()
                self.existsChanged.emit()
                self.refresh()
            else:
                self._status = "Save failed — check permissions."
        self.statusChanged.emit()

    @Slot()
    def deleteSnippet(self) -> None:  # noqa: N802
        if not self._name:
            return
        from ..core.scopebuddy import delete_envvars

        if delete_envvars(self._name):
            self._model.reset_rows([])
            self._exists = False
            self._loaded = False
            self._dirty = False
            self._status = "Snippet removed"
            self.existsChanged.emit()
            self.loadedChanged.emit()
            self.dirtyChanged.emit()
            self.refresh()
        else:
            self._status = "Couldn't remove snippet."
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

    def _on_work_error(self, message: str) -> None:
        self._status = f"Unexpected error: {message}"
        self.statusChanged.emit()

    def _list_work(self) -> None:
        from ..core.scopebuddy import list_envvars

        self._listResult.emit([s["name"] for s in list_envvars()])

    def _load_work(self, name: str) -> None:
        from ..core.scopebuddy import read_envvars

        exists, cfg = read_envvars(name)
        self._loadResult.emit(name, True, exists, sorted(cfg.items()))

    def _on_list(self, names: list) -> None:
        self._snippets = names
        self.snippetsChanged.emit()

    def _on_loaded(self, name: str, ok: bool, exists: bool, rows: list) -> None:
        if name != self._name:
            return
        self._model.reset_rows(rows)
        self._exists = exists
        self._loaded = ok
        self._dirty = False
        self._status = ""
        self.existsChanged.emit()
        self.loadedChanged.emit()
        self.dirtyChanged.emit()
        self.statusChanged.emit()
