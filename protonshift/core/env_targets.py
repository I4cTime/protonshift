"""Where saved environment variables go, so they reach *this* desktop (#47).

``~/.config/environment.d`` is only read by the systemd user manager, so on a
desktop the display manager starts the classic way (Cinnamon on LightDM, XFCE,
MATE, ``startx`` …) the file is written and nothing ever reads it. This module
adds two more targets that those sessions *do* read, both as a managed block
inside a shell file the user may also own:

* ``~/.xsessionrc`` — sourced by the Debian/Ubuntu/Mint ``Xsession`` wrapper
  for every X11 session started from a display manager.
* ``~/.profile`` — sourced by login shells and by most display-manager session
  wrappers (GDM, LightDM, SDDM); the portable fallback.

The managed block is delimited by two marker comments and contains only
``export KEY='value'`` lines; everything outside the block is preserved
byte-for-byte. Values are single-quoted with POSIX escaping so a value can't
inject shell into a file that is sourced at every login.

Pure Python, no Qt — keep it that way so :mod:`tests` stay Qt-free.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import env_vars, session
from .env_vars import _valid_key
from .fsutil import atomic_write_text

ENV_D = "environment.d"
PROFILE = "profile"
XSESSIONRC = "xsessionrc"
ENV_TARGETS = (ENV_D, PROFILE, XSESSIONRC)

# Module globals so tests can monkeypatch them (never HOME).
PROFILE_PATH = Path.home() / ".profile"
XSESSIONRC_PATH = Path.home() / ".xsessionrc"

BLOCK_BEGIN = "# >>> protonshift env (managed - do not edit inside) >>>"
BLOCK_END = "# <<< protonshift env <<<"

# Characters that need no quoting in a Steam launch-options prefix.
_LAUNCH_SAFE_RE = re.compile(r"^[A-Za-z0-9_./:=+-]+$")
_EXPORT_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


@dataclass(frozen=True)
class EnvTarget:
    id: str
    label: str
    path: Path
    read_by: str
    description: str


def _env_d_path() -> Path:
    # Same file env_vars manages; computed lazily so a monkeypatched
    # ``env_vars.ENV_D_DIR`` is honoured and nothing is created just by asking.
    return env_vars.ENV_D_DIR / env_vars.GAMING_CONF


def targets() -> list[EnvTarget]:
    """All targets, in ``ENV_TARGETS`` order, with paths resolved now."""
    return [
        EnvTarget(
            ENV_D,
            "environment.d (systemd)",
            _env_d_path(),
            "systemd user sessions - GNOME, KDE Plasma, sway/Hyprland under uwsm",
            "A .conf file the systemd user manager reads at login. Desktops it doesn't "
            "start (Cinnamon on LightDM, XFCE, MATE, startx) never see it.",
        ),
        EnvTarget(
            PROFILE,
            "~/.profile",
            PROFILE_PATH,
            "login shells and most display-manager session wrappers",
            "A managed block of export lines in your login profile. The portable "
            "fallback when the session isn't started by systemd.",
        ),
        EnvTarget(
            XSESSIONRC,
            "~/.xsessionrc",
            XSESSIONRC_PATH,
            "X11 sessions started by LightDM/GDM on Debian, Ubuntu and Mint",
            "A managed block of export lines the Xsession wrapper sources for "
            "every X11 desktop session.",
        ),
    ]


def get_target(target_id: str) -> EnvTarget:
    for t in targets():
        if t.id == target_id:
            return t
    raise ValueError(f"Unknown env target: {target_id!r}")


def target_path(target_id: str) -> Path:
    return get_target(target_id).path


# --- managed shell block ------------------------------------------------------


def _quote(value: str) -> str:
    """POSIX single-quote ``value`` (``'`` becomes ``'\\''``)."""
    return "'" + value.replace("'", "'\\''") + "'"


def _unquote(value: str) -> str:
    """Invert ``_quote`` for a single-quoted value; tolerate bare/double-quoted."""
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("'\\''", "'")
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _find_block(lines: list[str]) -> tuple[int, int] | None:
    """Return ``(start, end)`` line indices of the managed block, inclusive.

    An unterminated block (begin marker, no end) runs to the end of the file —
    everything after the begin marker is ours by contract.
    """
    start: int | None = None
    for i, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if start is None:
            if stripped == BLOCK_BEGIN:
                start = i
        elif stripped == BLOCK_END:
            return start, i
    if start is not None:
        return start, len(lines) - 1
    return None


def _read_raw(path: Path) -> str:
    # newline="" keeps CRLF and friends intact so the rewrite is byte-exact
    # outside the block.
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
        return f.read()


def read_block(path: Path) -> dict[str, str]:
    """Variables in the managed block of ``path`` ({} when absent)."""
    try:
        raw = _read_raw(path)
    except FileNotFoundError:
        return {}
    lines = raw.splitlines(keepends=True)
    span = _find_block(lines)
    if span is None:
        return {}
    start, end = span
    result: dict[str, str] = {}
    for line in lines[start + 1 : end]:
        m = _EXPORT_RE.match(line.rstrip("\r\n"))
        if m:
            result[m.group(1)] = _unquote(m.group(2).strip())
    return result


def render_block(vars_dict: dict[str, str]) -> list[str]:
    """The managed block as lines (with newlines), keys sorted."""
    out = [BLOCK_BEGIN + "\n"]
    for k, v in sorted(vars_dict.items()):
        out.append(f"export {k}={_quote(str(v))}\n")
    out.append(BLOCK_END + "\n")
    return out


def write_block(path: Path, vars_dict: dict[str, str]) -> bool:
    """Replace (or add / remove) the managed block in ``path``.

    Everything outside the block is preserved byte-for-byte; the file is
    created when missing; an empty ``vars_dict`` removes the block entirely.
    Every key must satisfy ``env_vars._valid_key`` or ``ValueError`` is raised
    before a byte is written — these files are sourced by a shell at login.
    """
    for key in vars_dict:
        if not _valid_key(key):
            raise ValueError(f"Invalid environment variable name: {key!r}")

    try:
        raw = _read_raw(path)
    except FileNotFoundError:
        raw = ""
    except OSError:
        return False

    lines = raw.splitlines(keepends=True)
    span = _find_block(lines)

    if not vars_dict:
        if span is None:
            return True  # nothing to remove; don't create the file
        start, end = span
        new_lines = lines[:start] + lines[end + 1 :]
    elif span is None:
        new_lines = list(lines)
        if raw and not raw.endswith(("\n", "\r")):
            new_lines.append("\n")
        new_lines.extend(render_block(vars_dict))
    else:
        start, end = span
        new_lines = lines[:start] + render_block(vars_dict) + lines[end + 1 :]

    try:
        atomic_write_text(path, "".join(new_lines), newline="")
    except (OSError, UnicodeEncodeError):
        # UnicodeEncodeError: the file wasn't UTF-8 (surrogateescape on read);
        # refuse rather than rewrite the user's bytes lossily.
        return False
    return True


# --- recommendation -----------------------------------------------------------


def recommended_target(support: str, desktop: str = "") -> str:
    """Which target this session actually reads.

    * systemd-managed session → ``environment.d``
    * classic display-manager / no-systemd session → ``xsessionrc`` on X11,
      ``profile`` otherwise
    * unknown → ``environment.d`` (don't steer the user on a guess)
    """
    if support == session.SYSTEMD:
        return ENV_D
    if support in (session.NOT_SYSTEMD, session.NO_SYSTEMD):
        if os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "x11":
            return XSESSIONRC
        return PROFILE
    return ENV_D


def display_path(path: Path) -> str:
    """``~``-relative rendering for status text and captions."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def target_warning(support: str, desktop: str, selected: str, recommended: str) -> str:
    """Banner text when ``selected`` isn't what this desktop reads ('' otherwise)."""
    if support == session.UNKNOWN or selected == recommended:
        return ""
    try:
        sel = get_target(selected)
        rec = get_target(recommended)
    except ValueError:
        return ""
    who = f"Your {desktop} session" if desktop else "Your desktop session"
    if support == session.NO_SYSTEMD:
        why = "This system has no systemd, so ~/.config/environment.d is never read"
    elif support == session.NOT_SYSTEMD:
        why = f"{who} isn't started by systemd, so ~/.config/environment.d is never read"
    else:  # SYSTEMD session but a shell-file target selected
        why = f"{who} is started by systemd and may not source {display_path(sel.path)}"
    return (
        f"{why}. This desktop reads {display_path(rec.path)} ({rec.read_by}) - "
        f"variables saved to {display_path(sel.path)} may never reach your games. "
        f"Switch the target to {rec.label} to fix this."
    )


# --- dispatch -----------------------------------------------------------------


def read_target(target_id: str) -> dict[str, str]:
    if target_id == ENV_D:
        return env_vars.read_gaming_env()
    return read_block(target_path(target_id))


def write_target(target_id: str, vars_dict: dict[str, str]) -> bool:
    if target_id == ENV_D:
        for key in vars_dict:
            if not _valid_key(key):
                raise ValueError(f"Invalid environment variable name: {key!r}")
        return env_vars.write_gaming_env(vars_dict)
    return write_block(target_path(target_id), vars_dict)


# --- Steam launch options -----------------------------------------------------


def _launch_quote(value: str) -> str:
    if value and _LAUNCH_SAFE_RE.match(value):
        return value
    return _quote(value)


def as_launch_prefix(vars_dict: dict[str, str]) -> str:
    """``KEY=value KEY2='v 2' %command%`` for a Steam game's launch options.

    Invalid keys are skipped; an empty set yields ``''`` (nothing to paste).
    """
    parts = [f"{k}={_launch_quote(str(v))}" for k, v in vars_dict.items() if _valid_key(k)]
    if not parts:
        return ""
    return " ".join(parts) + " %command%"
