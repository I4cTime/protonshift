"""Snapshots: the before and after of every change Diagnose makes, so Undo can put it back.

Before a one-click fix touches a game's launch options or compatibility tool, the
caller records a snapshot here; Undo reads the latest one, restores ``before``
and drops it. Snapshots live on disk (one JSON file per game under
``~/.config/protonshift/snapshots``) so Undo still works after a restart.

``record`` raising means the snapshot was not saved, and the caller must then
refuse to apply the fix: a change that cannot be undone is not one-click.

Security boundary: ``app_id`` becomes a file name. Steam app ids and non-Steam
shortcut ids are decimal, so only ``^[0-9]{1,20}$`` is accepted and the final
path is verified to stay inside the snapshot folder. Values read back are fed
to Steam's config by Undo, so entries carrying newlines or NULs are discarded
on read as well as refused on write.
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .fsutil import atomic_write_text
from .paths import PathValidationError, validate_within

MAX_PER_GAME = 20
FORMAT = "protonshift-snapshots"
VERSION = 1
LABEL_MAX = 200

_APP_ID_RE = re.compile(r"[0-9]{1,20}")
_BAD_CHARS = ("\n", "\r", "\x00")
# A full history is a few kilobytes; a file far past this is not ours.
_MAX_FILE_BYTES = 1 << 20


@dataclass(frozen=True)
class GameState:
    launch_options: str
    compat_tool: str  # "" means Steam's default


@dataclass(frozen=True)
class Snapshot:
    id: str
    taken_at: str
    app_id: str
    label: str
    finding_id: str
    before: GameState
    after: GameState


def snapshot_dir() -> Path:
    # Resolved per call, not at import, so tests can point HOME somewhere else.
    return Path.home() / ".config" / "protonshift" / "snapshots"


def _valid_app_id(app_id: object) -> bool:
    return isinstance(app_id, str) and _APP_ID_RE.fullmatch(app_id) is not None


def _snapshot_file(app_id: object) -> Path | None:
    """The game's snapshot file, or ``None`` when ``app_id`` is not a safe decimal id."""
    if not _valid_app_id(app_id):
        return None
    base = snapshot_dir()
    name = f"{app_id}.json"
    try:
        path = validate_within(base, base / name)
    except (PathValidationError, OSError, RuntimeError):
        return None
    # A symlink to another game's file would stay inside the folder yet mix two histories.
    return path if path.name == name else None


def _clean(value: object) -> bool:
    return isinstance(value, str) and not any(c in value for c in _BAD_CHARS)


def _state_to_dict(state: GameState) -> dict[str, str]:
    return {"launch_options": state.launch_options, "compat_tool": state.compat_tool}


def _state_from_dict(raw: object) -> GameState | None:
    if not isinstance(raw, dict):
        return None
    lo, ct = raw.get("launch_options"), raw.get("compat_tool")
    if not (_clean(lo) and _clean(ct)):
        return None
    return GameState(launch_options=lo, compat_tool=ct)


def _to_dict(s: Snapshot) -> dict[str, object]:
    return {
        "id": s.id,
        "taken_at": s.taken_at,
        "app_id": s.app_id,
        "label": s.label,
        "finding_id": s.finding_id,
        "before": _state_to_dict(s.before),
        "after": _state_to_dict(s.after),
    }


def _from_dict(raw: object, app_id: str) -> Snapshot | None:
    """One entry, or ``None`` when any part of it is missing, mistyped or unsafe."""
    if not isinstance(raw, dict):
        return None
    fields = {k: raw.get(k) for k in ("id", "taken_at", "app_id", "label", "finding_id")}
    if not all(_clean(v) for v in fields.values()):
        return None
    # An entry filed under another game's id must never be applied to this one.
    if fields["app_id"] != app_id or not fields["id"]:
        return None
    before, after = _state_from_dict(raw.get("before")), _state_from_dict(raw.get("after"))
    if before is None or after is None:
        return None
    return Snapshot(
        id=fields["id"],
        taken_at=fields["taken_at"],
        app_id=app_id,
        label=fields["label"][:LABEL_MAX],
        finding_id=fields["finding_id"],
        before=before,
        after=after,
    )


class _BadFile(Exception):
    """The snapshot file exists but is not a snapshot file we can read."""


def _load(path: Path, app_id: str) -> list[Snapshot]:
    """Entries oldest first. ``[]`` when there is no file; ``_BadFile`` when it's unusable."""
    try:
        if not path.exists():
            return []
        if path.stat().st_size > _MAX_FILE_BYTES:
            raise _BadFile
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _BadFile from exc
    if (
        not isinstance(data, dict)
        or data.get("format") != FORMAT
        or data.get("version") != VERSION
        or not isinstance(data.get("entries"), list)
    ):
        raise _BadFile
    out: list[Snapshot] = []
    for raw in data["entries"]:
        snap = _from_dict(raw, app_id)
        if snap is not None:
            out.append(snap)
    return out


def _save(path: Path, entries: list[Snapshot]) -> None:
    payload = {"format": FORMAT, "version": VERSION, "entries": [_to_dict(s) for s in entries]}
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _set_aside(path: Path) -> None:
    """Rename an unreadable file out of the way, keeping it for the user to inspect."""
    stamp = _now().strftime("%Y%m%dT%H%M%SZ")
    target = path.with_name(f"{path.name}.corrupt-{stamp}")
    if target.exists():
        target = path.with_name(f"{path.name}.corrupt-{stamp}-{secrets.token_hex(3)}")
    path.rename(target)


def record(app_id: str, label: str, finding_id: str, before: GameState, after: GameState) -> Snapshot:
    """Save a snapshot and return it. ValueError on bad input, OSError when it can't be written."""
    path = _snapshot_file(app_id)
    if path is None:
        raise ValueError(f"not a valid app id: {app_id!r}")
    for name, value in (
        ("label", label),
        ("finding_id", finding_id),
        ("before.launch_options", getattr(before, "launch_options", None)),
        ("before.compat_tool", getattr(before, "compat_tool", None)),
        ("after.launch_options", getattr(after, "launch_options", None)),
        ("after.compat_tool", getattr(after, "compat_tool", None)),
    ):
        if not isinstance(value, str):
            # ValueError, not TypeError: callers treat every refused input the same way.
            raise ValueError(f"{name} must be a string")  # noqa: TRY004
        if not _clean(value):
            raise ValueError(f"{name} must not contain a newline, carriage return or NUL")

    try:
        entries = _load(path, app_id)
    except _BadFile:
        # Refusing here would block every fix for this game, and overwriting would
        # lose whatever the file held, so it is kept beside the new one instead.
        _set_aside(path)
        entries = []

    now = _now()
    snap = Snapshot(
        id=f"{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}",
        taken_at=now.isoformat(),
        app_id=app_id,
        label=label[:LABEL_MAX],
        finding_id=finding_id,
        before=GameState(before.launch_options, before.compat_tool),
        after=GameState(after.launch_options, after.compat_tool),
    )
    entries.append(snap)
    _save(path, entries[-MAX_PER_GAME:])
    return snap


def history(app_id: str) -> list[Snapshot]:
    """The game's snapshots, newest first. ``[]`` for a bad id or an unreadable file."""
    path = _snapshot_file(app_id)
    if path is None:
        return []
    try:
        entries = _load(path, app_id)
    except _BadFile:
        return []
    # File order is recording order; timestamps tie within a second, so they don't decide.
    return list(reversed(entries))


def latest(app_id: str) -> Snapshot | None:
    entries = history(app_id)
    return entries[0] if entries else None


def drop(app_id: str, snapshot_id: str) -> bool:
    """Remove one snapshot (after its undo worked). False when there was nothing to remove."""
    path = _snapshot_file(app_id)
    if path is None or not isinstance(snapshot_id, str):
        return False
    try:
        entries = _load(path, app_id)
    except _BadFile:
        return False
    kept = [s for s in entries if s.id != snapshot_id]
    if len(kept) == len(entries):
        return False
    try:
        _save(path, kept)
    except OSError:
        return False
    return True
