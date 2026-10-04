"""Launch check: the common reasons a Steam game won't start, found up front.

``check_launch`` is pure: it is handed everything it needs to know (the
launch-options line, the chosen compatibility tool, what is installed) and
returns a list of findings, so it runs without Steam, a display or a disk in
tests. ``LaunchCheckController`` gathers the inputs on a worker thread.

Each finding is a dict with ``level`` (``error`` stops the game from starting,
``warn`` probably matters, ``info`` is context, ``ok`` is a passed check),
``title``, ``detail`` and ``fix`` (what to do about it; empty when nothing).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from pathlib import Path

from .launch_merge import COMMAND, _tokens

_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Wrapper commands people put in launch options -> the name to show.
KNOWN_COMMANDS: dict[str, str] = {
    "gamemoderun": "GameMode",
    "mangohud": "MangoHud",
    "gamescope": "gamescope",
    "scb": "ScopeBuddy",
    "scopebuddy": "ScopeBuddy",
    "obs-gamecapture": "OBS game capture",
    "prime-run": "prime-run",
    "strangle": "libstrangle",
}
# Environment switches that only do something when a tool is installed.
ENV_NEEDS: dict[str, tuple[str, str]] = {
    "MANGOHUD": ("mangohud", "MangoHud"),
}

# Steam's anti-cheat runtimes: tools a game using that anti-cheat needs installed.
ANTICHEAT_RUNTIMES: dict[str, tuple[str, str]] = {
    "eac": ("1826330", "Proton EasyAntiCheat Runtime"),
    "battleye": ("1161040", "Proton BattlEye Runtime"),
}
_ANTICHEAT_MARKERS: dict[str, tuple[str, ...]] = {
    "eac": ("easyanticheat", "easyanticheat_eos", "start_protected_game.exe"),
    "battleye": ("battleye", "beservice.exe", "beservice_x64.exe"),
}


def finding(level: str, title: str, detail: str = "", fix: str = "") -> dict[str, str]:
    return {"level": level, "title": title, "detail": detail, "fix": fix}


def detect_anticheat(install_path: Path | None, max_depth: int = 3) -> set[str]:
    """Which anti-cheat systems a game ships, judged by well-known file names.

    Looks a few folders deep only: the markers sit near the top of an install,
    and walking a 100 GB game tree would take too long for a button press.
    """
    found: set[str] = set()
    if not install_path or not install_path.is_dir():
        return found
    pending: list[tuple[Path, int]] = [(install_path, 0)]
    while pending:
        folder, depth = pending.pop()
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            name = entry.name.lower()
            for kind, markers in _ANTICHEAT_MARKERS.items():
                if name in markers:
                    found.add(kind)
            if depth + 1 < max_depth and entry.is_dir() and not entry.is_symlink():
                pending.append((entry, depth + 1))
    return found


def check_launch_options(text: str, tool_exists: Callable[[str], bool]) -> list[dict[str, str]]:
    """Findings about the launch-options line alone."""
    text = text.strip()
    if not text:
        return [finding("ok", "Launch options are empty", "The game starts with Steam's defaults.")]
    tokens = _tokens(text)
    count = tokens.count(COMMAND)
    out: list[dict[str, str]] = []
    before = tokens[: tokens.index(COMMAND)] if count else []

    if count > 1:
        out.append(finding(
            "error", "%command% appears more than once",
            "Steam replaces every %command% with the game, so it would be started inside itself.",
            "Keep a single %command% in the launch options.",
        ))
    if count == 0:
        # Without %command% the whole line is handed to the game as arguments.
        stray = [t for t in tokens if _ENV_RE.match(t) or t.rsplit("/", 1)[-1] in KNOWN_COMMANDS]
        if stray:
            out.append(finding(
                "error", "Launch options have no %command%",
                f"Without it, {', '.join(stray[:3])} {'is' if len(stray) == 1 else 'are'} passed to the game "
                "as arguments instead of wrapping it, so nothing they are meant to do happens.",
                "Add %command% after them, for example: " + " ".join(stray[:3]) + " %command%",
            ))

    seen: set[str] = set()
    for token in before:
        if _ENV_RE.match(token):
            key = token.split("=", 1)[0]
            need = ENV_NEEDS.get(key)
            if need and need[0] not in seen and not tool_exists(need[0]):
                seen.add(need[0])
                out.append(finding(
                    "warn", f"{need[1]} isn't installed",
                    f"{token} is set, but without {need[1]} it does nothing.",
                    f"Install {need[1]} from your package manager, or remove {token}.",
                ))
            continue
        name = token.rsplit("/", 1)[-1]
        if name in KNOWN_COMMANDS and name not in seen:
            seen.add(name)
            if not tool_exists(name):
                out.append(finding(
                    "error", f"{KNOWN_COMMANDS[name]} isn't installed",
                    f"The launch options run the game through `{name}`, which wasn't found. "
                    "Steam then fails to start the game at all, usually without a message.",
                    f"Install {KNOWN_COMMANDS[name]}, or remove `{name}` from the launch options.",
                ))
    if not out:
        out.append(finding("ok", "Launch options look right", text))
    return out


def check_launch(
    *,
    launch_options: str,
    launch_options_readable: bool,
    compat_tool: str,
    available_tools: Iterable[str],
    install_path: Path | None,
    prefix_path: Path | None,
    installed_app_ids: Iterable[str],
    tool_exists: Callable[[str], bool],
    protondb_tier: str = "",
) -> list[dict[str, str]]:
    """All findings for one Steam game, most serious first."""
    out: list[dict[str, str]] = []

    # --- the game's files ---
    if install_path is None or not install_path.is_dir():
        out.append(finding(
            "error", "The install folder is missing",
            str(install_path) if install_path else "Steam lists the game, but its folder isn't on disk.",
            "Let Steam verify the game files (Properties, Installed Files), or reinstall it.",
        ))
    else:
        out.append(finding("ok", "Game files are present", str(install_path)))

    # --- launch options ---
    if launch_options_readable:
        out.extend(check_launch_options(launch_options, tool_exists))
    else:
        out.append(finding(
            "warn", "Couldn't read the launch options",
            "Steam's localconfig.vdf could not be parsed, so they were not checked.",
        ))

    # --- compatibility tool ---
    tools = set(available_tools)
    if compat_tool and compat_tool not in tools:
        out.append(finding(
            "error", f"The chosen Proton build is gone: {compat_tool}",
            "It is still selected for this game but is no longer installed, so Steam can't start the game.",
            "Pick another build under Proton version, or reinstall this one from the Proton builds tab.",
        ))
    elif compat_tool:
        out.append(finding("ok", f"Proton build is installed: {compat_tool}"))
    else:
        out.append(finding("info", "Using Steam's default Proton",
                           "No build is forced for this game; Steam picks one itself."))

    # --- anti-cheat runtimes ---
    installed = set(installed_app_ids)
    for kind in sorted(detect_anticheat(install_path)):
        app_id, name = ANTICHEAT_RUNTIMES[kind]
        if app_id in installed:
            out.append(finding("ok", f"{name} is installed"))
        else:
            out.append(finding(
                "warn", f"{name} isn't installed",
                "This game ships that anti-cheat. Without the runtime it usually starts and then "
                "refuses to connect or closes.",
                f"Install \"{name}\" from your Steam library (enable Tools in the library filter).",
            ))

    # --- prefix ---
    if prefix_path is None or not prefix_path.is_dir():
        out.append(finding("info", "No Proton prefix yet",
                           "Steam creates it the first time the game runs. A first launch takes longer."))
    else:
        out.append(finding("ok", "Proton prefix exists", str(prefix_path)))

    # --- what other players report ---
    tier = protondb_tier.strip().lower()
    if tier == "borked":
        out.append(finding(
            "warn", "ProtonDB rates this game Borked",
            "Most players report it does not run under Proton at all, whatever the settings.",
            "Read the recent reports on ProtonDB before spending time on it.",
        ))
    elif tier == "bronze":
        out.append(finding("info", "ProtonDB rates this game Bronze",
                           "It runs for some players, often with crashes or missing features."))

    order = {"error": 0, "warn": 1, "info": 2, "ok": 3}
    out.sort(key=lambda f: order.get(f["level"], 4))  # stable: keeps the order within a level
    return out


def summarize(findings: list[dict[str, str]]) -> str:
    errors = sum(1 for f in findings if f["level"] == "error")
    warns = sum(1 for f in findings if f["level"] == "warn")
    if errors:
        return (f"{errors} problem{'s' if errors != 1 else ''} that will stop the game from starting"
                + (f", {warns} warning{'s' if warns != 1 else ''}" if warns else "") + ".")
    if warns:
        return f"Nothing blocks the launch. {warns} thing{'s' if warns != 1 else ''} worth a look."
    return "No problems found."
