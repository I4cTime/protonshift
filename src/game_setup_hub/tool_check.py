"""Unified tool detection with fallback paths for immutable distros.

On Bazzite, SteamOS, Fedora Atomic (Kinoite/Silverblue), NixOS, and
Flatpak-installed tools, binaries often live outside the default PATH
that shutil.which() searches.  This module provides a single
``find_tool()`` helper that first tries the normal PATH lookup, then
probes well-known fallback locations.
"""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path

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

    return None


def is_tool_available(name: str) -> bool:
    """Return True if *name* can be found anywhere on the system."""
    return find_tool(name) is not None
