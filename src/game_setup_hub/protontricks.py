"""Protontricks integration: detect and run for Steam games."""

from __future__ import annotations

import re
import subprocess

from game_setup_hub.tool_check import find_tool

PROTONTRICKS_FLATPAK = "com.github.Matoking.protontricks"

# Common Winetricks verbs users might want
COMMON_VERBS = [
    ("vcrun2022", "Visual C++ 2022 Redistributable"),
    ("dotnet48", ".NET Framework 4.8"),
    ("d3dx9", "DirectX 9 (d3dx9)"),
    ("corefonts", "Core fonts"),
    ("arial", "Arial font"),
]

# Steam app IDs are decimal integers. Anything else is rejected so a malicious
# payload like "440; rm -rf ~" cannot reach the protontricks command line.
_APP_ID_RE = re.compile(r"^\d{1,12}$")
# Winetricks verbs are short alphanumeric tokens with optional `_-`. We do
# NOT trust the COMMON_VERBS list as the whitelist because users can pass
# arbitrary verbs from the UI; instead we constrain by *shape*.
_VERB_RE = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")


class ProtontricksValidationError(ValueError):
    """Raised when an app_id or verb fails validation before subprocess use."""


def _validate_app_id(app_id: str) -> str:
    if not isinstance(app_id, str) or not _APP_ID_RE.match(app_id):
        raise ProtontricksValidationError(f"Invalid Steam app id: {app_id!r}")
    return app_id


def _validate_verb(verb: str | None) -> str | None:
    if verb is None:
        return None
    if not isinstance(verb, str) or not _VERB_RE.match(verb):
        raise ProtontricksValidationError(f"Invalid winetricks verb: {verb!r}")
    return verb


def is_protontricks_available() -> bool:
    """Check if Protontricks is available (native or Flatpak)."""
    if find_tool("protontricks"):
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

    Raises :class:`ProtontricksValidationError` if ``app_id`` or ``verb`` would
    inject anything other than a Steam app id / winetricks verb token. We
    enforce the whitelist *before* assembling the argv to keep the subprocess
    boundary clean even though :func:`subprocess.Popen` with a list arg does
    not invoke a shell.
    """
    safe_app_id = _validate_app_id(app_id)
    safe_verb = _validate_verb(verb)

    pt = find_tool("protontricks")
    if pt:
        cmd = [pt, safe_app_id]
        cmd.append(safe_verb if safe_verb else "--gui")
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

    cmd = ["flatpak", "run", PROTONTRICKS_FLATPAK, safe_app_id]
    cmd.append(safe_verb if safe_verb else "--gui")
    return cmd


def run_protontricks(app_id: str, verb: str | None = None) -> tuple[bool, str]:
    """
    Run Protontricks for a game.
    If verb is None, opens the GUI.
    Returns (success, error_message).
    """
    try:
        cmd = get_protontricks_cmd(app_id, verb)
    except ProtontricksValidationError as exc:
        return False, str(exc)
    if not cmd:
        return False, "Protontricks not found. Install from Flathub: com.github.Matoking.protontricks"
    try:
        subprocess.Popen(cmd, start_new_session=True)
        return True, ""
    except (FileNotFoundError, OSError) as e:
        return False, str(e)
