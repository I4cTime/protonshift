"""Does ~/.config/environment.d actually reach this desktop session?

``environment.d`` is read by the *systemd user manager* only. A desktop that
is started by that manager (GNOME, KDE Plasma, sway/Hyprland under uwsm, …)
inherits the variables, and so does every game launched from it. A desktop
started the classic way by a display manager (Cinnamon, XFCE, MATE, a bare
X11 ``startx`` session, …) never sees them — the file is written, nothing is
wrong with it, and MangoHud/Gamemode simply don't activate (#47).

``systemctl --user is-active graphical-session.target`` is the honest test:
the target is active exactly when the session is systemd-managed. Pure
Python, host-aware via :mod:`.host` so it works from inside the Flatpak.
"""

from __future__ import annotations

import os
import subprocess

from .host import host_run

# Classification of the running session, see ``session_env_support``.
SYSTEMD = "systemd"  # environment.d applies (after a re-login)
NOT_SYSTEMD = "not-systemd"  # systemd present, but the desktop isn't started by it
NO_SYSTEMD = "no-systemd"  # no systemctl at all (Void, Artix, …)
UNKNOWN = "unknown"  # couldn't tell — don't warn


def session_env_support() -> str:
    """Return one of SYSTEMD / NOT_SYSTEMD / NO_SYSTEMD / UNKNOWN."""
    try:
        cp = host_run(
            ["systemctl", "--user", "is-active", "graphical-session.target"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        return NO_SYSTEMD
    except (subprocess.TimeoutExpired, OSError):
        return UNKNOWN
    state = (cp.stdout or "").strip()
    if state == "active":
        return SYSTEMD
    if state in ("inactive", "failed", "activating", "deactivating"):
        return NOT_SYSTEMD
    # No usable answer on stdout: inside a Flatpak a missing host systemctl
    # surfaces as a non-zero exit with an empty stdout.
    if cp.returncode != 0 and not state:
        return NO_SYSTEMD
    return UNKNOWN


def current_desktop() -> str:
    """Human-friendly desktop name from XDG_CURRENT_DESKTOP ('' if unset)."""
    raw = os.environ.get("XDG_CURRENT_DESKTOP", "")
    first = raw.split(":", 1)[0].strip()
    return first.removeprefix("X-")


_ALTERNATIVES = (
    "Alternatives: put the same lines as `export KEY=value` in ~/.xsessionrc "
    "(X11 sessions on Debian/Ubuntu/Mint) or ~/.profile and log out and back in, "
    "or set them per game in Steam launch options: KEY=value %command%"
)


def env_d_warning(support: str, desktop: str = "") -> str:
    """Warning text for the Environment page, or '' when environment.d works."""
    if support == NOT_SYSTEMD:
        who = f"Your {desktop} session" if desktop else "Your desktop session"
        return (
            f"{who} isn't started by systemd, so variables saved here won't reach "
            f"games launched from the desktop. {_ALTERNATIVES}"
        )
    if support == NO_SYSTEMD:
        return (
            "This system has no systemd, so ~/.config/environment.d is never read and "
            f"variables saved here won't reach games. {_ALTERNATIVES}"
        )
    return ""
