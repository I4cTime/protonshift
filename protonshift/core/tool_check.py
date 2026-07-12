"""Unified tool detection with fallback paths for immutable distros.

On Bazzite, SteamOS, Fedora Atomic (Kinoite/Silverblue), NixOS, and
Flatpak-installed tools, binaries often live outside the default PATH
that shutil.which() searches.  This module provides a single
``find_tool()`` helper that first tries the normal PATH lookup, then
probes well-known fallback locations.

Lifted verbatim from the original ProtonShift Python core — no web layer,
no changes.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path


def _in_flatpak() -> bool:
    """True when running inside a Flatpak sandbox."""
    return os.path.exists("/.flatpak-info") or "FLATPAK_ID" in os.environ


def _host_which(name: str) -> str | None:
    """Look a binary up on the HOST from inside a sandbox via flatpak-spawn.

    ``shutil.which`` only sees the sandbox filesystem, so host-installed tools
    (gamescope, mangohud, protontricks live on the host, not in our runtime)
    read as missing. Needs the ``org.freedesktop.Flatpak`` talk-name (granted in
    the manifest). ``name`` is always an internal constant, never user input.
    """
    if not _in_flatpak():
        return None
    try:
        result = subprocess.run(
            ["flatpak-spawn", "--host", "sh", "-c", f"command -v {shlex.quote(name)}"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if result.returncode == 0:
        line = result.stdout.strip().splitlines()
        return line[0] if line and line[0].startswith("/") else None
    return None

_EXTRA_BIN_DIRS: tuple[str, ...] = (
    "/usr/bin",
    "/usr/local/bin",
    "/usr/games",
    "/var/usrlocal/bin",
    # Flatpak host extensions / SDK merge dirs
    "/usr/lib/extensions/vulkan/MangoHud/bin",
    "/usr/lib64/extensions/vulkan/MangoHud/bin",
    # NixOS profile links
    os.path.expanduser("~/.nix-profile/bin"),
    "/run/current-system/sw/bin",
    # Homebrew / Linuxbrew
    "/home/linuxbrew/.linuxbrew/bin",
)

_TOOL_SPECIFIC_PATHS: dict[str, tuple[str, ...]] = {
    "gamescope": (
        "/usr/bin/gamescope",
        "/usr/local/bin/gamescope",
        "/usr/lib/extensions/gamescope/bin/gamescope",
    ),
    "mangohud": (
        "/usr/bin/mangohud",
        "/usr/local/bin/mangohud",
        "/usr/lib/extensions/vulkan/MangoHud/bin/mangohud",
        "/usr/lib64/extensions/vulkan/MangoHud/bin/mangohud",
    ),
    "gamemoderun": (
        "/usr/bin/gamemoderun",
        "/usr/local/bin/gamemoderun",
        "/usr/lib/extensions/gamemode/bin/gamemoderun",
    ),
    "protontricks": (
        "/usr/bin/protontricks",
        "/usr/local/bin/protontricks",
        os.path.expanduser("~/.local/bin/protontricks"),
    ),
    "xrandr": (
        "/usr/bin/xrandr",
        "/usr/local/bin/xrandr",
    ),
    "wlr-randr": (
        "/usr/bin/wlr-randr",
        "/usr/local/bin/wlr-randr",
    ),
    "scopebuddy": (
        "/usr/bin/scopebuddy",
        "/usr/local/bin/scopebuddy",
        os.path.expanduser("~/.local/bin/scopebuddy"),
    ),
    "scb": (
        "/usr/bin/scb",
        "/usr/local/bin/scb",
        os.path.expanduser("~/.local/bin/scb"),
    ),
}


@lru_cache(maxsize=32)
def find_tool(name: str) -> str | None:
    """Locate a tool binary, returning the absolute path or ``None``.

    1. ``shutil.which(name)`` — uses the current process PATH.
    2. ``shutil.which(name, path=...)`` — searches extra bin directories
       common on immutable/atomic distros.
    3. Direct file existence checks for tool-specific known paths.
    """
    found = shutil.which(name)
    if found:
        return found

    extra_path = os.pathsep.join(_EXTRA_BIN_DIRS)
    found = shutil.which(name, path=extra_path)
    if found:
        return found

    for candidate in _TOOL_SPECIFIC_PATHS.get(name, ()):
        p = Path(candidate)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)

    # Last resort: ask the host (only does anything inside a Flatpak sandbox).
    return _host_which(name)


def is_tool_available(name: str) -> bool:
    """Return True if *name* can be found anywhere on the system."""
    return find_tool(name) is not None


def find_scopebuddy() -> tuple[str, str] | None:
    """Return ``(invoke_name, absolute_path)`` for ScopeBuddy.

    Prefers the short ``scb`` binary when present, else ``scopebuddy``.
    """
    scb = find_tool("scb")
    if scb:
        return ("scb", scb)
    scopebuddy = find_tool("scopebuddy")
    if scopebuddy:
        return ("scopebuddy", scopebuddy)
    return None


def is_scopebuddy_available() -> bool:
    """Return True if ``scb`` or ``scopebuddy`` is on the system."""
    return find_scopebuddy() is not None
