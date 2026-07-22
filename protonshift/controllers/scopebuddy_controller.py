"""QObject bridge for the global ScopeBuddy scb.conf editor.

Manages the SCB_* keys; anything else in the file (comments, bash logic,
unrelated vars) is preserved by the core's line-merge write. Same safe RMW
contract as the other editors: read error distinguished from empty, save
refuses unless a load succeeded.

Availability probing (binary lookup, version read, SCB_AUTO_* capability
detection) shells out — inside a Flatpak that can mean multi-second
``flatpak-spawn`` round-trips — so it runs on the load worker, not in
``__init__`` (review M4). The formerly-constant properties now notify via
``infoChanged`` so QML picks the values up when the probe lands.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..core.env_vars import _valid_key
from ..core.scopebuddy import SCB_KNOWN_KEYS, SCOPEBUDDY_PRESETS
from ._worker import start_worker
from .env_controller import EnvVarsModel  # generic key/value list model


class ScopeBuddyController(QObject):
    infoChanged = Signal()
    loadingChanged = Signal()
    loadedChanged = Signal()
    dirtyChanged = Signal()
    statusChanged = Signal()

    _infoResult = Signal(bool, str, str, dict)  # available, binary, version, caps
    _loadResult = Signal(bool, str, list)  # ok, error, rows

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Filled asynchronously by the first _load_work (M4: no subprocess
        # calls on the GUI thread during construction).
        self._available = False
        self._binary = ""
        self._version = ""
        self._auto_caps: dict = {}
        self._model = EnvVarsModel(self)
        self._model.modified.connect(self._mark_dirty)
        self._model.invalidKey.connect(self._on_invalid_key)
        self._loading = False
        self._loaded = False
        self._dirty = False
        self._error = ""
        self._status = ""
        self._known = list(SCB_KNOWN_KEYS)
        self._presets = list(SCOPEBUDDY_PRESETS.keys())
        self._infoResult.connect(self._on_info)
        self._loadResult.connect(self._on_loaded)
        self.reload()

    # --- static ---------------------------------------------------------------

    @Property(bool, notify=infoChanged)
    def available(self) -> bool:
        return self._available

    @Property(str, notify=infoChanged)
    def binaryName(self) -> str:  # noqa: N802
        return self._binary

    @Property(str, notify=infoChanged)
    def version(self) -> str:
        return self._version

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property("QStringList", constant=True)
    def knownKeys(self) -> list:  # noqa: N802
        return self._known

    @Property("QStringList", constant=True)
    def presetNames(self) -> list:  # noqa: N802
        return self._presets

    @Property("QVariantMap", notify=infoChanged)
    def autoCaps(self) -> dict:  # noqa: N802
        """Which SCB_AUTO_* backends this session can actually drive."""
        return self._auto_caps

    # --- reactive -------------------------------------------------------------

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=loadedChanged)
    def loaded(self) -> bool:
        return self._loaded

    @Property(str, notify=loadedChanged)
    def loadError(self) -> str:  # noqa: N802
        return self._error

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    # --- actions --------------------------------------------------------------

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

    @Slot(str)
    def applyPreset(self, name: str) -> None:  # noqa: N802
        preset = SCOPEBUDDY_PRESETS.get(name)
        if preset:
            self._model.merge(dict(preset))

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

    @Slot()
    def save(self) -> None:
        if not self._loaded:
            self._status = "Not saved — config was never loaded."
            self.statusChanged.emit()
            return
        cfg = self._model.to_dict()
        # Pre-validate: the core writer raises ValueError on keys that aren't
        # valid shell identifiers — surface it here, before any write attempt.
        bad = next((k for k in cfg if not _valid_key(k)), None)
        if bad is not None:
            self._status = f"Not saved — key “{bad}” is invalid."
            self.statusChanged.emit()
            return
        from ..core.scopebuddy import write_global_config

        try:
            ok = write_global_config(cfg)
        except (ValueError, OSError) as exc:
            ok = False
            self._status = f"Save failed: {exc}"
        else:
            if ok:
                self._dirty = False
                self._status = "Saved to scb.conf"
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
        from ..core.scopebuddy import (
            SCOPEBUDDY_GLOBAL_CONF,
            detect_auto_capabilities,
            parse_scb_conf,
            scopebuddy_available_info,
        )

        # Availability + capability probes (may shell out) — worker thread only.
        info = scopebuddy_available_info()
        caps = detect_auto_capabilities()
        self._infoResult.emit(
            bool(info["available"]), str(info["binary"]), str(info["version"]), caps
        )

        path = SCOPEBUDDY_GLOBAL_CONF
        if path.exists():
            try:
                path.read_text(encoding="utf-8")  # probe readability
            except (OSError, UnicodeDecodeError) as exc:
                self._loadResult.emit(False, str(exc), [])
                return
        cfg = {k: v for k, v in parse_scb_conf(path).items() if k.startswith("SCB_")}
        self._loadResult.emit(True, "", sorted(cfg.items()))

    def _on_info(self, available: bool, binary: str, version: str, caps: dict) -> None:
        self._available = available
        self._binary = binary
        self._version = version
        self._auto_caps = dict(caps)
        self.infoChanged.emit()

    def _on_loaded(self, ok: bool, error: str, rows: list) -> None:
        if ok:
            self._model.reset_rows(rows)
            self._loaded = True
            self._error = ""
            self._dirty = False
            self.dirtyChanged.emit()
        else:
            self._loaded = False
            self._error = error
        self._loading = False
        self._status = ""
        self.loadingChanged.emit()
        self.loadedChanged.emit()
        self.statusChanged.emit()
