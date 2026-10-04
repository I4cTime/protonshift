"""Proton's per-game debug log.

With ``PROTON_LOG=1`` in a game's launch options, Proton writes
``steam-<appid>.log`` into ``$PROTON_LOG_DIR`` (the home folder by default)
each time the game runs. This module finds that file and reads its tail; the
log of a crashing game can reach hundreds of megabytes, so it is never read
whole.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_APP_ID_RE = re.compile(r"^\d+$")
LOG_SWITCH = "PROTON_LOG=1"

# Lines that usually explain a failed launch.
_PROBLEM_RE = re.compile(
    r"(\berr:|\bfixme:.*(?:unimplemented|not supported)|Unhandled exception|Unhandled page fault"
    r"|wine: Call from|Assertion|Traceback|\bfatal\b|\bcrash|failed to|cannot open|could not load"
    r"|No such file|Permission denied|vk\w*: .*fail|ERROR)",
    re.IGNORECASE,
)


@dataclass
class LogTail:
    text: str
    total_bytes: int
    truncated: bool   # only the end of the file is shown
    problem_count: int


def log_dir() -> Path:
    custom = os.environ.get("PROTON_LOG_DIR", "").strip()
    return Path(custom).expanduser() if custom else Path.home()


def log_path(app_id: str) -> Path | None:
    """Where Proton writes this game's log, or None for a non-Steam id."""
    if not _APP_ID_RE.match(app_id or ""):
        return None
    return log_dir() / f"steam-{app_id}.log"


def logging_enabled(launch_options: str) -> bool:
    """True when the launch options switch Proton logging on."""
    return bool(re.search(r"(?<![\w])PROTON_LOG=(?!0\b)\S+", launch_options or ""))


def is_problem_line(line: str) -> bool:
    return bool(_PROBLEM_RE.search(line))


def read_tail(path: Path, max_bytes: int = 256 * 1024, max_lines: int = 800,
              problems_only: bool = False) -> LogTail:
    """The end of a log: at most ``max_bytes`` / ``max_lines``. Raises OSError."""
    total = path.stat().st_size
    with open(path, "rb") as f:
        if total > max_bytes:
            f.seek(total - max_bytes)
        data = f.read(max_bytes)
    lines = data.decode("utf-8", errors="replace").splitlines()
    truncated = total > max_bytes
    if truncated and lines:
        lines = lines[1:]  # the first line was cut mid-way by the seek
    problems = [line for line in lines if is_problem_line(line)]
    shown = problems if problems_only else lines
    if len(shown) > max_lines:
        shown = shown[-max_lines:]
        truncated = True
    return LogTail(text="\n".join(shown), total_bytes=total, truncated=truncated,
                   problem_count=len(problems))


def modified_label(path: Path) -> str:
    """e.g. ``2026-10-04 01:23`` (local time); empty when unreadable."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).astimezone().strftime("%Y-%m-%d %H:%M")
    except OSError:
        return ""
