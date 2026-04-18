"""Display/monitor detection and management."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass

from game_setup_hub.tool_check import find_tool


@dataclass
class MonitorInfo:
    name: str
    connected: bool
    resolution: str
    refresh_rate: str
    primary: bool
    position: str


def get_session_type() -> str:
    """Detect whether running X11 or Wayland."""
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session in ("x11", "wayland"):
        return session
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def _parse_xrandr() -> list[MonitorInfo]:
    """Parse xrandr output for connected monitors."""
    xrandr = find_tool("xrandr")
    if not xrandr:
        return []
    try:
        result = subprocess.run(
            [xrandr, "--current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    monitors: list[MonitorInfo] = []
    current_monitor: str | None = None

    for line in result.stdout.splitlines():
        # Match connected output line: "HDMI-1 connected primary 1920x1080+0+0 ..."
        match = re.match(
            r"^(\S+)\s+(connected|disconnected)\s*(primary)?\s*(\d+x\d+\+\d+\+\d+)?",
            line,
        )
        if match:
            name = match.group(1)
            connected = match.group(2) == "connected"
            primary = match.group(3) == "primary"
            geometry = match.group(4) or ""

            resolution = ""
            position = ""
            if geometry:
                parts = geometry.split("+")
                resolution = parts[0]
                if len(parts) >= 3:
                    position = f"+{parts[1]}+{parts[2]}"

            current_monitor = name
            monitors.append(MonitorInfo(
                name=name,
                connected=connected,
                resolution=resolution,
                refresh_rate="",
                primary=primary,
                position=position,
            ))
            continue

        # Match current mode line (has asterisk): "   1920x1080     60.00*+  ..."
        if current_monitor and line.strip() and "*" in line:
            rate_match = re.search(r"(\d+\.\d+)\*", line)
            if rate_match and monitors:
                monitors[-1].refresh_rate = rate_match.group(1)
                current_monitor = None

    return [m for m in monitors if m.connected]


def _parse_wlr_randr() -> list[MonitorInfo]:
    """Parse wlr-randr output for Wayland monitors."""
    wlr_randr = find_tool("wlr-randr")
    if not wlr_randr:
        return []
    try:
        result = subprocess.run(
            [wlr_randr],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    monitors: list[MonitorInfo] = []
    current: dict | None = None

    for line in result.stdout.splitlines():
        # Output name line (not indented)
        if not line.startswith(" ") and not line.startswith("\t") and line.strip():
            if current:
                monitors.append(MonitorInfo(**current))
            name = line.split()[0]
            current = {
                "name": name,
                "connected": True,
                "resolution": "",
                "refresh_rate": "",
                "primary": False,
                "position": "",
            }
        elif current:
            stripped = line.strip()
            # "current" mode line
            if "current" in stripped.lower():
                mode_match = re.search(r"(\d+x\d+)", stripped)
                rate_match = re.search(r"@ ([\d.]+)", stripped)
                if mode_match:
                    current["resolution"] = mode_match.group(1)
                if rate_match:
                    current["refresh_rate"] = rate_match.group(1)
            if "Position:" in stripped:
                pos_match = re.search(r"Position:\s*(\S+)", stripped)
                if pos_match:
                    current["position"] = pos_match.group(1)

    if current:
        monitors.append(MonitorInfo(**current))

    return monitors


def get_monitors() -> list[MonitorInfo]:
    """Get connected monitors regardless of session type."""
    session = get_session_type()
    if session == "wayland":
        monitors = _parse_wlr_randr()
        if monitors:
            return monitors
    monitors = _parse_xrandr()
    return monitors


# Output names emitted by xrandr/wlr-randr are short identifiers like
# ``HDMI-1`` or ``DP-2``. Anything outside this shape is rejected before
# ever reaching the xrandr command line so an attacker who can call the
# /display/resolution endpoint cannot inject extra args.
_MONITOR_NAME_RE = re.compile(r"^[A-Za-z0-9._\-]{1,32}$")
_MAX_DIMENSION = 16384  # 16k — comfortably above any real display


def set_resolution(monitor: str, width: int, height: int, refresh: float = 0) -> bool:
    """Set resolution for a monitor using xrandr. Returns True on success."""
    if not _MONITOR_NAME_RE.match(monitor):
        return False
    # Whitelist against actually-detected monitors. Even if the regex is wrong
    # this stops xrandr being driven against a name that isn't on the system.
    known_names = {m.name for m in get_monitors()}
    if known_names and monitor not in known_names:
        return False
    if not (0 < width <= _MAX_DIMENSION and 0 < height <= _MAX_DIMENSION):
        return False
    if not (0 <= refresh <= 1000):
        return False

    xrandr = find_tool("xrandr")
    if not xrandr:
        return False
    cmd = [xrandr, "--output", monitor, "--mode", f"{width}x{height}"]
    if refresh > 0:
        cmd.extend(["--rate", f"{refresh:g}"])
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
