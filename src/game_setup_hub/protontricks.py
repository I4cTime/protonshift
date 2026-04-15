"""Protontricks integration: detect and run for Steam games."""

from __future__ import annotations

import shutil
import subprocess


PROTONTRICKS_FLATPAK = "com.github.Matoking.protontricks"

# Common Winetricks verbs users might want
COMMON_VERBS = [
    ("vcrun2022", "Visual C++ 2022 Redistributable"),
    ("dotnet48", ".NET Framework 4.8"),
    ("d3dx9", "DirectX 9 (d3dx9)"),
    ("corefonts", "Core fonts"),
    ("arial", "Arial font"),
]


def is_protontricks_available() -> bool:
    """Check if Protontricks is available (native or Flatpak)."""
    if shutil.which("protontricks"):
        return True
    try:
        r = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True,
            text=True,
        )
        return r.returncode == 0 and PROTONTRICKS_FLATPAK in (r.stdout or "")
    except FileNotFoundError:
        return False


def get_protontricks_cmd(app_id: str, verb: str | None = None) -> list[str] | None:
    """
    Get command to run Protontricks for a game.
    Returns [cmd, ...args] or None if not available.
    If verb is None, opens GUI (--gui).
    """
    if shutil.which("protontricks"):
        cmd = ["protontricks", app_id]
        if verb:
            cmd.append(verb)
        else:
            cmd.append("--gui")
        return cmd

    try:
        r = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or PROTONTRICKS_FLATPAK not in (r.stdout or ""):
            return None
    except FileNotFoundError:
        return None

    cmd = ["flatpak", "run", PROTONTRICKS_FLATPAK, app_id]
    if verb:
        cmd.append(verb)
    else:
        cmd.append("--gui")
    return cmd


def run_protontricks(app_id: str, verb: str | None = None) -> tuple[bool, str]:
    """
    Run Protontricks for a game.
    If verb is None, opens the GUI.
    Returns (success, error_message).
    """
    cmd = get_protontricks_cmd(app_id, verb)
    if not cmd:
        return False, "Protontricks not found. Install from Flathub: com.github.Matoking.protontricks"
    try:
        subprocess.Popen(cmd, start_new_session=True)
        return True, ""
    except (FileNotFoundError, OSError) as e:
        return False, str(e)
