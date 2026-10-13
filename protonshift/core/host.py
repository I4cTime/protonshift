"""Run host commands from inside (or outside) a Flatpak sandbox.

Tools like nvidia-smi, powerprofilesctl, gamescope, protontricks live on the
*host*, not in our runtime. Inside a Flatpak they must be invoked via
``flatpak-spawn --host`` (granted by the manifest's org.freedesktop.Flatpak
talk-name); outside a sandbox this is a transparent pass-through.

``host_run`` deliberately does NOT swallow ``FileNotFoundError``: outside a
sandbox a missing tool raises it (callers catch it as before); inside a sandbox
``flatpak-spawn`` itself exists, so a missing *host* tool surfaces as a non-zero
return code instead - which existing ``returncode == 0`` checks already handle.
"""

from __future__ import annotations

import os
import subprocess


def in_flatpak() -> bool:
    """True when running inside a Flatpak sandbox."""
    return os.path.exists("/.flatpak-info") or "FLATPAK_ID" in os.environ


def host_argv(argv: list[str], env: dict[str, str] | None = None) -> list[str]:
    """Prefix ``flatpak-spawn --host`` when sandboxed, else return argv as-is.

    ``env`` holds extra variables for the host command. ``flatpak-spawn
    --host`` does not forward the caller's environment, so inside a sandbox
    they travel as ``--env=K=V`` flags; outside one the caller passes them to
    ``subprocess`` itself (``host_run`` does this).
    """
    if in_flatpak():
        flags = [f"--env={k}={v}" for k, v in (env or {}).items()]
        return ["flatpak-spawn", "--host", *flags, *argv]
    return list(argv)


def host_run(
    argv: list[str], *, extra_env: dict[str, str] | None = None, **kwargs
) -> subprocess.CompletedProcess:
    """``subprocess.run`` that targets the host when inside a Flatpak.

    ``extra_env`` is added to the command's environment in both cases (see
    :func:`host_argv`); don't pass ``env=`` for that, it never reaches the host.
    """
    if extra_env and not in_flatpak():
        kwargs["env"] = {**os.environ, **extra_env}
    return subprocess.run(
        host_argv(argv, extra_env), check=kwargs.pop("check", False), **kwargs
    )
