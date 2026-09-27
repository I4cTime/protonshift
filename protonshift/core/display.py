"""Display outputs, modes, and resolution switching — cross-session.

Reads the connected monitors and their modes from whichever tool the session
provides, and applies a mode where the backend supports it:

* **X11**            → ``xrandr`` (list + apply)
* **Hyprland**       → ``hyprctl`` (list + apply; ships with the compositor,
  so it works where ``wlr-randr`` isn't installed)
* **wlroots Wayland** (Sway/…) → ``wlr-randr`` (list + apply)
* **KDE Wayland**    → ``kscreen-doctor`` (list + apply)

All tool calls go through :func:`core.host.host_run` so they work identically
inside a Flatpak sandbox (via ``flatpak-spawn --host``) and on the host. The
parse functions are pure (text in, dataclasses out) so they can be verified
without a display attached.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field

from .host import host_run
from .tool_check import find_tool


@dataclass
class DisplayMode:
    width: int
    height: int
    refresh: float  # Hz; 0.0 when unknown

    @property
    def label(self) -> str:
        r = f"@{self.refresh:g}Hz" if self.refresh else ""
        return f"{self.width}×{self.height}{r}"

    @property
    def key(self) -> str:  # stable id: "1920x1080@60.000"
        return f"{self.width}x{self.height}@{self.refresh:.3f}"


@dataclass
class DisplayOutput:
    name: str
    connected: bool = True
    enabled: bool = True
    primary: bool = False
    current: DisplayMode | None = None
    modes: list[DisplayMode] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Backend selection
# --------------------------------------------------------------------------- #

def _is_wayland() -> bool:
    return (os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland") or bool(
        os.environ.get("WAYLAND_DISPLAY")
    )


def _desktop() -> str:
    return (
        os.environ.get("XDG_CURRENT_DESKTOP", "")
        or os.environ.get("DESKTOP_SESSION", "")
    ).lower()


def _is_hyprland() -> bool:
    return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")) or "hyprland" in _desktop()


def detect_backend() -> str | None:
    """Return the display backend: ``xrandr`` | ``hyprctl`` | ``wlr-randr`` | ``kscreen-doctor``.

    Chooses by session type first, then by which tool is actually installed,
    falling back to xrandr under XWayland when nothing native is present.
    """
    wayland = _is_wayland()
    if wayland:
        if "kde" in _desktop() and find_tool("kscreen-doctor"):
            return "kscreen-doctor"
        if _is_hyprland() and find_tool("hyprctl"):
            return "hyprctl"
        if find_tool("wlr-randr"):
            return "wlr-randr"
        if find_tool("kscreen-doctor"):
            return "kscreen-doctor"
        # XWayland fallback — xrandr often still reports the virtual output.
        if find_tool("xrandr"):
            return "xrandr"
        return None
    if find_tool("xrandr"):
        return "xrandr"
    if find_tool("wlr-randr"):
        return "wlr-randr"
    return None


# --------------------------------------------------------------------------- #
# Pure parsers (text -> [DisplayOutput])
# --------------------------------------------------------------------------- #

_XRANDR_OUTPUT_RE = re.compile(
    r"^(?P<name>\S+)\s+(?P<state>connected|disconnected)"
    r"(?P<primary>\s+primary)?"
)
_XRANDR_MODE_RE = re.compile(
    r"^\s+(?P<w>\d+)x(?P<h>\d+)\s+(?P<rates>.+?)\s*$"
)
_XRANDR_RATE_RE = re.compile(r"(?P<rate>\d+\.\d+)(?P<flags>[*+ ]*)")


def parse_xrandr(text: str) -> list[DisplayOutput]:
    """Parse ``xrandr`` (no args) output."""
    outputs: list[DisplayOutput] = []
    current: DisplayOutput | None = None
    for line in text.splitlines():
        m = _XRANDR_OUTPUT_RE.match(line)
        if m and not line.startswith(" "):
            connected = m.group("state") == "connected"
            current = DisplayOutput(
                name=m.group("name"),
                connected=connected,
                enabled=connected,  # refined below if a mode is starred
                primary=bool(m.group("primary")),
            )
            outputs.append(current)
            continue
        if current is None:
            continue
        mm = _XRANDR_MODE_RE.match(line)
        if not mm:
            continue
        w, h = int(mm.group("w")), int(mm.group("h"))
        for rm in _XRANDR_RATE_RE.finditer(mm.group("rates")):
            rate = float(rm.group("rate"))
            mode = DisplayMode(w, h, rate)
            current.modes.append(mode)
            if "*" in rm.group("flags"):
                current.current = mode
                current.enabled = True
    return outputs


def parse_wlr_randr(text: str) -> list[DisplayOutput]:
    """Parse ``wlr-randr`` output.

    Format::

        DP-1 "Dell ..." (DP-1)
          Enabled: yes
          Modes:
            1920x1080 px, 60.000000 Hz (current)
    """
    outputs: list[DisplayOutput] = []
    current: DisplayOutput | None = None
    in_modes = False
    for raw in text.splitlines():
        if raw and not raw[0].isspace():
            name = raw.split()[0]
            current = DisplayOutput(name=name)
            outputs.append(current)
            in_modes = False
            continue
        if current is None:
            continue
        stripped = raw.strip()
        low = stripped.lower()
        if low.startswith("enabled:"):
            current.enabled = low.endswith("yes")
            continue
        if low.startswith("modes:"):
            in_modes = True
            continue
        if in_modes:
            mm = re.match(
                r"(?P<w>\d+)x(?P<h>\d+)\s*px,\s*(?P<r>[\d.]+)\s*Hz(?P<cur>.*)",
                stripped,
            )
            if mm:
                mode = DisplayMode(int(mm.group("w")), int(mm.group("h")), float(mm.group("r")))
                current.modes.append(mode)
                if "current" in mm.group("cur"):
                    current.current = mode
    for o in outputs:
        o.connected = True
    return outputs


def parse_kscreen(text: str) -> list[DisplayOutput]:
    """Parse ``kscreen-doctor --json`` output."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return []
    outputs: list[DisplayOutput] = []
    for o in data.get("outputs", []):
        name = o.get("name") or o.get("id", "?")
        connected = bool(o.get("connected", True))
        enabled = bool(o.get("enabled", connected))
        primary = bool(o.get("primary", False))
        modes = []
        by_id: dict = {}
        for m in o.get("modes", []):
            size = m.get("size", {})
            w, h = int(size.get("width", 0)), int(size.get("height", 0))
            r = float(m.get("refreshRate", 0.0))
            if w and h:
                mode = DisplayMode(w, h, r)
                modes.append(mode)
                by_id[m.get("id")] = mode
        cur = by_id.get(o.get("currentModeId"))
        outputs.append(
            DisplayOutput(
                name=name,
                connected=connected,
                enabled=enabled,
                primary=primary,
                current=cur,
                modes=modes,
            )
        )
    return outputs


_HYPR_MODE_RE = re.compile(r"^(?P<w>\d+)x(?P<h>\d+)@(?P<r>\d+(?:\.\d+)?)Hz$")


def parse_hyprctl(text: str) -> list[DisplayOutput]:
    """Parse ``hyprctl monitors -j`` output.

    Each monitor lists ``availableModes`` as ``"2560x1600@165.00Hz"`` strings and
    reports the active mode as ``width``/``height``/``refreshRate``. The active
    refresh rate is reported with more precision than the mode list (60.00200
    vs 60.00Hz), so the current mode is matched to the nearest listed rate.
    """
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    outputs: list[DisplayOutput] = []
    for o in data:
        if not isinstance(o, dict) or not o.get("name"):
            continue
        modes: list[DisplayMode] = []
        for raw in o.get("availableModes", []) or []:
            m = _HYPR_MODE_RE.match(str(raw).strip())
            if m:
                modes.append(DisplayMode(int(m.group("w")), int(m.group("h")), float(m.group("r"))))
        cur: DisplayMode | None = None
        try:
            cw, ch = int(o.get("width", 0)), int(o.get("height", 0))
            cr = float(o.get("refreshRate", 0.0))
        except (TypeError, ValueError):
            cw = ch = 0
            cr = 0.0
        if cw and ch:
            candidates = [m for m in modes if m.width == cw and m.height == ch]
            if candidates:
                cur = min(candidates, key=lambda m: abs(m.refresh - cr))
            else:
                cur = DisplayMode(cw, ch, cr)
                modes.append(cur)
        outputs.append(
            DisplayOutput(
                name=str(o["name"]),
                connected=True,
                enabled=not bool(o.get("disabled", False)),
                primary=bool(o.get("focused", False)),
                current=cur,
                modes=modes,
            )
        )
    return outputs


# --------------------------------------------------------------------------- #
# Dedup / ordering helper
# --------------------------------------------------------------------------- #

def _dedup_sorted(modes: list[DisplayMode]) -> list[DisplayMode]:
    """Collapse duplicate (w,h,rate) and sort largest-area / highest-rate first."""
    seen: dict[tuple[int, int, float], DisplayMode] = {}
    for m in modes:
        seen.setdefault((m.width, m.height, round(m.refresh, 3)), m)
    return sorted(
        seen.values(),
        key=lambda m: (m.width * m.height, m.refresh),
        reverse=True,
    )


# --------------------------------------------------------------------------- #
# Public read/apply API
# --------------------------------------------------------------------------- #

def list_outputs() -> tuple[str, list[DisplayOutput]]:
    """Return ``(backend, outputs)``; backend is ``""`` when none is available."""
    backend = detect_backend()
    if backend is None:
        return "", []
    argv, parser = {
        "xrandr": (["xrandr"], parse_xrandr),
        "hyprctl": (["hyprctl", "monitors", "-j"], parse_hyprctl),
        "wlr-randr": (["wlr-randr"], parse_wlr_randr),
        "kscreen-doctor": (["kscreen-doctor", "--json"], parse_kscreen),
    }[backend]
    try:
        r = host_run(argv, capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return backend, []
    if r.returncode != 0 or not r.stdout:
        return backend, []
    outputs = parser(r.stdout)
    for o in outputs:
        o.modes = _dedup_sorted(o.modes)
    return backend, outputs


def _kscreen_output_index(output: str) -> str | None:
    """kscreen-doctor addresses outputs by numeric id; map a name to its id."""
    try:
        r = host_run(["kscreen-doctor", "--json"], capture_output=True, text=True, timeout=5)
        data = json.loads(r.stdout)
    except (ValueError, OSError, subprocess.SubprocessError):
        return None
    for o in data.get("outputs", []):
        if o.get("name") == output:
            return str(o.get("id"))
    return None


def _hypr_position_scale(output: str) -> tuple[str, str]:
    """``("XxY", "scale")`` for a Hyprland monitor; ``("auto", "1")`` if unknown."""
    try:
        r = host_run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, timeout=5)
        data = json.loads(r.stdout)
    except (ValueError, OSError, subprocess.SubprocessError):
        return "auto", "1"
    for o in data if isinstance(data, list) else []:
        if isinstance(o, dict) and o.get("name") == output:
            pos = f"{int(o.get('x', 0))}x{int(o.get('y', 0))}"
            scale = f"{float(o.get('scale', 1.0)):g}"
            return pos, scale
    return "auto", "1"


def set_mode(output: str, width: int, height: int, refresh: float) -> tuple[bool, str]:
    """Apply ``width×height@refresh`` to ``output``. Returns ``(ok, message)``."""
    backend = detect_backend()
    if backend is None:
        return False, "No display tool available."

    if backend == "xrandr":
        argv = ["xrandr", "--output", output, "--mode", f"{width}x{height}"]
        if refresh:
            argv += ["--rate", f"{refresh:g}"]
    elif backend == "wlr-randr":
        mode = f"{width}x{height}"
        if refresh:
            mode += f"@{refresh:g}Hz"
        argv = ["wlr-randr", "--output", output, "--mode", mode]
    elif backend == "hyprctl":
        # `hyprctl keyword monitor NAME,WxH@R,XxY,SCALE` — keep the monitor's
        # current position and scale so only the mode changes.
        pos, scale = _hypr_position_scale(output)
        mode = f"{width}x{height}"
        if refresh:
            mode += f"@{refresh:g}"
        argv = ["hyprctl", "keyword", "monitor", f"{output},{mode},{pos},{scale}"]
    elif backend == "kscreen-doctor":
        oid = _kscreen_output_index(output)
        if oid is None:
            return False, f"Output {output} not found."
        target = f"output.{oid}.mode.{width}x{height}"
        if refresh:
            target += f"@{round(refresh)}"
        argv = ["kscreen-doctor", target]
    else:  # pragma: no cover — detect_backend only returns the four above
        return False, "Unsupported display backend."

    try:
        r = host_run(argv, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        return False, f"Couldn't run {backend}: {exc}"
    if r.returncode == 0:
        return True, f"Set {output} to {width}×{height}"
    return False, (r.stderr or r.stdout or "Failed").strip()
