"""Diagnose: one ranked list of the reasons a game may not start or run well.

Four sources feed it, in this order: the launch check (the game's own
settings), the Proton log, the fix pack's rules (and the user's own fixes),
and the system checks (the machine under every game). Each becomes a
:class:`Finding` with a severity from :data:`SEVERITY_ORDER`, evidence where
there is some, and the actions of a one-click fix where one is known.

Everything down to :func:`to_row` is pure and works on a :class:`Facts`, so
tests never need Steam or a display. :func:`collect` is the one function that
reads the disk; the controller calls it on a worker thread. It reads only, and
never starts the game.

Diagnose prefers a missed finding to a false one: a fact that could not be
found out never satisfies a rule's condition (``docs/fix-pack.md``).
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from . import compat_tool, fix_pack, gpu, host, launch_check, proton_log, steam, system_checks, tool_check
from .display import _is_wayland
from .fix_apply import read_state
from .fix_pack import Action, Rule, When, match_log
from .gpu import GPUInfo
from .launch_merge import prefix_commands, prefix_env, split_line
from .snapshots import GameState
from .system_checks import Check
from .vdf_config import read_launch_options

SEVERITY_ORDER = ("blocking", "likely", "advice", "context", "ok")

_LEVELS = {"error": "blocking", "warn": "likely", "info": "context", "ok": "ok"}
# Launch check findings about Proton itself, which a native game does not use.
_PROTON_ONLY_IDS = ("proton-", "prefix-", "anticheat-")
_LAUNCH_ACTIONS = frozenset({"env", "unset_env", "game_arg", "remove_word", "single_command", "add_command",
                             "user_snippet"})
_MAX_EVIDENCE = 300

T = TypeVar("T")


@dataclass(frozen=True)
class Facts:
    app_id: str
    steam_app: bool  # False for a Non-Steam shortcut
    native: bool  # a native Linux game: no Proton involved
    launch_options: str
    launch_options_readable: bool
    compat_tool: str  # "" = Steam's default
    proton_family: str  # "valve" | "ge" | "cachyos" | "other" | "" (unknown)
    proton_major: int | None
    gpu_vendors: frozenset[str]  # subset of {"nvidia","amd","intel"}; empty = unknown
    session: str  # "wayland" | "x11" | "" (unknown)
    log_lines: tuple[str, ...] | None  # None = no log file
    log_modified: str  # "" when no log
    log_path: str = ""  # the log file as the user knows the path; "" when none


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str  # one of SEVERITY_ORDER
    title: str
    cause: str
    evidence: str  # the log line or the setting that triggered it; "" when none
    fix: str  # prose: what to do
    source: str  # URL, "" when none
    origin: str  # "check" | "log" | "system" | "pack" | "user"
    actions: tuple[Action, ...]


# --------------------------------------------------------------------------- #
# facts
# --------------------------------------------------------------------------- #

# Steam's own names carry no minor part. ``proton_9_0`` and the like are not
# Valve names: older ProtonShift builds wrote them, and Steam does not know them.
_VALVE_RE = re.compile(r"proton_([0-9]+)")
_VALVE_NAMED = frozenset({"proton_experimental", "proton_hotfix"})
_GE_RE = re.compile(r"GE-Proton([0-9]+)-[0-9]+")
_GE_OLD_RE = re.compile(r"Proton-([0-9]+)\.[0-9]+-GE-[0-9]+(?:-[A-Za-z]+)?")
# Distro packages register GE without a version in the name (Arch's
# proton-ge-custom-bin calls itself "Proton-GE").
_GE_UNVERSIONED = frozenset({"proton-ge", "proton-ge-custom", "ge-proton"})
_CACHYOS_VERSION_RE = re.compile(r"cachyos[-_]v?([0-9]+)\.[0-9]+")


def _valve_major(digits: str) -> int | None:
    if digits.startswith("0"):
        return None
    if len(digits) == 1:
        return int(digits)
    # Up to 6.3 Valve ran major and minor together (proton_513 is 5.13,
    # proton_63 is 6.3); from 7 on the name is the major alone (proton_10).
    if digits[0] in "3456":
        return int(digits[0])
    if len(digits) == 2 and digits[0] in "12":
        return int(digits)
    return None


def proton_build(tool_name: str) -> tuple[str, int | None]:
    """``(family, major)`` of a compatibility tool's internal name.

    The version is only ever read off the name; a name that does not carry one
    in a known shape gives ``None``, never a guess.
    """
    name = (tool_name or "").strip()
    if not name:
        return "", None
    if name in _VALVE_NAMED:
        return "valve", None
    m = _VALVE_RE.fullmatch(name)
    if m:
        return "valve", _valve_major(m.group(1))
    m = _GE_RE.fullmatch(name) or _GE_OLD_RE.fullmatch(name)
    if m:
        return "ge", int(m.group(1))
    lower = name.lower()
    if lower in _GE_UNVERSIONED:
        return "ge", None
    if "cachyos" in lower:
        m = _CACHYOS_VERSION_RE.search(lower)
        return "cachyos", int(m.group(1)) if m else None
    return "other", None


# Kernel driver names (what gpu.py reports from sysfs) and words in the
# product names nvidia-smi reports.
_DRIVER_VENDORS = {
    "amdgpu": "amd", "radeon": "amd",
    "i915": "intel", "xe": "intel",
    "nvidia": "nvidia", "nouveau": "nvidia",
}
_NAME_WORDS = {
    "nvidia": "nvidia", "geforce": "nvidia", "quadro": "nvidia",
    "amd": "amd", "radeon": "amd",
    "intel": "intel",
}


def gpu_vendors(gpus: Iterable[GPUInfo]) -> frozenset[str]:
    """The vendors of ``gpus``; a name or driver that says nothing adds nothing."""
    found: set[str] = set()
    for info in gpus:
        for text in (getattr(info, "name", ""), getattr(info, "driver", "")):
            if not isinstance(text, str):
                continue
            lower = text.strip().lower()
            if lower in _DRIVER_VENDORS:
                found.add(_DRIVER_VENDORS[lower])
                continue
            for word in re.split(r"[^a-z0-9]+", lower):
                if word in _NAME_WORDS:
                    found.add(_NAME_WORDS[word])
    return frozenset(found)


def session_type() -> str:
    """``"wayland"``, ``"x11"`` or ``""`` when the session does not say."""
    if _is_wayland():
        return "wayland"
    # DISPLAY alone is not enough: an X11-only sandbox on Wayland has it too.
    if os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "x11":
        return "x11"
    return ""


# --------------------------------------------------------------------------- #
# rules
# --------------------------------------------------------------------------- #

def _prefix(facts: Facts) -> list[str] | None:
    # Read as launch_check reads it: with no %command% every word is a game
    # argument, so nothing is "before" it and no word or variable counts.
    if not facts.launch_options_readable:
        return None
    return split_line(facts.launch_options)[0]


def _basename(word: str) -> str:
    return word.rsplit("/", 1)[-1]


def _uses_proton(when: When) -> bool:
    return bool(when.proton_family) or when.proton_major_min is not None or when.proton_major_max is not None


def when_holds(when: When, facts: Facts) -> bool:
    """True when every condition set in ``when`` holds; an unset one holds, an unknown fact never does."""
    if when.gpu_vendor and not facts.gpu_vendors & set(when.gpu_vendor):
        return False
    if when.session and facts.session not in when.session:
        return False
    if when.proton_family and facts.proton_family not in when.proton_family:
        return False
    major = facts.proton_major
    if when.proton_major_min is not None and (major is None or major < when.proton_major_min):
        return False
    if when.proton_major_max is not None and (major is None or major > when.proton_major_max):
        return False
    if when.launch_has or when.env_set or when.env_unset:
        prefix = _prefix(facts)
        if prefix is None:
            return False
        words = {_basename(w) for w in prefix_commands(prefix)}
        keys = {w.split("=", 1)[0] for w in prefix_env(prefix)}
        if not all(word in words for word in when.launch_has):
            return False
        if not all(key in keys for key in when.env_set):
            return False
        if any(key in keys for key in when.env_unset):
            return False
    return True


def _setting_evidence(when: When, facts: Facts) -> str:
    """The setting that satisfied a rule that matched without a log line."""
    prefix = _prefix(facts) or []
    shown = [w for w in prefix_commands(prefix) if _basename(w) in when.launch_has]
    shown += [w for w in prefix_env(prefix) if w.split("=", 1)[0] in when.env_set]
    if shown:
        return " ".join(dict.fromkeys(shown))
    if _uses_proton(when):
        return facts.compat_tool
    return ""


def rule_finding(rule: Rule, facts: Facts) -> Finding | None:
    """The finding ``rule`` gives for ``facts``, or None when any part of its match fails."""
    if rule.app_ids and facts.app_id not in rule.app_ids:
        return None
    if facts.native and (rule.log or _uses_proton(rule.when)):
        return None
    if not when_holds(rule.when, facts):
        return None
    if rule.log:
        if facts.log_lines is None:
            return None
        line = match_log(rule, facts.log_lines)
        if line is None:
            return None
        evidence, origin = line[:_MAX_EVIDENCE], "log"
    else:
        evidence, origin = _setting_evidence(rule.when, facts), "pack"
    if rule.origin == "user":
        origin = "user"
    return Finding(
        id=rule.id,
        severity=rule.severity,
        title=rule.title,
        cause=rule.cause,
        evidence=evidence,
        fix="",
        source=rule.source,
        origin=origin,
        actions=tuple(rule.actions),
    )


# --------------------------------------------------------------------------- #
# the list
# --------------------------------------------------------------------------- #

def _check_evidence(actions: Sequence[Action], facts: Facts) -> str:
    kinds = {a.type for a in actions}
    if kinds & _LAUNCH_ACTIONS:
        return facts.launch_options
    if "default_proton" in kinds:
        return facts.compat_tool
    return ""


def _launch_rows(launch_findings: Sequence[dict[str, Any]], facts: Facts) -> list[Finding]:
    rows: list[Finding] = []
    for index, raw in enumerate(launch_findings):
        fid = str(raw.get("id") or f"check-{index}")
        if facts.native and fid.startswith(_PROTON_ONLY_IDS):
            continue
        actions = tuple(raw.get("actions") or ())
        rows.append(Finding(
            id=fid,
            severity=_LEVELS.get(str(raw.get("level", "")), "context"),
            title=str(raw.get("title", "")),
            cause=str(raw.get("detail", "")),
            evidence=_check_evidence(actions, facts),
            fix=str(raw.get("fix", "")),
            source="",
            origin="check",
            actions=actions,
        ))
    return rows


def _context(
    fid: str, title: str, cause: str, evidence: str = "", actions: tuple[Action, ...] = (),
) -> Finding:
    return Finding(fid, "context", title, cause, evidence, "", "", "log", actions)


def _log_rows(facts: Facts, rule_matched_log: bool) -> list[Finding]:
    if facts.native:
        return []
    readable = facts.launch_options_readable
    logging_on = readable and proton_log.logging_enabled(facts.launch_options)
    if facts.log_lines is None:
        if not facts.steam_app:
            return []
        if logging_on:
            return [_context(
                "log-waiting", "There is no Proton log for this game yet",
                "Proton logging is on, but no log has been written yet. Run the game once, then diagnose "
                "again.",
            )]
        return [_context(
            "log-off", "There is no Proton log for this game",
            "Proton writes a log of what happens while the game starts only when logging is on. Turn it on, "
            "run the game once, then diagnose again, so Diagnose can recognise more problems.",
            actions=(Action("env", key="PROTON_LOG", value="1"),) if readable else (),
        )]

    rows: list[Finding] = []
    where = facts.log_path or "the Proton log"
    when = f", last written {facts.log_modified}" if facts.log_modified else ""
    cause = (f"Diagnose read the end of {where}{when}. If the game has failed since then, run it again and "
             "diagnose again so the log is current.")
    if readable and not logging_on:
        cause += " Logging is off now, so this log is from an earlier run."
    title = "Read the Proton log"
    if facts.log_modified:
        title += f" written {facts.log_modified}"
    rows.append(_context("log-read", title, cause, evidence=facts.log_path))

    if not rule_matched_log:
        problems = [line.strip() for line in facts.log_lines if proton_log.is_problem_line(line)]
        if problems:
            count = len(problems)
            if count == 1:
                title = "1 line in the log looks like a problem ProtonShift does not recognise"
            else:
                title = f"{count} lines in the log look like problems ProtonShift does not recognise"
            rows.append(_context(
                "log-unrecognised", title,
                "They may still explain the trouble. Read them in the log, or search the web for them "
                "together with the game's name.",
                evidence=problems[0][:_MAX_EVIDENCE],
            ))
    return rows


def _system_rows(checks: Sequence[Check], facts: Facts) -> list[Finding]:
    rows: list[Finding] = []
    for check in checks:
        if facts.native and check.id == "disk-prefix":
            continue  # a native game has no Proton prefix
        if check.state == system_checks.PROBLEM:
            # Proton needs Vulkan to start at all; a native game may still run on OpenGL.
            severity = "blocking" if check.id == "vulkan" and not facts.native else "likely"
        elif check.state == system_checks.OK:
            severity = "ok"
        else:
            severity = "context"
        rows.append(Finding(check.id, severity, check.title, check.detail, "", check.fix, "", "system", ()))
    return rows


def _rank(finding: Finding) -> int:
    try:
        return SEVERITY_ORDER.index(finding.severity)
    except ValueError:
        return len(SEVERITY_ORDER)


def diagnose(
    facts: Facts,
    *,
    rules: Sequence[Rule],
    launch_findings: Sequence[dict[str, Any]],
    checks: Sequence[Check],
) -> list[Finding]:
    """Every finding for one game, most serious first.

    Built in origin order (launch check, log, rules, system), deduplicated by
    id with the first one kept, then sorted by severity; the sort is stable, so
    origin order holds within a severity.
    """
    rule_rows = [f for f in (rule_finding(rule, facts) for rule in rules) if f is not None]
    rule_matched_log = any(f.origin == "log" for f in rule_rows)
    built = [
        *_launch_rows(launch_findings, facts),
        *_log_rows(facts, rule_matched_log),
        *rule_rows,
        *_system_rows(checks, facts),
    ]
    seen: set[str] = set()
    unique: list[Finding] = []
    for finding in built:
        if finding.id in seen:
            continue
        seen.add(finding.id)
        unique.append(finding)
    return sorted(unique, key=_rank)


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def summarize(findings: Sequence[Finding]) -> str:
    """One sentence for the top of the dialog, the most serious count first."""
    blocking = sum(1 for f in findings if f.severity == "blocking")
    likely = sum(1 for f in findings if f.severity == "likely")
    advice = sum(1 for f in findings if f.severity == "advice")
    if blocking:
        text = _count(blocking, "problem", "problems") + " that will stop the game from starting"
        if likely:
            text += f", {likely} more worth a look"
        return text + "."
    if likely:
        return f"Nothing blocks the launch. {_count(likely, 'thing', 'things')} worth a look."
    if advice:
        return f"No problems found. {_count(advice, 'suggestion', 'suggestions')} you can try."
    return "No problems found."


def to_row(f: Finding) -> dict[str, object]:
    """A finding as plain str/bool/list values, safe to hand to QML."""
    return {
        "id": f.id,
        "severity": f.severity,
        "title": f.title,
        "cause": f.cause,
        "evidence": f.evidence,
        "fix": f.fix,
        "source": f.source,
        "origin": f.origin,
        "manual": [a.text for a in f.actions if a.type == "manual"],
        "canApply": any(a.type != "manual" for a in f.actions),
    }


# --------------------------------------------------------------------------- #
# gathering (disk)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Report:
    app_id: str
    findings: list[Finding]
    summary: str
    state: GameState | None  # current settings, None when unreadable or a shortcut
    can_apply: bool  # False for shortcuts and unreadable configs
    steam_running: bool | None
    log_path: str
    paths: tuple[Path | None, Path | None]  # (localconfig.vdf, config.vdf) for apply/undo


def _quiet(read: Callable[[], T], fallback: T) -> T:
    # Diagnose has to open whatever is broken on this machine; a failed read
    # becomes an unknown fact, which the rules already treat as "does not hold".
    try:
        return read()
    except Exception:  # noqa: BLE001
        return fallback


def _installed_runtimes(root: Path | None) -> list[str]:
    # Tools (Proton builds, runtimes) are hidden from the game list, so their
    # manifests are looked for directly.
    if root is None:
        return []
    found: list[str] = []
    for lib in steam._find_libraryfolders(root):
        for runtime_id, _name in launch_check.ANTICHEAT_RUNTIMES.values():
            if (lib / "steamapps" / f"appmanifest_{runtime_id}.acf").exists():
                found.append(runtime_id)
    return found


def collect(
    app_id: str,
    *,
    install_path: str,
    prefix_path: str,
    shortcut_options: str | None,
    native: bool,
    protondb_tier: str,
) -> Report:
    """Gather everything about one game and diagnose it. Reads only; never raises for missing data.

    ``shortcut_options`` not None means a Non-Steam shortcut whose launch
    options are given (Steam keeps them in the shortcut, not in localconfig).
    """
    steam_app = shortcut_options is None
    root = _quiet(lambda: steam.discover_games()[0], None)
    localconfig = _quiet(lambda: steam.get_localconfig_path(root), None) if root else None
    config_vdf = compat_tool.get_config_vdf_path(root) if root else None

    if steam_app:
        readable, options = (False, "")
        if localconfig:
            readable, options = _quiet(lambda: read_launch_options(localconfig, app_id), (False, ""))
    else:
        readable, options = True, shortcut_options or ""
    if not isinstance(options, str):
        readable, options = False, ""
    ok, tool = (False, "")
    if config_vdf:
        ok, tool = _quiet(lambda: compat_tool.read_compat_tool(config_vdf, app_id), (False, ""))
    tool = tool if ok and isinstance(tool, str) else ""

    install = Path(install_path) if install_path else None
    prefix = Path(prefix_path) if prefix_path else None
    family, major = ("", None) if native else proton_build(tool)
    available = list(_quiet(lambda: steam.get_available_proton_tools(root), [""]))
    runtimes = _quiet(lambda: _installed_runtimes(root), [])
    if family == "valve" and tool not in available:
        # Steam downloads its own Proton builds when a game needs one, and
        # their internal names are not on disk to compare with, so a Valve
        # build is never reported as gone.
        available.append(tool)
    launch_findings = _quiet(lambda: launch_check.check_launch(
        launch_options=options,
        launch_options_readable=readable,
        compat_tool=tool,
        available_tools=available,
        install_path=install,
        prefix_path=prefix,
        installed_app_ids=runtimes,
        tool_exists=tool_check.is_tool_available,
        protondb_tier=protondb_tier,
    ), [])

    log_file = None if native else proton_log.log_path(app_id)
    log_lines: tuple[str, ...] | None = None
    log_modified = ""
    if log_file is not None:
        try:
            log_lines = tuple(proton_log.read_tail(log_file).text.splitlines())
            log_modified = proton_log.modified_label(log_file)
        except (OSError, ValueError):
            log_lines = None

    facts = Facts(
        app_id=app_id,
        steam_app=steam_app,
        native=native,
        launch_options=options,
        launch_options_readable=readable,
        compat_tool=tool,
        proton_family=family,
        proton_major=major,
        gpu_vendors=_quiet(lambda: gpu_vendors(gpu.get_gpu_info()), frozenset()),
        session=_quiet(session_type, ""),
        log_lines=log_lines,
        log_modified=log_modified,
        log_path=steam.host_display_path(log_file) if log_lines is not None and log_file else "",
    )
    checks = _quiet(lambda: system_checks.run_checks(
        steam_root=root, install_path=install, prefix_path=prefix, run=host.host_run,
    ), [])
    rules = [*fix_pack.load_bundled_pack().rules, *_quiet(lambda: fix_pack.user_rules(app_id), [])]
    findings = diagnose(facts, rules=rules, launch_findings=launch_findings, checks=checks)

    state = read_state(localconfig, config_vdf, app_id) if steam_app else None
    return Report(
        app_id=app_id,
        findings=findings,
        summary=summarize(findings),
        state=state,
        can_apply=steam_app and state is not None,
        steam_running=_quiet(lambda: system_checks.steam_running(host.host_run), None),
        log_path=str(log_file) if log_file else "",
        paths=(localconfig, config_vdf),
    )
