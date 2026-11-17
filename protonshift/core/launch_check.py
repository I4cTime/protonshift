"""Launch check: the common reasons a Steam game won't start, found up front.

``check_launch`` is pure: it is handed everything it needs to know (the
launch-options line, the chosen compatibility tool, what is installed) and
returns a list of findings, so it runs without Steam, a display or a disk in
tests. ``diagnose.collect`` gathers the inputs.

Each finding is a dict with ``level`` (``error`` stops the game from starting,
``warn`` probably matters, ``info`` is context, ``ok`` is a passed check),
``title``, ``detail``, ``fix`` (what to do about it; empty when nothing),
``id`` (stable kebab-case, the same finding has the same id on every run) and
``actions`` (a tuple of ``fix_pack.Action``: the one-click fix where one is
mechanical, empty otherwise). ``single_command`` and ``add_command`` actions
exist only here; a fix pack cannot name them.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from .fix_pack import Action
from .launch_merge import (
    COMMAND,
    KNOWN_COMMANDS,
    _tokens,
    add_command,
    remove_word,
    single_command,
    unset_env,
)

_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

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


# Names an older ProtonShift wrote for Valve's builds; Steam's are proton_9, not proton_9_0.
_OLD_BUILTIN_NAME_RE = re.compile(r"proton_[0-9]+_0")


def finding(
    level: str,
    title: str,
    detail: str = "",
    fix: str = "",
    *,
    id: str = "",
    actions: Sequence[Action] = (),
) -> dict[str, Any]:
    """One finding. ``id`` is stable across runs; ``actions`` is the one-click fix, if there is one."""
    return {"level": level, "title": title, "detail": detail, "fix": fix, "id": id, "actions": tuple(actions)}


def _if_it_changes(text: str, edit: Callable[[str], str], action: Action) -> tuple[Action, ...]:
    # An action that would leave the line as it is would offer a button that does nothing.
    return (action,) if edit(text) != text else ()


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


def check_launch_options(text: str, tool_exists: Callable[[str], bool]) -> list[dict[str, Any]]:
    """Findings about the launch-options line alone."""
    text = text.strip()
    if not text:
        return [finding("ok", "Launch options are empty", "The game starts with Steam's defaults.",
                        id="launch-empty")]
    tokens = _tokens(text)
    count = tokens.count(COMMAND)
    out: list[dict[str, Any]] = []
    before = tokens[: tokens.index(COMMAND)] if count else []

    if count > 1:
        out.append(finding(
            "error", "%command% appears more than once",
            "Steam replaces every %command% with the game, so it would be started inside itself.",
            "Keep a single %command% in the launch options.",
            id="command-twice",
            actions=_if_it_changes(text, single_command, Action("single_command")),
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
                id="command-missing",
                actions=_if_it_changes(text, add_command, Action("add_command")),
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
                    id=f"env-needs-{key.lower().replace('_', '-')}",
                    actions=_if_it_changes(
                        text, lambda t, k=key: unset_env(t, k), Action("unset_env", key=key),
                    ),
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
                    id=f"wrapper-missing-{name}",
                    actions=_if_it_changes(
                        text, lambda t, n=name: remove_word(t, n), Action("remove_word", value=name),
                    ),
                ))
    if not out:
        out.append(finding("ok", "Launch options look right", text, id="launch-ok"))
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
) -> list[dict[str, Any]]:
    """All findings for one Steam game, most serious first."""
    out: list[dict[str, Any]] = []

    # --- the game's files ---
    if install_path is None or not install_path.is_dir():
        out.append(finding(
            "error", "The install folder is missing",
            str(install_path) if install_path else "Steam lists the game, but its folder isn't on disk.",
            "Let Steam verify the game files (Properties, Installed Files), or reinstall it.",
            id="install-missing",
        ))
    else:
        out.append(finding("ok", "Game files are present", str(install_path), id="install-ok"))

    # --- launch options ---
    if launch_options_readable:
        out.extend(check_launch_options(launch_options, tool_exists))
    else:
        out.append(finding(
            "warn", "Couldn't read the launch options",
            "Steam's localconfig.vdf could not be parsed, so they were not checked.",
            id="launch-unreadable",
        ))

    # --- compatibility tool ---
    tools = set(available_tools)
    if compat_tool and compat_tool not in tools:
        if _OLD_BUILTIN_NAME_RE.fullmatch(compat_tool):
            # ProtonShift up to 1.3.2 offered Valve's builds under names Steam never used
            # (proton_9_0 for proton_9), so there is nothing to reinstall: the name itself is wrong.
            detail = ("Steam has no build with this name. Older versions of ProtonShift wrote it by mistake, "
                      "so Steam can't start the game with it.")
            fix = "Pick the build you want under Proton version, or let Steam choose with its default."
        else:
            detail = "It is still selected for this game but is no longer installed, so Steam can't start the game."
            fix = "Pick another build under Proton version, or reinstall this one from the Proton builds tab."
        out.append(finding(
            "error", f"The chosen Proton build is gone: {compat_tool}", detail, fix,
            id="proton-gone",
            actions=(Action("default_proton"),),
        ))
    elif compat_tool:
        out.append(finding("ok", f"Proton build is installed: {compat_tool}", id="proton-ok"))
    else:
        out.append(finding("info", "Using Steam's default Proton",
                           "No build is forced for this game; Steam picks one itself.", id="proton-default"))

    # --- anti-cheat runtimes ---
    installed = set(installed_app_ids)
    for kind in sorted(detect_anticheat(install_path)):
        app_id, name = ANTICHEAT_RUNTIMES[kind]
        if app_id in installed:
            out.append(finding("ok", f"{name} is installed", id=f"anticheat-ok-{kind}"))
        else:
            out.append(finding(
                "warn", f"{name} isn't installed",
                "This game ships that anti-cheat. Without the runtime it usually starts and then "
                "refuses to connect or closes.",
                f"Install \"{name}\" from your Steam library (enable Tools in the library filter).",
                id=f"anticheat-missing-{kind}",
            ))

    # --- prefix ---
    if prefix_path is None or not prefix_path.is_dir():
        out.append(finding("info", "No Proton prefix yet",
                           "Steam creates it the first time the game runs. A first launch takes longer.",
                           id="prefix-none"))
    else:
        out.append(finding("ok", "Proton prefix exists", str(prefix_path), id="prefix-ok"))

    # --- what other players report ---
    tier = protondb_tier.strip().lower()
    if tier == "borked":
        out.append(finding(
            "warn", "ProtonDB rates this game Borked",
            "Most players report it does not run under Proton at all, whatever the settings.",
            "Read the recent reports on ProtonDB before spending time on it.",
            id="protondb-borked",
        ))
    elif tier == "bronze":
        out.append(finding("info", "ProtonDB rates this game Bronze",
                           "It runs for some players, often with crashes or missing features.",
                           id="protondb-bronze"))

    order = {"error": 0, "warn": 1, "info": 2, "ok": 3}
    out.sort(key=lambda f: order.get(f["level"], 4))  # stable: keeps the order within a level
    return out


def summarize(findings: list[dict[str, Any]]) -> str:
    errors = sum(1 for f in findings if f["level"] == "error")
    warns = sum(1 for f in findings if f["level"] == "warn")
    if errors:
        return (f"{errors} problem{'s' if errors != 1 else ''} that will stop the game from starting"
                + (f", {warns} warning{'s' if warns != 1 else ''}" if warns else "") + ".")
    if warns:
        return f"Nothing blocks the launch. {warns} thing{'s' if warns != 1 else ''} worth a look."
    return "No problems found."
