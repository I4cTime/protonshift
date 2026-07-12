"""Run host commands from inside (or outside) a Flatpak sandbox.

Tools like nvidia-smi, powerprofilesctl, gamescope, protontricks live on the
*host*, not in our runtime. Inside a Flatpak they must be invoked via
``flatpak-spawn --host`` (granted by the manifest's org.freedesktop.Flatpak
talk-name); outside a sandbox this is a transparent pass-through.

``host_run`` deliberately does NOT swallow ``FileNotFoundError``: outside a
sandbox a missing tool raises it (callers catch it as before); inside a sandbox
``flatpak-spawn`` itself exists, so a missing *host* tool surfaces as a non-zero
return code instead — which existing ``returncode == 0`` checks already handle.
"""

from __future__ import annotations

import os
import subprocess


def in_flatpak() -> bool:
    """True when running inside a Flatpak sandbox."""
    return os.path.exists("/.flatpak-info") or "FLATPAK_ID" in os.environ


def host_argv(argv: list[str]) -> list[str]:
    """Prefix ``flatpak-spawn --host`` when sandboxed, else return argv as-is."""
    if in_flatpak():
        return ["flatpak-spawn", "--host", *argv]
    return list(argv)


def host_run(argv: list[str], **kwargs) -> subprocess.CompletedProcess:
    """``subprocess.run`` that targets the host when inside a Flatpak."""
    return subprocess.run(host_argv(argv), **kwargs)
