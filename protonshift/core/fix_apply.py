"""Apply a Diagnose fix to a game's Steam settings, and undo it.

:func:`plan` is pure: it works out, from a finding's actions and the game's
current settings, what the settings would become, without touching anything.
The dialog shows that before and after to the user, and only then calls
:func:`apply_change` with the very same plan.

The disk part keeps three promises:

- It never writes over something the user did not see. The settings are read
  again right before writing, and a plan made from older settings is refused.
- It never makes a change that cannot be undone. The snapshot is saved first;
  if that fails, nothing is written.
- It never leaves half a change behind. When the second of two writes fails,
  the first is put back.

Paths are passed in, never looked up here, so tests run against VDF files in a
temporary folder.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import snapshots
from .compat_tool import read_compat_tool, set_compat_tool
from .fix_pack import (
    _ENV_VALUE_RE,
    _FORBIDDEN_PREFIX,
    _FORBIDDEN_VARS,
    _GAME_ARG_RE,
    _KEY_RE,
    _WORD_RE,
    Action,
)
from .launch_merge import (
    COMMAND,
    add_command,
    add_game_arg,
    merge_launch_snippet,
    remove_word,
    set_env,
    single_command,
    unset_env,
)
from .snapshots import GameState, Snapshot
from .vdf_config import read_launch_options, set_launch_options

_BAD_CHARS = ("\n", "\r", "\x00")

_VALUE_REFUSED = (
    "The value has characters ProtonShift will not write into launch options for you, "
    "so add it by hand if you want it."
)
_KEY_REFUSED = "{key} is not a variable name ProtonShift can set, so add it by hand if you want it."
_LOADER_REFUSED = (
    "{key} decides what code the game loads, so ProtonShift will not change it for you. "
    "Add it by hand if you are sure."
)
_UNKNOWN_ACTION = "ProtonShift does not know how to make this change for you."
_LINE_BREAK = "The new launch options would contain a line break, which Steam cannot store."
_STATE_MOVED = "The settings changed since the check. Run Diagnose again."
_UNREADABLE = "Steam's settings for this game could not be read, so nothing was changed."


@dataclass(frozen=True)
class Change:
    before: GameState
    after: GameState
    manual: tuple[str, ...]  # instructions from manual actions, in order
    blocked: str  # "" or a plain reason why this cannot be applied automatically

    @property
    def changed(self) -> bool:
        return self.after != self.before


@dataclass(frozen=True)
class ApplyResult:
    ok: bool
    message: str  # plain sentence for the user
    snapshot_id: str  # "" when nothing was recorded
    state: GameState | None  # the state now on disk, when known


# --------------------------------------------------------------------------- #
# planning
# --------------------------------------------------------------------------- #

def _key_problem(key: str) -> str:
    if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
        return _KEY_REFUSED.format(key=key or "The name")
    # The pack loader already refuses these; a user's own fix is not loaded
    # through it, and one click should not be able to set them either way.
    if key in _FORBIDDEN_VARS or key.startswith(_FORBIDDEN_PREFIX):
        return _LOADER_REFUSED.format(key=key)
    return ""


def _user_snippet(text: str, value: str) -> str:
    # The contract: a user's launch_arg with %command% is merged like any
    # snippet; without it, it is game arguments (merge_launch_snippet alone
    # would put it in front of the game).
    snippet = value if COMMAND in value else f"{COMMAND} {value}"
    return merge_launch_snippet(text, snippet)


def _step(action: Action, text: str) -> tuple[str, str]:
    """``(new_text, refusal)`` for one launch-options action."""
    kind = action.type
    if kind in ("env", "unset_env"):
        problem = _key_problem(action.key)
        if problem:
            return text, problem
        if kind == "unset_env":
            return unset_env(text, action.key), ""
        value = action.value
        if not isinstance(value, str) or not _ENV_VALUE_RE.fullmatch(value) or COMMAND in value:
            return text, _VALUE_REFUSED
        return set_env(text, action.key, value), ""
    if kind == "game_arg":
        if not isinstance(action.value, str) or not _GAME_ARG_RE.fullmatch(action.value):
            return text, _VALUE_REFUSED
        return add_game_arg(text, action.value), ""
    if kind == "remove_word":
        if not isinstance(action.value, str) or not _WORD_RE.fullmatch(action.value):
            return text, _VALUE_REFUSED
        return remove_word(text, action.value), ""
    simple: dict[str, Callable[[str], str]] = {"single_command": single_command, "add_command": add_command}
    if kind in simple:
        return simple[kind](text), ""
    if kind == "user_snippet":
        if not isinstance(action.value, str) or not action.value.strip():
            return text, _VALUE_REFUSED
        return _user_snippet(text, action.value.strip()), ""
    return text, _UNKNOWN_ACTION


def plan(actions: Sequence[Action], state: GameState) -> Change:
    """What ``actions`` would do to ``state``. Pure: nothing is read or written.

    Actions apply in order. A blocked plan changes nothing (``after`` is
    ``before``), but still lists every manual instruction so the user can
    follow them by hand.
    """
    text, tool = state.launch_options, state.compat_tool
    manual: list[str] = []
    blocked = ""
    for action in actions:
        if action.type == "manual":
            manual.append(action.text)
            continue
        if blocked:
            continue
        if action.type == "default_proton":
            tool = ""
            continue
        # Splitting would quietly turn a bare line break into a space; the user
        # should see the value refused rather than changed.
        if any(ch in str(action.value) + str(action.key) for ch in _BAD_CHARS):
            blocked = _LINE_BREAK
            continue
        text, blocked = _step(action, text)
    if not blocked and any(ch in text or ch in tool for ch in _BAD_CHARS):
        blocked = _LINE_BREAK
    after = state if blocked else GameState(launch_options=text, compat_tool=tool)
    return Change(before=state, after=after, manual=tuple(manual), blocked=blocked)


# --------------------------------------------------------------------------- #
# disk
# --------------------------------------------------------------------------- #

def read_state(localconfig: Path | None, config_vdf: Path | None, app_id: str) -> GameState | None:
    """The game's launch options and Proton build as Steam has them, or None.

    None when either file is missing or cannot be parsed. A missing file is
    refused too: writing would create a new one in a place Steam may not read,
    and the user would see a fix that did nothing.
    """
    if localconfig is None or config_vdf is None:
        return None
    try:
        if not localconfig.is_file() or not config_vdf.is_file():
            return None
        ok_lo, options = read_launch_options(localconfig, app_id)
        ok_ct, tool = read_compat_tool(config_vdf, app_id)
    except Exception:  # noqa: BLE001 - an unreadable config is an answer, not a crash
        return None
    if not (ok_lo and ok_ct and isinstance(options, str) and isinstance(tool, str)):
        return None
    return GameState(launch_options=options, compat_tool=tool)


def _safe(write: Callable[[], bool]) -> bool:
    try:
        return bool(write())
    except Exception:  # noqa: BLE001 - a write that raised did not happen as far as the caller knows
        return False


def _shown(text: str) -> str:
    return f'"{text}"' if text else "empty"


def _write(
    localconfig: Path,
    config_vdf: Path,
    app_id: str,
    current: GameState,
    target: GameState,
    *,
    unchanged: str,
) -> str:
    """Move the files from ``current`` to ``target``. ``""`` on success, else a sentence for the user.

    ``unchanged`` finishes the sentence when nothing ended up changed
    ("nothing was changed", "the fix is still in place").
    """
    write_lo = target.launch_options != current.launch_options
    write_ct = target.compat_tool != current.compat_tool
    if write_lo and not _safe(lambda: set_launch_options(localconfig, app_id, target.launch_options)):
        return f"Steam's launch options could not be written, so {unchanged}."
    if write_ct and not _safe(lambda: set_compat_tool(config_vdf, app_id, target.compat_tool)):
        if not write_lo:
            return f"Steam's Proton setting could not be written, so {unchanged}."
        if _safe(lambda: set_launch_options(localconfig, app_id, current.launch_options)):
            return ("Steam's Proton setting could not be written, so the launch options were put back "
                    f"as they were and {unchanged}.")
        return ("Steam's Proton setting could not be written, and the launch options could not be put "
                f"back either. They are now {_shown(target.launch_options)}; they were "
                f"{_shown(current.launch_options)}.")
    return ""


def apply_change(
    localconfig: Path | None,
    config_vdf: Path | None,
    app_id: str,
    change: Change,
    *,
    label: str,
    finding_id: str,
) -> ApplyResult:
    """Write ``change.after`` to Steam's files, after saving a snapshot to undo it."""
    if change.blocked:
        return ApplyResult(False, change.blocked, "", None)
    if not change.changed:
        return ApplyResult(False, "This fix would not change anything.", "", None)
    current = read_state(localconfig, config_vdf, app_id)
    if current is None or localconfig is None or config_vdf is None:
        return ApplyResult(False, _UNREADABLE, "", None)
    if current != change.before:
        return ApplyResult(False, _STATE_MOVED, "", current)
    try:
        snap = snapshots.record(app_id, label, finding_id, change.before, change.after)
    except (OSError, ValueError):
        return ApplyResult(
            False, "ProtonShift could not save a way to undo this fix, so nothing was changed.", "", current,
        )

    failure = _write(localconfig, config_vdf, app_id, current, change.after, unchanged="nothing was changed")
    if failure:
        snapshots.drop(app_id, snap.id)
        return ApplyResult(False, failure, "", read_state(localconfig, config_vdf, app_id))

    now = read_state(localconfig, config_vdf, app_id)
    if now != change.after:
        # The undo point stays: whatever did land can still be put back with Undo.
        return ApplyResult(
            False,
            "The fix was written, but Steam's files do not show it now. Close Steam and run Diagnose again.",
            snap.id, now,
        )
    return ApplyResult(True, "The fix was applied. You can undo it from Diagnose.", snap.id, now)


def undo_latest(
    localconfig: Path | None,
    config_vdf: Path | None,
    app_id: str,
    *,
    force: bool = False,
) -> ApplyResult:
    """Put back the settings from before the latest fix, then forget that fix.

    When the settings were changed after the fix was applied, Undo would
    overwrite those changes, so it refuses unless ``force`` is set. The
    result's ``snapshot_id`` is the snapshot Undo acted on; it is dropped only
    when the settings are back as they were before the fix.
    """
    snap = snapshots.latest(app_id)
    if snap is None:
        return ApplyResult(False, "There is no fix to undo for this game.", "", None)
    current = read_state(localconfig, config_vdf, app_id)
    if current is None or localconfig is None or config_vdf is None:
        return ApplyResult(False, _UNREADABLE, snap.id, None)
    if current == snap.before:
        snapshots.drop(app_id, snap.id)
        return ApplyResult(
            True, "The settings were already back to how they were before the fix.", snap.id, current,
        )
    if current != snap.after and not force:
        message = (
            "The settings were changed after the fix was applied, so Undo would overwrite those changes. "
            f"The launch options are now {_shown(current.launch_options)}; before the fix they were "
            f"{_shown(snap.before.launch_options)}."
        )
        if current.compat_tool != snap.before.compat_tool:
            message += (f" The Proton build is now {_shown(current.compat_tool)}; before the fix it was "
                        f"{_shown(snap.before.compat_tool)}.")
        return ApplyResult(False, message, snap.id, current)

    failure = _write(
        localconfig, config_vdf, app_id, current, snap.before, unchanged="the fix is still in place",
    )
    if failure:
        return ApplyResult(False, failure, snap.id, read_state(localconfig, config_vdf, app_id))
    now = read_state(localconfig, config_vdf, app_id)
    if now != snap.before:
        return ApplyResult(
            False,
            "The old settings were written, but Steam's files do not show them now. "
            "Close Steam and try Undo again.",
            snap.id, now,
        )
    snapshots.drop(app_id, snap.id)
    return ApplyResult(True, "The fix was undone.", snap.id, now)


def undo_available(app_id: str) -> Snapshot | None:
    """The fix Undo would take back, or None when there is none."""
    return snapshots.latest(app_id)
