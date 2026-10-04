"""QObject bridge for the interface sounds: on/off, volume, sound set, playback.

Persists ``{enabled, volume, set}`` under the ``sounds`` key in
``~/.config/protonshift/settings.json`` (the same file the appearance lives
in) and plays the WAV files of the chosen set with Qt Multimedia's
``QSoundEffect``. QML calls ``sounds.play("click")`` from the Ps* components;
a build without Qt Multimedia simply reports ``available == False`` and every
play is a no-op.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from ..core import sounds as sounds_core
from ..core.fsutil import atomic_write_text

try:  # Qt Multimedia is an optional part of some Qt builds (and of some runtimes)
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover - depends on the installed Qt
    QSoundEffect = None

_SETTINGS = Path.home() / ".config" / "protonshift" / "settings.json"


class SoundController(QObject):
    changed = Signal()  # enabled / volume / soundSet
    # chime() may be called from a worker thread; this hops to the GUI thread
    _chime = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        stored = sounds_core.normalize(self._read_settings())
        self._enabled = stored["enabled"]
        self._volume = stored["volume"]
        self._set = stored["set"]
        # One QSoundEffect per (set, type), created the first time it is needed.
        self._effects: dict[tuple[str, str], QSoundEffect] = {}
        self._last_played: dict[str, float] = {}
        # A dragged volume slider changes the value many times a second; write
        # settings.json once the drag settles instead of on every step.
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self._save)
        self._chime.connect(self.result)
        if self.available and self._enabled:
            self._preload(self._set)

    # --- persistence ------------------------------------------------------

    @staticmethod
    def _read_settings() -> dict:
        try:
            data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        existing = self._read_settings()
        existing["sounds"] = {"enabled": self._enabled, "volume": self._volume, "set": self._set}
        try:
            atomic_write_text(_SETTINGS, json.dumps(existing, indent=2))
        except OSError:
            pass

    # --- playback -----------------------------------------------------------

    def _effect(self, set_id: str, sound_type: str) -> QSoundEffect | None:
        if QSoundEffect is None or sound_type not in sounds_core.SOUND_TYPES:
            return None
        key = (set_id, sound_type)
        effect = self._effects.get(key)
        if effect is None:
            path = sounds_core.sound_path(set_id, sound_type)
            if not path.is_file():
                return None
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(str(path)))
            self._effects[key] = effect
        return effect

    def _preload(self, set_id: str) -> None:
        for sound_type in sounds_core.SOUND_TYPES:
            self._effect(set_id, sound_type)

    def _play_from(self, set_id: str, sound_type: str) -> None:
        effect = self._effect(set_id, sound_type)
        if effect is None:
            return
        effect.setVolume(sounds_core.effective_volume(sound_type, self._volume))
        effect.play()

    # --- state --------------------------------------------------------------

    @Property(bool, constant=True)
    def available(self) -> bool:
        """False when this Qt build has no Qt Multimedia (sounds can't play)."""
        return QSoundEffect is not None

    @Property(bool, notify=changed)
    def enabled(self) -> bool:
        return self._enabled

    @Property(int, notify=changed)
    def volume(self) -> int:
        return self._volume

    @Property(str, notify=changed)
    def soundSet(self) -> str:
        return self._set

    @Property("QVariantList", constant=True)
    def sets(self) -> list:
        return sounds_core.SOUND_SETS

    # --- actions --------------------------------------------------------------

    @Slot(str)
    def play(self, sound_type: str) -> None:
        """Play one sound of the chosen set, if sounds are on."""
        if not self._enabled:
            return
        gap = sounds_core.THROTTLE_SECONDS.get(sound_type)
        if gap is not None:
            now = time.monotonic()
            if now - self._last_played.get(sound_type, 0.0) < gap:
                return
            self._last_played[sound_type] = now
        self._play_from(self._set, sound_type)

    def chime(self, ok: bool) -> None:
        """Thread-safe ``result``: controllers finish their work on worker
        threads, and a QSoundEffect must only be touched on the GUI thread."""
        self._chime.emit(ok)

    @Slot(bool)
    def result(self, ok: bool) -> None:
        """The chime for an action's outcome: a save, an install, a delete."""
        self.play("success" if ok else "error")

    @Slot(str)
    def preview(self, set_id: str) -> None:
        """Audition a set regardless of the on/off switch: a click, then the
        success chime - the two sounds heard most."""
        if set_id not in {entry["id"] for entry in sounds_core.SOUND_SETS}:
            return
        self._play_from(set_id, "click")
        QTimer.singleShot(260, lambda: self._play_from(set_id, "success"))

    @Slot(bool)
    def setEnabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self._save()
        self.changed.emit()
        if enabled:
            self.preview(self._set)  # hear what was just switched on

    @Slot(int)
    def setVolume(self, volume: int) -> None:
        volume = sounds_core.clamp_volume(volume)
        if volume == self._volume:
            return
        self._volume = volume
        self._save_timer.start()
        self.changed.emit()

    @Slot(str)
    def setSoundSet(self, set_id: str) -> None:
        if set_id == self._set or set_id not in {entry["id"] for entry in sounds_core.SOUND_SETS}:
            return
        self._set = set_id
        self._save()
        self.changed.emit()
        if self._enabled:
            self.preview(set_id)  # hear what was just picked
