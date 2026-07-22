"""protontricks integration — run winetricks verbs against a game's Proton prefix.

protontricks is a wrapper that points winetricks at the right Steam Proton
prefix for a given app id. We support both the native binary and the Flathub
package (``com.github.Matoking.protontricks``), invoked through the host runner
so it works from inside our own Flatpak too.

Two kinds of action:

* **verbs** — ``protontricks <appid> <verb> …`` runs a batch of winetricks verbs
  (corefonts, vcrun2022, dxvk, …). Long-running and may download; run off the UI
  thread with a generous timeout.
* **GUI** — ``protontricks --gui`` (optionally scoped to an app id) opens the
  interactive winetricks window; launched detached, we don't wait on it.

The ``--no-bwrap`` flag is passed for verb runs: on some setups (notably the
Flatpak build and hardened kernels) winetricks' own bubblewrap nesting fails,
and disabling it is the documented workaround.
"""

from __future__ import annotations

import re
import subprocess

from .host import host_argv, host_run, in_flatpak
from .tool_check import find_tool

# A curated shortlist of the verbs people most often need for Proton games.
# (verb, human label). Not exhaustive — the GUI covers the long tail.
COMMON_VERBS: tuple[tuple[str, str], ...] = (
    ("corefonts", "MS core fonts"),
    ("vcrun2022", "Visual C++ 2015–2022"),
    ("vcrun2019", "Visual C++ 2015–2019"),
    ("dotnet48", ".NET Framework 4.8"),
    ("dotnetdesktop6", ".NET Desktop Runtime 6"),
    ("dxvk", "DXVK (DirectX→Vulkan)"),
    ("vkd3d", "VKD3D (D3D12→Vulkan)"),
    ("d3dcompiler_47", "d3dcompiler_47"),
    ("xact", "XACT audio"),
    ("physx", "NVIDIA PhysX"),
    ("faudio", "FAudio"),
    ("win10", "Windows 10 version"),
)

_FLATPAK_ID = "com.github.Matoking.protontricks"


def protontricks_base() -> list[str] | None:
    """Return the base argv for protontricks, or ``None`` if not installed.

    Prefers a native binary; falls back to the Flathub package. The returned
    argv is *not* yet wrapped for the host — pass it through :func:`host_argv`
    (or :func:`host_run`) at call time.
    """
    native = find_tool("protontricks")
    if native:
        return [native]
    # Flathub package — probe via the host's flatpak.
    try:
        r = host_run(
            ["flatpak", "info", _FLATPAK_ID],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if r.returncode == 0:
        return ["flatpak", "run", _FLATPAK_ID]
    return None


def is_available() -> bool:
    return protontricks_base() is not None


_LIST_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<appid>\d+)\)\s*$")


def parse_list(text: str) -> list[tuple[str, str]]:
    """Parse ``protontricks --list`` output into ``[(appid, name)]``."""
    games: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith(("found the following", "note:", "warning:")):
            continue
        m = _LIST_RE.match(line)
        if m:
            games.append((m.group("appid"), m.group("name").strip()))
    return games


def list_prefixes() -> list[tuple[str, str]]:
    """Return games protontricks knows about as ``[(appid, name)]``."""
    base = protontricks_base()
    if base is None:
        return []
    try:
        r = host_run(
            [*base, "--list"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_verb_env(),
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0 or not r.stdout:
        return []
    return parse_list(r.stdout)


def _verb_env() -> dict | None:
    """Non-interactive winetricks env so verb installs don't block on prompts."""
    import os

    env = dict(os.environ)
    env["WINETRICKS_LATEST_VERSION_CHECK"] = "disabled"
    return env


def run_verbs(appid: str, verbs: list[str], timeout: int = 1800) -> tuple[bool, str]:
    """Run winetricks ``verbs`` for ``appid``. Blocking — call off the UI thread.

    Returns ``(ok, combined_output)``.
    """
    base = protontricks_base()
    if base is None:
        return False, "protontricks is not installed."
    clean = [v for v in verbs if v]
    if not clean:
        return False, "No verbs selected."
    argv = [*base, "--no-bwrap", appid, *clean]
    try:
        r = host_run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_verb_env(),
        )
    except subprocess.TimeoutExpired:
        return False, f"Timed out after {timeout // 60} min."
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        return False, f"Couldn't run protontricks: {exc}"
    out = (r.stdout or "") + (r.stderr or "")
    return (r.returncode == 0), out.strip()


def launch_gui(appid: str = "") -> tuple[bool, str]:
    """Open the interactive protontricks GUI (detached). Optionally scoped to ``appid``."""
    base = protontricks_base()
    if base is None:
        return False, "protontricks is not installed."
    argv = [*base, "--gui"] if not appid else [*base, appid, "--gui"]
    try:
        subprocess.Popen(  # noqa: S603 — argv is built from constants + numeric appid
            host_argv(argv),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (FileNotFoundError, OSError) as exc:
        return False, f"Couldn't launch protontricks: {exc}"
    where = "on the host" if in_flatpak() else ""
    return True, f"Opened winetricks GUI {where}".strip() + "."
